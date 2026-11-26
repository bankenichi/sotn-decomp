#!/usr/bin/env bash
# Install JDK 21 + Ghidra 12.1.4 headless into WSL Ubuntu-24.04.
# Self-contained: resolves the asset, checksums the download, extracts,
# symlinks, and smoke-tests analyzeHeadless. Run as root via wsl -u root.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
exec 2>&1

echo "=== 1/6 apt-get update"
apt-get update -qq

echo "=== 2/6 openjdk-21-jdk-headless"
apt-get install -y -qq openjdk-21-jdk-headless wget unzip ca-certificates curl
java -version

echo "=== 3/6 resolve Ghidra_12.1.4_build asset"
mkdir -p /opt/ghidra-dl
curl -fsSL -H "User-Agent: sotn-decomp-pilot" \
  https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/tags/Ghidra_12.1.4_build \
  -o /opt/ghidra-dl/release.json
INFO=$(python3 - <<'PYEOF'
import json
d = json.load(open('/opt/ghidra-dl/release.json'))
a = [a for a in d['assets'] if a['name'].endswith('.zip')][0]
print(a['browser_download_url'])
print(a.get('digest') or 'none')
print(a.get('size') or 'none')
PYEOF
)
URL=$(echo "$INFO" | sed -n '1p')
DIGEST=$(echo "$INFO" | sed -n '2p')
SIZE=$(echo "$INFO" | sed -n '3p')
echo "asset: $URL"
echo "digest: $DIGEST  declared size: $SIZE"

echo "=== 4/6 download (about 570 MB)"
cd /opt/ghidra-dl
wget -q -O ghidra_1214.zip "$URL"
ls -l ghidra_1214.zip
ACTUAL=$(sha256sum ghidra_1214.zip | cut -d' ' -f1)
if [ "$DIGEST" != "none" ]; then
  EXPECTED="${DIGEST#sha256:}"
  if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "SHA-256 MISMATCH: expected $EXPECTED got $ACTUAL"
    exit 3
  fi
  echo "sha256 OK: $ACTUAL"
else
  echo "WARNING: release published no digest; trusting https origin"
fi

echo "=== 5/6 extract + symlink"
unzip -qo ghidra_1214.zip -d /opt
LINK=$(ls -d /opt/ghidra_12.1.*_PUBLIC | sort | tail -1)
ln -sfn "$LINK" /opt/ghidra
echo "installed: $LINK"

echo "=== 6/6 analyzeHeadless smoke"
/opt/ghidra/support/analyzeHeadless 2>&1 | head -25 || true
/opt/ghidra/support/analyzeHeadless -version 2>&1 | head -3 || true
echo "GHIDRA_INSTALL_COMPLETE $LINK"
