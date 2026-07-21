#!/usr/bin/env bash
#
# gitexclude.sh: keep automation scratch state out of git without touching the
# tracked .gitignore (so your fork stays clean for upstream PRs).
#
# Adds work/ and automation/wt/ to .git/info/exclude in your real clone.
#
# Usage:  bash automation/setup/gitexclude.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXCLUDE="$REPO_ROOT/.git/info/exclude"

if [ ! -f "$EXCLUDE" ]; then
  echo "no $EXCLUDE (is this a git clone?)"; exit 1
fi

for pat in "work/" "automation/wt/" "RESULT.json" ".claude/"; do
  if ! grep -qxF "$pat" "$EXCLUDE"; then
    echo "$pat" >> "$EXCLUDE"
    echo "excluded: $pat"
  else
    echo "already excluded: $pat"
  fi
done
