"""Configured translation-unit membership for immutable source donor scans.

Directory membership alone is not platform membership. Splat shares src/dra
and src/st between builds with different C translation units. Only configured
units and their quoted include closure can supply source donor functions.
"""
from __future__ import annotations

import re
from pathlib import Path


def configured_source_texts(roots, *, root: Path, texts: dict[Path, str]):
    from automation.search_donor_scan import _load_config, _INCLUDE_RE

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
    while pending:
        path = pending.pop()
        for include in _INCLUDE_RE.findall(texts[path]):
            for candidate in (path.parent / include, *(root / source / include for source in roots.source_roots)):
                candidate = candidate.resolve()
                if candidate in texts:
                    if candidate not in selected:
                        selected.add(candidate)
                        pending.append(candidate)
                    break

    accepted, excluded = {}, []
    for path in sorted(selected):
        text = texts[path]
        # Until a version-aware preprocessor is bound to the snapshot, neither
        # branch of an unresolved conditional is admissible semantic evidence.
        # Keep its original bytes and record the exclusion, rather than scan
        # mutually exclusive bodies as simultaneous platform implementations.
        if re.search(r"^\s*#\s*(?:if|ifdef|ifndef)\b", text, re.M):
            excluded.append({"path": path.relative_to(root).as_posix(), "reason": "conditional_source_requires_preprocessing"})
        else:
            accepted[path] = text
    return accepted, {
        "protocol": "sotn-donor-source-coverage-v1",
        "version": roots.version,
        "translation_units": translation_units,
        "missing_translation_units": sorted(missing),
        "included_source_files": sorted(path.relative_to(root).as_posix() for path in selected),
        "excluded_source_files": excluded,
        "assembly_coverage": "not_captured",
    }
