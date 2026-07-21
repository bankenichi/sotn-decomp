#!/usr/bin/env bash
#
# sotn_dispatch.sh: the WSL-side dispatcher behind the Windows `sotn` wrapper.
#
# Topology A: OpenCode and llama-server run natively on Windows; only the build
# toolchain and the repo live in WSL. Windows callers run `sotn <cmd> ...`,
# which forwards here via wsl.exe. Keeping the logic in bash (rather than in a
# .cmd file) means it is testable and quoting stays sane.
#
# Usage (from Windows):  sotn <subcommand> [args]
#   sotn build [version]                 make build VERSION=...
#   sotn extract [version]               make extract VERSION=...
#   sotn expected [version]              make expected VERSION=...
#   sotn clean [version]                 make clean VERSION=...
#   sotn diff <symbol> [version] [overlay]   asm-differ for one function
#   sotn permuter <dir>                  run decomp-permuter on a work dir
#   sotn permuter-import <c_file> <asm_file>
#   sotn status                          git status --short
#   sotn commit "<message>"              git add -A && git commit -m ...
#   sotn sched <args...>                 scheduler.py passthrough
#   sotn run "<raw bash>"                escape hatch, runs in the repo root
#
# Env: VERSION (default us), SOTN_REPO (default: repo containing this script)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${SOTN_REPO:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
cd "$REPO"

PY="${SOTN_PYTHON:-$REPO/.venv/bin/python}"
[ -x "$PY" ] || PY="python3"

DEFAULT_VERSION="${VERSION:-us}"

usage() {
  # Select by CONTENT, not by line number. This used to be `sed -n '7,25p'`,
  # which silently drifted as the header grew: it began mid-sentence and ran past
  # the comment block into `set -euo pipefail`, printing shell code as help text.
  awk '/^# Usage \(from Windows\)/,/^# Env:/' "${BASH_SOURCE[0]}" \
    | sed 's/^# \{0,1\}//'
  exit 2
}

sub="${1:-}"; [ -n "$sub" ] || usage
shift || true

case "$sub" in
  build|extract|expected|clean)
    v="${1:-$DEFAULT_VERSION}"
    exec make "$sub" "VERSION=$v"
    ;;
  diff)
    sym="${1:?usage: sotn diff <symbol> [version] [overlay]}"
    v="${2:-$DEFAULT_VERSION}"
    ov="${3:-dra}"
    exec "$PY" tools/asm-differ/diff.py -m --format plain \
         --version "$v" --overlay "$ov" "$sym"
    ;;
  permuter)
    d="${1:?usage: sotn permuter <work_dir>}"
    exec "$PY" tools/decomp-permuter/permuter.py "$d"
    ;;
  permuter-import)
    c="${1:?usage: sotn permuter-import <c_file> <asm_file>}"
    a="${2:?usage: sotn permuter-import <c_file> <asm_file>}"
    exec "$PY" tools/decomp-permuter/import.py "$c" "$a"
    ;;
  status)
    exec git status --short
    ;;
  commit)
    msg="${1:?usage: sotn commit \"<message>\"}"
    git add -A
    exec git commit -m "$msg"
    ;;
  sched)
    exec "$PY" automation/scheduler.py "$@"
    ;;
  run)
    raw="${1:?usage: sotn run \"<raw bash>\"}"
    exec bash -lc "$raw"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "unknown subcommand: $sub" >&2
    usage
    ;;
esac
