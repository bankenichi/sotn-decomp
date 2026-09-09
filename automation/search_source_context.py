"""Target-scoped preprocessing for archived translation-unit candidates."""
from __future__ import annotations

from pathlib import Path
import re


def candidate_belongs_to_recipient(source: str, path: Path, recipient_id: str) -> bool:
    """Reject explicitly foreign preserved translation units, retaining files."""
    records = re.findall(r"^\s*(?:\*\s*)?record\s*:\s*(\S+)", source, re.M | re.I)
    if records:
        return recipient_id in records
    if re.match(r"^(us|hd|pspeu|saturn)_", path.stem):
        prefix = recipient_id.replace(":", "_").replace("/", "_")
        return (path.stem == prefix or path.stem.startswith(prefix + "_")
                or re.fullmatch(re.escape(prefix) + r"\.v[0-9]+", path.stem) is not None)
    return True


def overlay_include_arguments(repo: Path, recipient_id: str | None) -> tuple[str, ...]:
    """Resolve the source overlay from the manifest recipient, never a search.

    Factory source evidence hashes src/ and include/, so these headers are
    covered by the same pre-dispatch drift check as the target source tree.
    """
    if recipient_id is None:
        return ()
    parts = recipient_id.split(":")
    if len(parts) != 3 or not re.fullmatch(r"[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*", parts[1]):
        raise ValueError("preprocessing requires a canonical recipient overlay")
    source_root = (repo / "src").resolve()
    directory = source_root.joinpath(*parts[1].lower().split("/"))
    if not directory.resolve().is_relative_to(source_root):
        raise ValueError("recipient include directory escapes the source root")
    return ("-iquote", str(directory))


def preprocess_for_mutation(source: str, recipient_id: str, expected_identity: str, temporary_root: Path) -> str:
    """Use the target preprocessor and archived recipient context for the AST."""
    from .compiler_corpus import ROOT, _pipeline, _run_stage, CompilerCorpusError

    pipeline = _pipeline()
    if pipeline.identity.identity != expected_identity:
        raise CompilerCorpusError("seed preprocessor differs from the immutable compiler binding")
    stage = (*pipeline.stages[0], *overlay_include_arguments(ROOT, recipient_id), "-P", "-DPERMUTER")
    return _run_stage(
        stage, source.encode("utf-8"), cwd=ROOT, temporary_root=temporary_root,
        label="target-seed-preprocessor", source_name="candidate",
    ).decode("utf-8")


TARGET_CONTEXT_PROTOCOL = "sotn-us-target-context-v1"


def target_declaration(text: str, symbol: str) -> tuple[dict, str]:
    """Extract a named top-level declaration, never a local scope or a guess."""
    # Mask comments and strings without moving offsets or interpreting braces
    # inside literals. Function bodies and struct members are excluded by depth.
    tokens = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    scrubbed = tokens.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), text)
    pattern = re.compile(r"(?m)(?:^|(?<=[;{}]))[ \t]*(?P<ret>[A-Za-z_][\w \t\n*]*?)\b" + re.escape(symbol) + r"\s*\((?P<params>[^();{}]*)\)\s*(?P<end>[;{])")
    cursor, depth, facts = 0, 0, []
    unsupported = False
    for match in pattern.finditer(scrubbed):
        prefix = scrubbed[cursor:match.start()]
        depth += prefix.count("{") - prefix.count("}")
        cursor = match.start()
        if depth != 0:
            continue
        result_type = " ".join(match["ret"].split())
        if "typedef" in result_type.split():
            unsupported = True
            continue
        result_type = re.sub(r"^(?:(?:static|extern|inline)\s+)+", "", result_type)
        result_type = re.sub(r"\s*\*\s*", "*", result_type)
        raw = match["params"].strip()
        parameters = []
        valid = bool(raw)
        if raw != "void":
            for entry in raw.split(","):
                # Normalize stars before separating the final identifier, so
                # Entity* self and Entity *self retain the same pointer type.
                normalized = re.sub(r"\*\s*", "* ", entry.strip())
                parts = normalized.rsplit(None, 1)
                if len(parts) != 2 or parts[-1] in {"void", "char", "short", "int", "long", "float", "double", "signed", "unsigned", "const", "volatile", "struct", "union", "enum"} or not re.fullmatch(r"[A-Za-z_]\w*", parts[1]):
                    valid = False
                    break
                kind = re.sub(r"\s*\*\s*", "*", " ".join(parts[0].split()))
                if not re.fullmatch(r"[A-Za-z_]\w*(?: [A-Za-z_]\w*)*\**", kind) or kind in {"void", "const", "volatile", "struct", "union", "enum"}:
                    valid = False
                    break
                parameters.append({"type": kind, "name": parts[1]})
        if not valid or len({p["name"] for p in parameters}) != len(parameters):
            unsupported = True
            continue
        facts.append((match["end"] == "{", {"return_type": result_type, "parameters": parameters}))
    if unsupported:
        return {}, "unsupported_declaration"
    if not facts:
        return {}, "declaration_missing"
    signatures = {(d["return_type"], tuple(p["type"] for p in d["parameters"])) for _, d in facts}
    if len(signatures) != 1:
        return {}, "ambiguous_declaration"
    # Definition names take precedence over prototype names with identical ABI.
    return max(facts, key=lambda item: item[0])[1], "declared"


def preprocess_target_context(repo: Path, source: bytes, directory: Path, expected_identity: str, config_path: Path) -> bytes:
    from .compiler_corpus import _pipeline, _run_stage, CompilerCorpusError
    import tempfile

    pipeline = _pipeline(config_path=config_path)
    if pipeline.identity.identity != expected_identity:
        raise CompilerCorpusError("target context preprocessor differs from immutable compiler binding")
    with tempfile.TemporaryDirectory(prefix="us-target-context-") as temporary:
        return _run_stage((*pipeline.stages[0], "-P", "-DPERMUTER", "-iquote", str(directory)), source,
                          cwd=repo, temporary_root=Path(temporary), label="target-context-preprocessor", source_name="target-context")


def capture_target_context(repo, record_id, assembly_path, compiler_identity, config_path):
    from .search_types import ArtifactRef, hash_bytes
    from .search_run_factory import _safe_repo_file

    version, overlay, symbol = record_id.split(":")
    if version != "us":
        raise ValueError("target context requires US recipient")
    relative = Path("src").joinpath(*overlay.lower().split("/"), Path(assembly_path).parent.name + ".c")
    evidence = {"protocol": TARGET_CONTEXT_PROTOCOL, "record_id": record_id,
                "compiler_identity": compiler_identity, "path": relative.as_posix(), "status": "source_missing"}
    path = repo / relative
    if not path.exists() and not path.is_symlink():
        return {"context_evidence": evidence}, ()
    path = _safe_repo_file(repo, relative.as_posix(), "target context source")
    raw = path.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("target context exceeds archive bound")
    context = preprocess_target_context(repo, raw, path.parent, compiler_identity, config_path)
    if len(raw) > 8 * 1024 * 1024 or len(context) > 8 * 1024 * 1024:
        raise ValueError("target context exceeds archive bound")
    facts, status = target_declaration(context.decode("utf-8"), symbol)
    artifacts = []
    for key, category, data in (("input", "target-context-input", raw), ("preprocessed", "target-context", context)):
        digest = hash_bytes(data)
        reference = ArtifactRef(digest, "artifacts/" + category + "/" + digest[7:] + ".c", "text/x-c", len(data))
        evidence[key] = reference.to_dict()
        artifacts.append((category, reference, data))
    evidence["status"] = status
    return {**facts, "context_evidence": evidence}, tuple(artifacts)


def verify_target_context(declarations, archive, record_id, compiler_identity, assembly_path):
    """Reconstruct captured declaration facts using archived bytes only."""
    from .search_types import ArtifactRef

    evidence = declarations.get("context_evidence")
    if evidence is None:  # Preserved archives predate target-context capture.
        return
    base = {"protocol", "record_id", "compiler_identity", "path", "status"}
    if not isinstance(evidence, dict):
        evidence = dict(evidence)
    missing = evidence.get("status") == "source_missing"
    if set(evidence) != (base if missing else base | {"input", "preprocessed"}):
        raise ValueError("target context fields differ")
    if (evidence["protocol"] != TARGET_CONTEXT_PROTOCOL or evidence["record_id"] != record_id
            or evidence["compiler_identity"] != compiler_identity or not record_id.startswith("us:")):
        raise ValueError("target context bindings differ")
    overlay = record_id.split(":")[1].lower()
    path = Path(evidence["path"])
    if path.is_absolute() or ".." in path.parts or "\\" in evidence["path"] or path.parent.as_posix() != "src/" + overlay or path.suffix != ".c":
        raise ValueError("target context path differs from recipient")
    if path.name != Path(assembly_path).parent.name + ".c":
        raise ValueError("target context translation unit differs from assembly")
    if missing:
        if set(declarations) != {"context_evidence"}:
            raise ValueError("missing target context supplied declaration facts")
        return
    values = {}
    for key, category in (("input", "target-context-input"), ("preprocessed", "target-context")):
        ref = ArtifactRef.from_dict(evidence[key])
        if ref.path != "artifacts/" + category + "/" + ref.content_hash[7:] + ".c" or ref.media_type != "text/x-c" or ref.byte_size > 8 * 1024 * 1024:
            raise ValueError("target context artifact is not canonical")
        values[key] = archive.verify(ref)
    facts, status = target_declaration(values["preprocessed"].decode("utf-8"), record_id.split(":")[2])
    if status != evidence["status"] or {k: v for k, v in declarations.items() if k != "context_evidence"} != facts:
        raise ValueError("target declarations differ from archived context")


def verify_target_context_source(declarations, source_document):
    """Bind captured input to the source snapshot taken before preprocessing."""
    evidence = declarations.get("context_evidence")
    if evidence is None:
        return
    entries = [item for item in source_document["files"] if item["path"] == evidence["path"]]
    if evidence["status"] == "source_missing":
        if entries:
            raise ValueError("target context source disappeared during capture")
    elif (len(entries) != 1 or any(entries[0][key] != evidence["input"][key]
                                  for key in ("content_hash", "byte_size"))):
        raise ValueError("target context input differs from frozen source evidence")
