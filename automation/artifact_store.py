#!/usr/bin/env python3
"""Immutable history plus one atomic stable view for generated C evidence.

Candidate, rejection, and permuter-seed writers all use this store. The stable
top-level path supports non-recursive discovery; the returned version path is
the durable identity recorded in queue evidence. Existing bytes are archived
before replacement and no history generation is overwritten.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_RECORD_ID = re.compile(r"^[A-Za-z0-9_.-]+:[A-Za-z0-9_./-]+:[A-Za-z0-9_.$-]+$")
_PARENT_RELATIVE_INCLUDE = re.compile(
    r'^\s*#\s*include\s+"(?:\.\./)+', re.MULTILINE)


def history_versions(path: str | Path) -> list[Path]:
    """Immutable versions for one stable artifact path, in numeric order."""
    stable = Path(path)
    directory = stable.parent / "history"
    if not directory.is_dir():
        return []
    pattern = re.compile(
        rf"^{re.escape(stable.stem)}\.v([0-9]+){re.escape(stable.suffix)}$")
    versions = []
    for item in directory.iterdir():
        match = pattern.fullmatch(item.name) if item.is_file() else None
        if match:
            versions.append((int(match.group(1)), item))
    return [item for _number, item in sorted(versions)]


def write_history_version(path: str | Path, data: bytes) -> Path:
    """Write one immutable version and return its absolute path."""
    stable = Path(path)
    directory = stable.parent / "history"
    directory.mkdir(parents=True, exist_ok=True)
    existing = history_versions(stable)
    version = 1
    if existing:
        match = re.search(
            r"\.v([0-9]+)" + re.escape(stable.suffix) + r"$",
            existing[-1].name)
        if match:
            version = int(match.group(1)) + 1
    while True:
        candidate = directory / f"{stable.stem}.v{version:04d}{stable.suffix}"
        try:
            with candidate.open("xb") as handle:
                handle.write(data)
            return candidate
        except FileExistsError:
            version += 1


def publish_versioned_artifact(
        path: str | Path, text: str, label: str, repo_root: str | Path) -> str:
    """Preserve a generation, atomically refresh stable, and return its repo path."""
    stable = Path(path)
    root = Path(repo_root)
    stable.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    versions = history_versions(stable)
    archived = None
    if stable.is_file():
        current = stable.read_bytes()
        if not any(version.read_bytes() == current for version in versions):
            archived = write_history_version(stable, current)

    version_path = write_history_version(stable, data)
    temp_path = None
    try:
        fd, raw_temp = tempfile.mkstemp(
            prefix=f".{stable.name}.", suffix=".tmp", dir=stable.parent)
        temp_path = Path(raw_temp)
    except OSError as exc:
        print(f"  !! {label} version saved but stable view was not refreshed: "
              f"{exc}", flush=True)
        return version_path.relative_to(root).as_posix()
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        temp_path.replace(stable)
        temp_path = None
    except OSError as exc:
        print(f"  !! {label} version saved but stable view was not refreshed: "
              f"{exc}", flush=True)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    if archived is not None:
        print(f"  -> prior {label} archived: "
              f"{archived.relative_to(root).as_posix()}", flush=True)
    return version_path.relative_to(root).as_posix()


def candidate_path(record_id: str, repo_root: str | Path = REPO) -> Path:
    """The single stable candidate path owned by one exact queue record."""
    if not _RECORD_ID.fullmatch(record_id or ""):
        raise ValueError("record id must be an exact build:overlay:function id")
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", record_id).strip("_")
    return Path(repo_root) / "automation" / "candidates" / f"{slug}.c"


def publish_candidate_file(
        record_id: str, source_file: str | Path,
        repo_root: str | Path = REPO) -> dict:
    """Publish one complete C artifact without accepting an output path."""
    root = Path(repo_root).resolve()
    source = (root / source_file).resolve()
    if source != root and root not in source.parents:
        raise ValueError("source file must resolve inside the repo")
    if source == root / ".git" or root / ".git" in source.parents:
        raise ValueError("source file cannot be inside .git")
    if not source.is_file() or source.suffix != ".c":
        raise ValueError("source file must be an existing in-repo .c file")
    text = source.read_text(encoding="utf-8")
    if _PARENT_RELATIVE_INCLUDE.search(text):
        raise ValueError(
            "candidate source must use publish-ready includes, not parent-relative "
            "scratch paths")
    function = record_id.rsplit(":", 1)[-1]
    if not re.search(
            rf"\b{re.escape(function)}\s*\([^;{{}}]*\)\s*{{", text,
            re.DOTALL):
        raise ValueError(f"source file does not define {function}")
    stable = candidate_path(record_id, root)
    version = publish_versioned_artifact(
        stable, text, "candidate", root)
    return {
        "record": record_id,
        "source": source.relative_to(root).as_posix(),
        "stable": stable.relative_to(root).as_posix(),
        "version": version,
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        stable = root / "automation" / "candidates" / "seed.c"
        first = publish_versioned_artifact(stable, "first\n", "seed", root)
        checks = [
            (first.endswith("history/seed.v0001.c"), "first version is v0001"),
            (stable.read_text() == "first\n", "stable view matches first version"),
        ]
        stable.write_text("manual prior bytes\n")
        second = publish_versioned_artifact(stable, "second\n", "seed", root)
        versions = history_versions(stable)
        checks += [
            (second.endswith("history/seed.v0003.c"),
             "unrepresented stable bytes are archived before the next version"),
            ([item.read_text() for item in versions] ==
             ["first\n", "manual prior bytes\n", "second\n"],
             "every generation remains byte-identical and ordered"),
            (stable.read_text() == "second\n", "stable view refreshes atomically"),
        ]
        incoming = root / "automation" / "logs" / "incoming.c"
        incoming.parent.mkdir(parents=True)
        incoming.write_text("void Function(void) {}\n")
        published = publish_candidate_file(
            "us:ST/TEST:Function", incoming, root)
        candidate = root / published["stable"]
        checks += [
            (published["version"].endswith(
                "history/us_ST_TEST_Function.v0001.c"),
             "candidate publication returns its immutable generation"),
            (candidate.read_text() == incoming.read_text(),
             "candidate stable view is derived from the exact source bytes"),
        ]
        try:
            publish_candidate_file(
                "us:ST/TEST:Function", root.parent / "outside.c", root)
            escaped = False
        except ValueError:
            escaped = True
        checks.append((escaped, "candidate publication rejects escaping sources"))
        incoming.write_text('#include "../../../src/test.h"\nvoid Function(void) {}\n')
        try:
            publish_candidate_file("us:ST/TEST:Function", incoming, root)
            parent_relative = False
        except ValueError:
            parent_relative = True
        checks.append((
            parent_relative,
            "candidate publication rejects parent-relative scratch includes"))
    failed = [label for ok, label in checks if not ok]
    for ok, label in checks:
        print(("  ok   " if ok else "  FAIL ") + label)
    if failed:
        print(f"artifact_store self-test: {len(failed)} failure(s)")
        return 1
    print("artifact_store self-test: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    publish = subparsers.add_parser(
        "publish-candidate",
        help="publish one in-repo C file under its exact queue record id")
    publish.add_argument("--id", required=True)
    publish.add_argument("--from-file", required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.command == "publish-candidate":
        try:
            result = publish_candidate_file(args.id, args.from_file)
        except (OSError, UnicodeError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, sort_keys=True))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
