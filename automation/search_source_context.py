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
