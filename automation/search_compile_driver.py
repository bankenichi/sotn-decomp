"""Execute the immutable PSX compiler recipe for a permuter candidate."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.compiler_corpus import (
    CompilerCorpusError, _compile_source, _pipeline,
)


def compile_file(source: Path, output: Path, expected_identity: str) -> None:
    pipeline = _pipeline()
    if pipeline.identity.identity != expected_identity:
        raise CompilerCorpusError("permuter compiler identity differs from immutable binding")
    temporary_base = Path(os.environ["TMPDIR"]).resolve(strict=True)
    for path in (source, output):
        if path.is_symlink() or not path.resolve().is_relative_to(temporary_base):
            raise CompilerCorpusError("permuter compiler path escapes isolated temporary storage")
    if source.stat().st_size > 4 * 1024 * 1024:
        raise CompilerCorpusError("permuter source exceeds the immutable size bound")
    with tempfile.TemporaryDirectory(prefix="psx-candidate-", dir=temporary_base) as directory:
        compiled, _, _ = _compile_source(
            source.read_text(encoding="utf-8"), pipeline, Path(directory), name="candidate",
        )
        output.write_bytes(compiled.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", dest="output", required=True, type=Path)
    args = parser.parse_args()
    try:
        compile_file(args.source, args.output, os.environ["SOTN_COMPILER_IDENTITY"])
    except (CompilerCorpusError, OSError, KeyError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
