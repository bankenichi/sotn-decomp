#!/usr/bin/env bash
#
# start_fleet.sh: launch N volume-engine workers in parallel, each grinding the
# queue via automation/worker.py. Logs go to automation/wt/logs/.
#
# Usage:
#   automation/start_fleet.sh [N] [--max M]
#     N        number of workers (default 3)
#     --max M  max functions per worker (default: until queue empty)
#
# Env passed through to workers: OPENCODE_CMD, OPENCODE_MODEL, OPENCODE_MODEL_T1,
# OPENCODE_AGENT, OPENCODE_CONFIG, MAX_ITERS, NEAR_THRESHOLD, RUN_TIMEOUT,
# WORKER_DRYRUN. See worker.py.
set -euo pipefail

N="${1:-3}"; shift || true
MAXARG=()
if [ "${1:-}" = "--max" ]; then MAXARG=(--max "${2:?}"); fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOGDIR="$REPO_ROOT/automation/wt/logs"
mkdir -p "$LOGDIR"

echo "starting $N workers (logs in $LOGDIR)"
pids=()
for i in $(seq 1 "$N"); do
  WORKER_NAME="fleet-$i" python3 "$REPO_ROOT/automation/worker.py" loop "${MAXARG[@]}" \
    > "$LOGDIR/worker-$i.log" 2>&1 &
  pids+=($!)
  echo "  worker $i pid $!"
done

echo "waiting on workers (Ctrl-C to stop; workers finish their current function)"
wait "${pids[@]}"
echo "fleet done"
