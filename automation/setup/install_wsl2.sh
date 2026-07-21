#!/usr/bin/env bash
#
# install_wsl2.sh: one-shot bootstrap for the SOTN decomp on Windows + WSL2.
#
# Single-tree layout: the repo lives in your Windows project directory, which
# WSL reaches through /mnt/c. Windows tools use it natively, WSL only compiles,
# and nothing is ever synced between two copies.
#
# This does EVERYTHING except the one thing that needs a human: placing the
# disc image you own into disks/. Specifically it handles:
#   - Ubuntu release guard (must be noble/24.04)
#   - /mnt metadata mount option (writes /etc/wsl.conf, tells you to restart)
#   - Debian packages, Rust, Go, dosemu2
#   - git safe.directory and core.fileMode for the Windows mount
#   - turning the directory into a real git clone if it is not one
#   - clearing stale submodule dirs and initializing submodules
#   - .git/info/exclude so images/automation/build never get committed
#   - both Python venvs (.venv and automation/mcp/.venv)
#
# Idempotent: safe to re-run at any point. Run it again after any failure.
#
# Usage:  bash automation/setup/install_wsl2.sh
# Exit codes: 0 ok, 1 error, 3 restart WSL then re-run
set -uo pipefail

GO_VERSION="${GO_VERSION:-1.24.13}"
DOSEMU_REPO="https://github.com/sozud/dosemu-deb.git"
ORIGIN_URL="${ORIGIN_URL:-https://github.com/bankenichi/sotn-decomp.git}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [ -t 1 ]; then C_OK=$'\033[1;32m'; C_ER=$'\033[1;31m'; C_IN=$'\033[1;36m'; C_WN=$'\033[1;33m'; C_0=$'\033[0m'
else C_OK=""; C_ER=""; C_IN=""; C_WN=""; C_0=""; fi
say()  { printf '\n%s==> %s%s\n' "$C_IN" "$*" "$C_0"; }
ok()   { printf '%s  ok  %s%s\n' "$C_OK" "$*" "$C_0"; }
warn() { printf '%s[warn] %s%s\n' "$C_WN" "$*" "$C_0"; }
die()  { printf '%s[fail] %s%s\n' "$C_ER" "$*" "$C_0" >&2; exit 1; }

# ---- 0. sanity --------------------------------------------------------------
say "Environment checks"
[ "$(uname -s)" = "Linux" ] || die "run this inside WSL2, not $(uname -s)"
[ -f Makefile ] && [ -d config ] || die "not the sotn-decomp repo root ($REPO_ROOT)"

if grep -qi docker-desktop /proc/sys/kernel/hostname 2>/dev/null; then
  die "you are in Docker Desktop's utility distro. Exit and use Ubuntu-24.04."
fi

CODENAME="$(. /etc/os-release 2>/dev/null && echo "${VERSION_CODENAME:-unknown}" || true)"
EXPECTED_CODENAME="${EXPECTED_CODENAME:-noble}"
if [ "$CODENAME" != "$EXPECTED_CODENAME" ]; then
  echo
  echo "Ubuntu release is '$CODENAME'; this project needs '$EXPECTED_CODENAME' (24.04)."
  echo "Newer releases have no candidate for gcc-mipsel-linux-gnu, so the PSX"
  echo "toolchain cannot be installed. From PowerShell:"
  echo "    wsl --install -d Ubuntu-24.04"
  echo "    wsl --set-default Ubuntu-24.04"
  [ "${SOTN_ALLOW_ANY_RELEASE:-0}" = "1" ] || exit 1
  warn "SOTN_ALLOW_ANY_RELEASE=1; continuing on '$CODENAME' at your own risk"
fi
ok "Ubuntu $CODENAME"

# ---- 1. /mnt metadata (needed for git and pip on the Windows tree) ----------
case "$REPO_ROOT" in
  /mnt/*)
    say "Windows mount check (single-tree layout)"
    if mount | grep ' /mnt/c ' | grep -q metadata; then
      ok "/mnt/c mounted with metadata"
    else
      warn "/mnt/c lacks the 'metadata' option, so chmod fails and git/pip break here."
      if [ ! -f /etc/wsl.conf ]; then
        printf '[automount]\noptions = "metadata"\n' | sudo tee /etc/wsl.conf >/dev/null
        ok "wrote /etc/wsl.conf"
      elif ! grep -q '^\s*\[automount\]' /etc/wsl.conf; then
        printf '\n[automount]\noptions = "metadata"\n' | sudo tee -a /etc/wsl.conf >/dev/null
        ok "appended [automount] to /etc/wsl.conf"
      else
        warn "/etc/wsl.conf already has [automount]; add metadata to its options line:"
        warn '    options = "metadata"'
      fi
      echo
      echo "${C_WN}ACTION NEEDED${C_0}: from PowerShell run"
      echo "    wsl --shutdown"
      echo "then reopen WSL and re-run this script. Everything after this point"
      echo "depends on it, so stopping here rather than failing halfway."
      exit 3
    fi
    ;;
  *) ok "repo on the Linux filesystem ($REPO_ROOT)" ;;
esac

# ---- 2. Debian packages -----------------------------------------------------
say "Debian packages"
DEBS="$(grep -vE '^\s*#|^\s*$' tools/requirements-debian.txt | tr '\n' ' ')"
sudo apt-get update -qq || die "apt-get update failed"
# jq for automation/qwen.sh; build tooling helps pip build wheels
sudo apt-get install -y -qq $DEBS jq build-essential python3-dev ca-certificates \
  || die "apt-get install failed (see output above)"
ok "packages installed"

# ---- 3. Rust ----------------------------------------------------------------
say "Rust"
if command -v rustup >/dev/null 2>&1; then
  rustup default stable >/dev/null 2>&1 && ok "rustup default stable" \
    || warn "rustup default stable failed; check network"
else
  warn "rustup not on PATH yet; open a new shell and run: rustup default stable"
fi

# ---- 4. Go ------------------------------------------------------------------
say "Go ${GO_VERSION}"
ARCH="$(dpkg --print-architecture)"
case "$ARCH" in amd64) GOARCH=amd64 ;; arm64) GOARCH=arm64 ;; *) die "unsupported arch $ARCH" ;; esac
if command -v go >/dev/null 2>&1 && go version 2>/dev/null | grep -q "go${GO_VERSION}"; then
  ok "already installed"
else
  TGZ="go${GO_VERSION}.linux-${GOARCH}.tar.gz"
  curl -fSL "https://go.dev/dl/${TGZ}" -o "/tmp/${TGZ}" || die "Go download failed"
  sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf "/tmp/${TGZ}" && rm -f "/tmp/${TGZ}"
  ok "installed to /usr/local/go"
fi
grep -q '/usr/local/go/bin' "$HOME/.profile" 2>/dev/null || \
  echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> "$HOME/.profile"
export PATH="$PATH:/usr/local/go/bin:$HOME/go/bin"

# ---- 5. dosemu2 -------------------------------------------------------------
say "dosemu2 (PSX compiler path)"
if command -v dosemu >/dev/null 2>&1; then
  ok "already installed"
else
  T="$(mktemp -d)"
  if git clone --depth 1 "$DOSEMU_REPO" "$T/d" >/dev/null 2>&1; then
    sudo dpkg -i "$T"/d/fdpp_*_"${ARCH}".deb        >/dev/null 2>&1 || true
    sudo dpkg -i "$T"/d/fdpp-dev_*_"${ARCH}".deb    >/dev/null 2>&1 || true
    sudo dpkg -i "$T"/d/comcom32_*_all.deb          >/dev/null 2>&1 || true
    sudo dpkg -i "$T"/d/dosemu2_*_"${ARCH}".deb     >/dev/null 2>&1 || true
    sudo apt-get -f install -y -qq >/dev/null 2>&1 || true
    command -v dosemu >/dev/null 2>&1 && ok "installed" || warn "dosemu2 install incomplete"
  else
    warn "could not clone $DOSEMU_REPO; skipping dosemu2"
  fi
  rm -rf "$T"
fi

# ---- 6. git configuration for the Windows tree ------------------------------
say "git configuration"
git config --global --get-all safe.directory 2>/dev/null | grep -qx "$REPO_ROOT" || \
  git config --global --add safe.directory "$REPO_ROOT"
ok "safe.directory registered"
case "$REPO_ROOT" in
  /mnt/*) git config --global core.fileMode false; ok "core.fileMode false (Windows mount)" ;;
esac

# ---- 7. make this directory a real git clone --------------------------------
say "Repository"
if [ ! -d .git ]; then
  warn "no .git here; initializing from $ORIGIN_URL"
  git init -q                              || die "git init failed"
  git remote add origin "$ORIGIN_URL"      || true
  git fetch --depth=1 origin               || die "git fetch failed"
  git checkout -f -B master origin/master  || die "git checkout failed"
  ok "repository initialized"
else
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "$ORIGIN_URL"
  ok "already a git repository"
fi

# ---- 8. submodules ----------------------------------------------------------
say "Submodules"
if [ -f .gitmodules ]; then
  # A previous file copy can leave these as plain directories, which blocks
  # `git submodule update` ("already exists and is not an empty directory").
  cleared=0
  while read -r p; do
    [ -n "$p" ] || continue
    if [ -d "$p" ] && [ ! -e "$p/.git" ]; then rm -rf "$p"; cleared=$((cleared+1)); fi
  done < <(git config -f .gitmodules --get-regexp path 2>/dev/null | awk '{print $2}')
  [ "$cleared" -gt 0 ] && ok "cleared $cleared stale submodule director(ies)"
  git submodule update --init --recursive >/dev/null 2>&1 \
    && ok "submodules checked out" \
    || warn "submodule update had issues; run: git submodule update --init --recursive"
fi

# ---- 9. local excludes ------------------------------------------------------
say "Local excludes (.git/info/exclude)"
if [ -d .git ]; then
  mkdir -p .git/info
  cat > .git/info/exclude <<'EOF'
# Managed by automation/setup/install_wsl2.sh
# Local automation and docs, never intended for upstream
automation/
.claude/
work/
Getting-Started.md
Home-Checklist.md
ORCHESTRATOR.md
Claude-Desktop-Harness.md
SOTN-Decomp-Assessment.md
SOTN-Decomp-Agent-Playbook.md
SOTN-Orchestration-Stack.md
SOTN-Orchestration-Action-Plan.md
# Disc images and archives: yours, large, never committed
disks/*
*.7z
*.iso
*.cue
*.bin
*.img
# Build artifacts
build/
*.log
EOF
  ok "exclude list written"
fi

# ---- 10. Python venvs -------------------------------------------------------
say "Python environments"
[ -d .venv ] || python3 -m venv .venv || die "could not create .venv"
./.venv/bin/pip install -q --upgrade pip >/dev/null 2>&1
./.venv/bin/pip install -q -r tools/requirements-python.txt || die "repo venv install failed"
# asm-differ needs colorama, which tools/requirements-python.txt omits. Without
# it diff.py exits 0 printing only a warning, so the matcher gets no feedback.
./.venv/bin/pip install -q colorama watchdog levenshtein cxxfilt >/dev/null 2>&1 \
  && ok "asm-differ prerequisites" || warn "could not install asm-differ prerequisites"
ok "repo .venv ready"

[ -d automation/mcp/.venv ] || python3 -m venv automation/mcp/.venv
./automation/mcp/.venv/bin/pip install -q --upgrade pip >/dev/null 2>&1
./automation/mcp/.venv/bin/pip install -q -r automation/mcp/requirements.txt \
  && ok "automation/mcp/.venv ready" || warn "bridge venv install failed"

# ---- 11. native helper tools the build assumes exist ------------------------
say "Native helper tools"
# tools/builds/gen.py pipes every compile through tools/sotn_str, but that
# binary is only produced by the Makefile's `update-dependencies` target, which
# `make build` does not depend on. Build it here so the build is self-sufficient.
if [ -x tools/sotn_str/target/release/sotn_str ]; then
  ok "sotn_str already built"
elif command -v cargo >/dev/null 2>&1; then
  if cargo build --release --manifest-path ./tools/sotn_str/Cargo.toml >/dev/null 2>&1; then
    ok "sotn_str built"
  else
    warn "sotn_str build failed; run manually:"
    warn "  cargo build --release --manifest-path ./tools/sotn_str/Cargo.toml"
  fi
else
  warn "cargo not on PATH; cannot build sotn_str. Run 'rustup default stable',"
  warn "open a new shell, then re-run this script."
fi

# ---- summary ----------------------------------------------------------------
say "Versions"
printf '  make      : %s\n' "$(make --version 2>/dev/null | head -1)"
printf '  mipsel gcc: %s\n' "$(mipsel-linux-gnu-gcc --version 2>/dev/null | head -1 || echo MISSING)"
printf '  clang-fmt : %s\n' "$(clang-format --version 2>/dev/null || echo MISSING)"
printf '  go        : %s\n' "$(go version 2>/dev/null || echo 'run: source ~/.profile')"
printf '  rustc     : %s\n' "$(rustc --version 2>/dev/null || echo 'run: rustup default stable')"
printf '  dosemu    : %s\n' "$(command -v dosemu >/dev/null && echo present || echo MISSING)"
printf '  python    : %s\n' "$(python3 --version)"

cat <<NEXT

${C_OK}Bootstrap complete.${C_0} One human step remains:

  1. Put the disc image you own in disks/ with these exact names:
         disks/sotn.us.cue
         disks/sotn.us.bin
     (The cue's TRACK 01 FILE line must name sotn.us.bin. Extra audio tracks
     are parsed and ignored, so a multi-track dump is fine.)

  2. Then run everything else unattended:
         bash automation/setup/phase0.sh

     That extracts, builds, and verifies all 77 hashes. Exit 0 means the
     baseline matches and you can start function work.
NEXT
