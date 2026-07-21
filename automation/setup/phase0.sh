#!/usr/bin/env bash
#
# phase0.sh: run the entire Phase 0 baseline unattended and prove it matched.
#
# You place the disc image(s) in disks/. This script does everything else:
#   preflight -> extract_disk -> extract -> build -> verify every SHA-1
#
# It exits 0 ONLY if every entry in config/check.<version>.sha reports OK.
# That is the definition of a matching build, so a zero exit is a green
# baseline and anything else is a precise diagnosis of what went wrong.
#
# Usage:
#   bash automation/setup/phase0.sh                 # VERSION=us
#   bash automation/setup/phase0.sh -v pspeu
#   bash automation/setup/phase0.sh --dry-run       # show the plan, run nothing
#   bash automation/setup/phase0.sh --skip-disk     # disks/<v>/ already unpacked
#   bash automation/setup/phase0.sh --seed          # on success, seed the queue
#
# Options:
#   -v, --version <us|hd|pspeu|saturn>   target build (default: us)
#       --skip-disk                      skip extract_disk
#       --force                          make clean first
#       --seed                           seed work/queue.jsonl on success (us only)
#       --dry-run                        print stages without executing
#       --log <file>                     log file (default: build-phase0-<v>.log)
#   -h, --help
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO"

VERSION="us"
SKIP_DISK=0
FORCE=0
SEED=0
DRYRUN=0
LOG=""

while [ $# -gt 0 ]; do
  case "$1" in
    -v|--version) VERSION="${2:?--version needs a value}"; shift 2 ;;
    --skip-disk)  SKIP_DISK=1; shift ;;
    --force)      FORCE=1; shift ;;
    --seed)       SEED=1; shift ;;
    --dry-run)    DRYRUN=1; shift ;;
    --log)        LOG="${2:?--log needs a value}"; shift 2 ;;
    -h|--help)    sed -n '3,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
done

case "$VERSION" in
  us|hd|pspeu|saturn) ;;
  *) echo "version must be one of: us hd pspeu saturn" >&2; exit 2 ;;
esac
[ -n "$LOG" ] || LOG="build-phase0-${VERSION}.log"

# ---- output helpers ---------------------------------------------------------
if [ -t 1 ]; then C_OK=$'\033[1;32m'; C_ER=$'\033[1;31m'; C_IN=$'\033[1;36m'; C_0=$'\033[0m'
else C_OK=""; C_ER=""; C_IN=""; C_0=""; fi
say()  { printf '%s==> %s%s\n' "$C_IN" "$*" "$C_0"; }
ok()   { printf '%s  OK  %s%s\n' "$C_OK" "$*" "$C_0"; }
die()  { printf '%s FAIL %s%s\n' "$C_ER" "$*" "$C_0" >&2; exit 1; }

START_ALL=$(date +%s)

STAGE_NUM=0
STAGE_TOTAL=0
SPIN='-\|/'

term_width() {
  local w="${COLUMNS:-}"
  [ -n "$w" ] || w="$(tput cols 2>/dev/null)"
  [ -n "$w" ] || w=100
  echo "$w"
}

draw_bar() { # draw_bar <done> <total> [width]
  local d="$1" t="$2" w="${3:-16}" filled i out=""
  [ "$t" -gt 0 ] 2>/dev/null || t=1
  filled=$(( d * w / t )); [ "$filled" -gt "$w" ] && filled=$w
  for ((i = 0; i < w; i++)); do
    if [ "$i" -lt "$filled" ]; then out="$out#"; else out="$out."; fi
  done
  printf '[%s] %d/%d' "$out" "$d" "$t"
}

# Run a stage with a live progress line: overall bar, spinner, elapsed time, and
# the most recent line of build output. Falls back to periodic plain lines when
# stdout is not a terminal (piped or redirected).
stage() { # stage "label" cmd...
  local label="$1"; shift
  STAGE_NUM=$((STAGE_NUM + 1))

  if [ "$DRYRUN" = 1 ]; then
    printf '%s==> %s %s%s\n' "$C_IN" "$(draw_bar "$STAGE_NUM" "$STAGE_TOTAL")" "$label" "$C_0"
    echo "    [dry-run] $*"
    return 0
  fi

  local t0 pid rc i=0 w el mm ss last line
  t0=$(date +%s)
  "$@" >>"$LOG" 2>&1 &
  pid=$!

  if [ -t 1 ]; then
    while kill -0 "$pid" 2>/dev/null; do
      w=$(term_width)
      el=$(( $(date +%s) - t0 )); mm=$((el / 60)); ss=$((el % 60))
      last="$(tail -n 1 "$LOG" 2>/dev/null | tr -d '\r' | tr -cd '[:print:]')"
      line="$(draw_bar "$STAGE_NUM" "$STAGE_TOTAL") ${SPIN:i++%4:1} $(printf '%02d:%02d' "$mm" "$ss") $label"
      [ -n "$last" ] && line="$line | $last"
      printf '\r%s%-*.*s%s' "$C_IN" $((w - 1)) $((w - 1)) "$line" "$C_0"
      sleep 0.5
    done
  else
    while kill -0 "$pid" 2>/dev/null; do
      el=$(( $(date +%s) - t0 ))
      [ $((el % 30)) -eq 0 ] && [ "$el" -gt 0 ] && \
        printf '    ... %s still running (%ds)\n' "$label" "$el"
      sleep 1
    done
  fi

  wait "$pid"; rc=$?
  el=$(( $(date +%s) - t0 )); mm=$((el / 60)); ss=$((el % 60))
  [ -t 1 ] && printf '\r%*s\r' "$(( $(term_width) - 1 ))" ''

  if [ "$rc" -ne 0 ]; then
    printf '%s %s FAILED after %02d:%02d%s\n' "$C_ER" "$label" "$mm" "$ss" "$C_0" >&2
    echo "--- last 40 lines of $LOG ---" >&2
    tail -40 "$LOG" >&2
    die "$label failed. Full log: $LOG"
  fi
  printf '%s  ok  %s %s (%02d:%02d)%s\n' "$C_OK" \
    "$(draw_bar "$STAGE_NUM" "$STAGE_TOTAL")" "$label" "$mm" "$ss" "$C_0"
}

# ---- 1. preflight -----------------------------------------------------------
say "Preflight"

[ -f Makefile ] && [ -d config ] || die "not in the sotn-decomp repo root ($REPO)"

missing=""
need() { command -v "$1" >/dev/null 2>&1 || missing="$missing $1"; }
need make; need git; need python3; need go
case "$VERSION" in
  us|hd)     need mipsel-linux-gnu-gcc ;;
esac
case "$VERSION" in
  pspeu|hd)  need 7z ;;
  saturn)    need bchunk; need sh-elf-ld || true ;;
esac
[ -n "$missing" ] && die "missing tools:$missing
Run: bash automation/setup/install_wsl2.sh"

[ -x .venv/bin/python ] || die "no .venv found. Run: bash automation/setup/install_wsl2.sh"

SHATOOL=""
command -v shasum   >/dev/null 2>&1 && SHATOOL="shasum"
[ -n "$SHATOOL" ] || { command -v sha1sum >/dev/null 2>&1 && SHATOOL="sha1sum"; }
[ -n "$SHATOOL" ] || die "neither shasum nor sha1sum is available"

SHA_FILE="config/check.${VERSION}.sha"
[ -f "$SHA_FILE" ] || die "missing $SHA_FILE (unknown target?)"
EXPECTED=$(grep -c '[^[:space:]]' "$SHA_FILE")
ok "toolchain present, $SHATOOL available, $EXPECTED hashes to verify"

# Native helper tools that the generated ninja rules invoke but that `make
# build` never builds. tools/builds/gen.py pipes every compile through
# sotn_str, yet sotn_str is only produced by the `update-dependencies` target.
# Build it here so the pipeline is self-sufficient.
SOTN_STR="tools/sotn_str/target/release/sotn_str"
NEED_SOTN_STR=0
if [ ! -x "$SOTN_STR" ]; then
  NEED_SOTN_STR=1
  command -v cargo >/dev/null 2>&1 || die "$SOTN_STR is missing and cargo is not
installed, so it cannot be built. Run: rustup default stable
(or re-run bash automation/setup/install_wsl2.sh)"
  ok "$SOTN_STR missing; will build it (cargo present)"
else
  ok "sotn_str present"
fi

# ---- 2. required disc images ------------------------------------------------
say "Checking for your disc image(s) in disks/"
required=""
case "$VERSION" in
  us)     required="disks/sotn.us.cue disks/sotn.us.bin" ;;
  hd)     required="disks/sotn.pspeu.iso" ;;
  pspeu)  required="disks/sotn.pspeu.iso" ;;
  saturn) required="disks/sotn.saturn.bin disks/sotn.saturn.cue" ;;
esac
absent=""
for f in $required; do [ -f "$f" ] || absent="$absent $f"; done
if [ -n "$absent" ]; then
  die "missing required file(s):$absent

Place the image(s) from the disc you own at exactly those paths, then re-run.
See Getting-Started.md section 1 for per-target filenames and how the Makefile
consumes them."
fi
for f in $required; do ok "found $f ($(du -h "$f" | cut -f1))"; done

# ---- 2b. validate (and repair) the cue sheet --------------------------------
# A dumper writes its own filenames into the cue. Renaming the data track to
# sotn.<v>.bin without updating the cue leaves TRACK 01 pointing at a file that
# no longer exists, which surfaces as a Go panic deep in extract_disk. Detect
# that here and fix it, since it is unambiguous.
CUE="disks/sotn.${VERSION}.cue"
if [ -f "$CUE" ]; then
  say "Validating $CUE"

  # Windows-authored cues often have CRLF; trailing \r corrupts the filename.
  if grep -q $'\r' "$CUE" 2>/dev/null; then
    if [ "$DRYRUN" = 1 ]; then
      echo "    [dry-run] would strip CRLF line endings from $CUE"
    else
      cp -n "$CUE" "$CUE.bak" 2>/dev/null || true
      sed -i 's/\r$//' "$CUE"
      ok "normalized CRLF line endings (backup: $CUE.bak)"
    fi
  fi

  CUE_FILE="$(grep -iE '^[[:space:]]*FILE' "$CUE" | head -1 \
              | sed -E 's/^[[:space:]]*[Ff][Ii][Ll][Ee][[:space:]]+"([^"]+)".*/\1/')"
  DATA_BIN="sotn.${VERSION}.bin"

  if [ -z "$CUE_FILE" ]; then
    die "$CUE has no FILE line; it is not a usable cue sheet"
  elif [ -f "disks/$CUE_FILE" ]; then
    ok "track 1 references $CUE_FILE (present)"
  elif [ -f "disks/$DATA_BIN" ]; then
    if [ "$DRYRUN" = 1 ]; then
      echo "    [dry-run] would repoint track 1 from '$CUE_FILE' to '$DATA_BIN'"
    else
      cp -n "$CUE" "$CUE.bak" 2>/dev/null || true
      awk -v new="$DATA_BIN" '
        BEGIN { done = 0 }
        /^[[:space:]]*[Ff][Ii][Ll][Ee]/ && !done { sub(/"[^"]+"/, "\"" new "\""); done = 1 }
        { print }' "$CUE" > "$CUE.tmp" && mv "$CUE.tmp" "$CUE"
      ok "repaired: track 1 now references $DATA_BIN (was '$CUE_FILE', backup: $CUE.bak)"
    fi
  else
    die "$CUE references '$CUE_FILE', which does not exist in disks/, and no
$DATA_BIN is present either. Put the data track at disks/$DATA_BIN."
  fi

  CUE_MODE="$(grep -iE '^[[:space:]]*TRACK' "$CUE" | head -1 | awk '{print $3}')"
  case "$CUE_MODE" in
    MODE1/2048|MODE2/2352) ok "track 1 mode $CUE_MODE" ;;
    "") warn "could not read track 1 mode from $CUE" ;;
    *) die "track 1 mode is '$CUE_MODE'; the extractor accepts only MODE1/2048
or MODE2/2352. Re-dump the disc in raw mode." ;;
  esac
fi

# ---- 3. build pipeline ------------------------------------------------------
: > "$LOG"
say "Logging to $LOG"

# stages: [sotn_str] + [clean] + [extract_disk] + extract + build + verify + [seed]
STAGE_TOTAL=3
[ "$NEED_SOTN_STR" = 1 ] && STAGE_TOTAL=$((STAGE_TOTAL + 1))
[ "$FORCE" = 1 ] && STAGE_TOTAL=$((STAGE_TOTAL + 1))
[ "$SKIP_DISK" = 0 ] && STAGE_TOTAL=$((STAGE_TOTAL + 1))
[ "$SEED" = 1 ] && [ "$VERSION" = "us" ] && STAGE_TOTAL=$((STAGE_TOTAL + 1))

# A previous run that died mid-compile (for example with sotn_str missing) can
# leave zero-byte .o files behind. Ninja treats them as up to date, and the
# link then fails with undefined references to engine symbols. Detect that
# precise symptom and clear the object tree rather than let it recur.
if [ -d "build/$VERSION" ] && [ "$DRYRUN" = 0 ]; then
  EMPTY_OBJS=$(find "build/$VERSION" -type f -name '*.o' -size 0 2>/dev/null | wc -l)
  if [ "$EMPTY_OBJS" -gt 0 ]; then
    warn "found $EMPTY_OBJS zero-byte object file(s) from an earlier failed build"
    rm -rf "build/$VERSION"
    ok "cleared build/$VERSION so this run recompiles cleanly"
  fi
fi

if [ "$NEED_SOTN_STR" = 1 ]; then
  stage "cargo build sotn_str (required by every compile step)" \
        cargo build --release --manifest-path ./tools/sotn_str/Cargo.toml
  [ "$DRYRUN" = 1 ] || [ -x "$SOTN_STR" ] || die "cargo reported success but
$SOTN_STR still does not exist"
fi

[ "$FORCE" = 1 ] && stage "make clean" make clean "VERSION=$VERSION"

if [ "$SKIP_DISK" = 0 ]; then
  stage "make extract_disk (unpack disc into disks/$VERSION/)" \
        make extract_disk "VERSION=$VERSION"
else
  say "Skipping extract_disk (--skip-disk)"
fi

stage "make extract (assets per config/assets.$VERSION.yaml)" \
      make extract "VERSION=$VERSION"

stage "make build" make build "VERSION=$VERSION"

# ---- 4. verify every hash ---------------------------------------------------
STAGE_NUM=$((STAGE_NUM + 1))
printf '%s==> %s Verifying %s hashes from %s%s\n' \
  "$C_IN" "$(draw_bar "$STAGE_NUM" "$STAGE_TOTAL")" "$EXPECTED" "$SHA_FILE" "$C_0"
if [ "$DRYRUN" = 1 ]; then
  echo "    [dry-run] $SHATOOL -c $SHA_FILE"
else
  VERIFY_OUT="$($SHATOOL -c "$SHA_FILE" 2>&1)" || true
  printf '%s\n' "$VERIFY_OUT" >>"$LOG"
  N_OK=$(printf '%s\n' "$VERIFY_OUT" | grep -c ': OK$' || true)
  N_BAD=$(printf '%s\n' "$VERIFY_OUT" | grep -cE ': (FAILED|No such file or directory)' || true)

  if [ "$N_OK" = "$EXPECTED" ] && [ "$N_BAD" = 0 ]; then
    ok "$N_OK/$EXPECTED OK"
  else
    echo >&2
    printf '%s\n' "$VERIFY_OUT" | grep -vE ': OK$' | head -20 >&2
    die "$N_OK/$EXPECTED matched, $N_BAD failed.
The build completed but does NOT match the reference, so this is not a valid
baseline. Do not start the fleet. Full output: $LOG"
  fi
fi

# ---- 5. optional queue seed -------------------------------------------------
if [ "$SEED" = 1 ]; then
  if [ "$VERSION" != "us" ]; then
    say "Skipping --seed (seed.us.txt is for the us target)"
  elif [ "$DRYRUN" = 1 ]; then
    echo "    [dry-run] python3 automation/scheduler.py init --from automation/queue/seed.us.txt"
  else
    stage "seed work/queue.jsonl" \
          python3 automation/scheduler.py init --from automation/queue/seed.us.txt
    python3 automation/scheduler.py stats || true
  fi
fi

# ---- done -------------------------------------------------------------------
END_ALL=$(date +%s)
echo
if [ "$DRYRUN" = 1 ]; then
  say "Dry run complete. Nothing was executed."
  exit 0
fi
printf '%sPHASE 0 GREEN%s  target=%s  %s/%s hashes OK  total %ss\n' \
       "$C_OK" "$C_0" "$VERSION" "$N_OK" "$EXPECTED" "$((END_ALL-START_ALL))"
echo "Baseline matches the reference. You can start function work."
echo "Next, from PowerShell: python automation\\win\\worker_direct.py once"
echo "      (or 'loop --max 20' to keep going). Queue: scheduler.py stats"
