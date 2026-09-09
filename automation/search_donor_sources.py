"""Configured translation-unit membership for immutable source donor scans.

Directory membership alone is not platform membership. Splat shares src/dra
and src/st between builds with different C translation units. Only configured
units and their quoted include closure can supply source donor functions.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


PROJECTION_PROTOCOL = "sotn-donor-platform-projection-v1"


def _platform_macros(version):
    # Canonical PSX/PSP version selection follows include/version.h. Saturn
    # uses a separate toolchain: do not invent equivalent macro definitions.
    if version not in ("us", "hd", "pspeu"):
        return {}
    return {"VERSION_US": version == "us", "VERSION_HD": version == "hd",
            "VERSION_PSP": version == "pspeu", "VERSION_PC": False}


def _platform_condition(expression, macros):
    def defined(match):
        name = match[1] or match[2]
        if name not in macros:
            raise ValueError("unknown platform condition")
        return str(int(macros[name]))

    def boolean(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return bool(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not boolean(node.operand)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            values = [boolean(value) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        raise ValueError("unsupported platform condition")

    try:
        expr = re.sub(r"\bdefined\s*(?:\(\s*([A-Za-z_]\w*)\s*\)|([A-Za-z_]\w*))", defined, expression)
        if re.sub(r"0[xX][0-9A-Fa-f]+|[0-9]+|&&|\|\||[!()\s]", "", expr):
            return None
        # VERSION_US is an empty definition, not integer 1. Only defined()
        # queries establish these platform facts; bare macro values stay unknown.
        expr = expr.replace("&&", " and ").replace("||", " or ")
        expr = re.sub(r"!(?!=)", " not ", expr)
        return boolean(ast.parse(expr.strip(), mode="eval").body)
    except (ValueError, SyntaxError, RecursionError):
        return None


def project_platform_source(text, version):
    """Project known version branches, retaining offsets and refusing unknowns.

    This is a bounded conditional projection, not a general C preprocessor.
    Consumer feature macros, include guards and compiler-specific expressions
    still need a bound preprocessing context. Never treat unknown as false.
    """
    from automation.search_donor_scan import _strip_c_comments
    macros = _platform_macros(version)
    original_lines = text.splitlines(keepends=True)
    scrubbed_lines = _strip_c_comments(text).splitlines(keepends=True)
    # C splices physical lines before removing comments. A splice hidden by
    # comment removal needs a real preprocessor; otherwise its next line could
    # be falsely admitted as an active directive or donor function.
    if any(raw.rstrip("\r\n").endswith("\\") and not clean.rstrip("\r\n").endswith("\\")
           for raw, clean in zip(original_lines, scrubbed_lines)):
        return None
    stack, output = [], []
    active, index = True, 0
    while index < len(original_lines):
        raw, logical = original_lines[index], scrubbed_lines[index]
        index += 1
        while logical.rstrip("\r\n").endswith("\\") and index < len(original_lines):
            logical = logical.rstrip("\r\n")[:-1] + scrubbed_lines[index]
            raw += original_lines[index]
            index += 1
        directive = re.match(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif|define|undef)\b(.*)", logical, re.S)
        keep = active
        if directive:
            kind, tail = directive[1], directive[2].strip()
            if kind in ("define", "undef"):
                name = re.match(r"[A-Za-z_]\w*", tail)
                if active and name and name[0] in macros:
                    return None
            elif kind in ("if", "ifdef", "ifndef"):
                expression = tail if kind == "if" else f"defined({tail})"
                condition = _platform_condition(expression, macros) if active else False
                if condition is None:
                    return None
                if kind == "ifndef":
                    condition = not condition
                stack.append({"parent": active, "taken": bool(condition), "else": False})
                active = active and bool(condition)
                keep = False
            elif not stack:
                return None
            elif kind == "elif":
                frame = stack[-1]
                if frame["else"]:
                    return None
                evaluate = frame["parent"] and not frame["taken"]
                condition = _platform_condition(tail, macros) if evaluate else False
                if condition is None:
                    return None
                active = bool(evaluate and condition)
                frame["taken"] |= bool(condition)
                keep = False
            elif kind == "else":
                frame = stack[-1]
                if frame["else"] or tail:
                    return None
                frame["else"] = True
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
                keep = False
            elif kind == "endif":
                if tail:
                    return None
                active = stack.pop()["parent"]
                keep = False
        output.append(raw if keep else "".join("\n" if c == "\n" else " " for c in raw))
    return None if stack else "".join(output)


def configured_source_texts(roots, *, root: Path, texts: dict[Path, str]):
    from automation.search_donor_scan import _load_config, _INCLUDE_RE, _strip_c_comments

    selected, missing = set(), set()

    def walk(value, source_root):
        if isinstance(value, list):
            if len(value) >= 3 and value[1] in ("c", ".text"):
                add(source_root, value[2])
            else:
                for child in value:
                    walk(child, source_root)
        elif isinstance(value, dict):
            if value.get("type") in ("c", ".text"):
                add(source_root, value.get("file", value.get("name")))
            for key in ("segments", "subsegments"):
                if key in value:
                    walk(value[key], source_root)

    def add(source_root, name):
        if not isinstance(name, str) or not name:
            return
        path = (source_root / (name if name.endswith(".c") else name + ".c")).resolve()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            raise ValueError("configured donor translation unit escapes snapshot")
        if path in texts:
            selected.add(path)
        else:
            missing.add(relative)

    for relative in roots.config_paths:
        path = root / relative
        config = _load_config(path, verified_texts=texts)
        source = config.get("options", {}).get("src_path")
        if source:
            walk(config.get("segments", []), root / source)
    translation_units = sorted(path.relative_to(root).as_posix() for path in selected)
    pending = sorted(selected)
    accepted, excluded = {}, []
    while pending:
        path = pending.pop()
        projected = project_platform_source(texts[path], roots.version)
        if projected is None:
            excluded.append({"path": path.relative_to(root).as_posix(), "reason": "conditional_source_requires_preprocessing"})
            continue
        accepted[path] = projected
        # An include in a discarded version branch is not a donor for this
        # platform. Unresolved consumers cannot authorize their include closure.
        for include in _INCLUDE_RE.findall(_strip_c_comments(projected)):
            for candidate in (path.parent / include, *(root / source / include for source in roots.source_roots)):
                candidate = candidate.resolve()
                if candidate in texts:
                    if candidate not in selected:
                        selected.add(candidate)
                        pending.append(candidate)
                    break

    return accepted, {
        "protocol": "sotn-donor-source-coverage-v1",
        "version": roots.version,
        "translation_units": translation_units,
        "missing_translation_units": sorted(missing),
        "included_source_files": sorted(path.relative_to(root).as_posix() for path in selected),
        "excluded_source_files": sorted(excluded, key=lambda item: item["path"]),
        "projection": {"protocol": PROJECTION_PROTOCOL, "defined_macros": _platform_macros(roots.version)},
        "assembly_coverage": "not_captured",
    }
