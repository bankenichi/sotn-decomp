"""Generate a Ghidra-ready MIPS LE ELF wrapper for one SOTN US overlay.

The decompilation pilot needs each overlay BIN exposed to Ghidra as a proper
ELF32 little-endian MIPS image whose load addresses are identical to the
splat-configured vram base.  A minimal single PT_LOAD ELF achieves that:

    file layout: [ELF header 52B][program header 32B][pad to 0x1000][overlay]
    p_offset = 0x1000, p_vaddr = base (0x80180000)

so overlay byte at file offset f maps at address base + f, which is exactly
how every splat symbol address is defined (for example bobo7
EntityBreakable = 0x80193258 = 0x80180000 + 0x13258).

For each requested overlay (arg in srcdir form, e.g. "boss/bo7") this script:

  1. reads config/splat.us.<cfg>.yaml for target_path, vram and sha1,
  2. verifies the retail BIN's SHA-1 against the config and stops on mismatch,
  3. resolves every remaining US stub symbol of the overlay (from the temp
     routes.json produced earlier this session) to an address through
     config/symbols.us.<cfg>.txt,
  4. writes  <temp>/wrapped/<NAME>.elf,
  5. writes  <temp>/targets/<NAME>.txt  (lines: 0xADDR NAME),
  6. writes  <temp>/run/<NAME>.sh  (the WSL runner ready to execute).

Exit status is non-zero if the checksum fails or no target resolves.
"""

import hashlib
import json
import os
import re
import struct
import sys

REPO = r"C:\Users\kenic\Documents\SOTN-Decomp"
TEMP = r"C:\Users\kenic\AppData\Local\Temp\opencode\sotn-rea"

VRA_M_DEFAULT = 0x80180000          # every US boss/ST overlay loads here
SMALLEST_MEMSZ = 0x1000             # header page is skipped, so at most this
MIPSP_WINDOW = 0xA0000              # sane symbol-address window: 640 KiB
PAGE = 0x1000


def overlay_config_name(srcdir):
    """Map a src overlay directory to its splat config basename.

    boss/bo7 -> bobo7, boss/rbo6 -> borbo6, st/rno4 -> strno4, st/sel -> stsel.
    """
    parts = srcdir.split("/")
    if len(parts) < 2:
        sys.exit("srcdir must be like boss/bo7, got %r" % srcdir)
    top, name = parts[0], parts[1]
    if top == "boss":
        if name.startswith("r"):
            return "bor" + name[1:]
        return "bobo" + name[2:]
    return "st" + name


def parse_splat(path):
    """Return (target_path, vram_int, sha1_hex) from a splat config file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    tm = re.search(r"^\s*target_path:\s*(\S+)", text, re.M)
    vm = re.search(r"^\s*vram:\s*(0x[0-9a-fA-F]+)", text, re.M)
    hm = re.search(r"^sha1:\s*([0-9a-fA-F]+)", text, re.M)
    if not (tm and vm and hm):
        sys.exit("splat config %s is missing one of target_path/vram/sha1" % path)
    return tm.group(1), int(vm.group(1), 16), hm.group(1).lower()


def load_symbols(path):
    """Parse splat symbol files: 'Name = 0x801xxxxx;'. Returns addr -> name."""
    out = {}
    pat = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+)")
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pat.search(line)
            if m:
                out[int(m.group(2), 16)] = m.group(1)
    return out


def to_wsl_path(win_path):
    """C:\\x\\y -> /mnt/c/x/y."""
    p = win_path.replace("\\", "/")
    drive, rest = p.split(":", 1)
    return "/mnt/" + drive.lower() + rest


def build_elf(bin_path, base, mem_end, out_path):
    """Write the wrapper ELF and return its total size in bytes."""
    with open(bin_path, "rb") as f:
        blob = f.read()

    # ELF32 LE header, MIPS (EM_MIPS=8), one program header.
    # e_flags left 0 so Ghidra picks plain MIPS:LE:32:default.
    ident = b"\x7fELF" + bytes([1, 1, 1, 0, 0]) + bytes(7)
    ehdr = struct.pack(
        "<16sHHIIIIIHHHHHH",
        ident,
        2,            # e_type ET_EXEC
        8,            # e_machine EM_MIPS
        1,            # e_version
        base,         # e_entry
        52,           # e_phoff (right after the 52-byte header)
        0,            # e_shoff (no sections)
        0,            # e_flags
        52,           # e_ehsize
        32,           # e_phentsize
        1,            # e_phnum
        0, 0, 0,      # e_shentsize, e_shnum, e_shstrndx
    )
    assert len(ehdr) == 52, len(ehdr)

    filesz = len(blob)
    # memory span covers the file and any overlay .bss taken from the highest
    # known symbol address inside a sane window
    span = max(filesz, mem_end - base, SMALLEST_MEMSZ)
    span = (span + 15) & ~15     # round up to 16

    phdr = struct.pack(
        "<IIIIIIII",
        1,                 # p_type PT_LOAD
        PAGE,              # p_offset (overlay bytes after the skipped page)
        base,              # p_vaddr
        base,              # p_paddr
        filesz,            # p_filesz
        span,              # p_memsz
        7,                 # p_flags RWX
        PAGE,              # p_align
    )
    assert len(phdr) == 32, len(phdr)

    pad = bytes(PAGE - (len(ehdr) + len(phdr)))
    with open(out_path, "wb") as f:
        f.write(ehdr)
        f.write(phdr)
        f.write(pad)
        f.write(blob)
    return len(blob)


def main():
    srcdir = sys.argv[1]
    cfg = overlay_config_name(srcdir)
    splat = os.path.join(REPO, "config", "splat.us.%s.yaml" % cfg)
    symfile = os.path.join(REPO, "config", "symbols.us.%s.txt" % cfg)

    target_path, base, expected_sha1 = parse_splat(splat)
    bin_path = os.path.join(REPO, target_path.replace("/", os.sep))
    if not os.path.exists(bin_path):
        sys.exit("overlay BIN not found: %s" % bin_path)

    actual_sha1 = hashlib.sha1(open(bin_path, "rb").read()).hexdigest()
    if actual_sha1 != expected_sha1:
        sys.exit("SHA-1 mismatch for %s: expected %s got %s"
                 % (bin_path, expected_sha1, actual_sha1))
    print("sha1 OK: %s = %s" % (target_path, actual_sha1))

    # NAME for file layout: last directory of target_path (BO7, RNO4, ...)
    dir_tokens = target_path.replace("/", os.sep).split(os.sep)
    name = dir_tokens[-2].upper()
    print("overlay NAME: %s  (srcdir %s, config %s)" % (name, srcdir, cfg))

    symbols = load_symbols(symfile)
    print("symbols loaded: %d from %s" % (len(symbols), symfile))

    # resolve every remaining US stub of this overlay to an address
    routes = json.load(open(os.path.join(TEMP, "routes.json")))
    stubs = [r for r in routes if r["overlay"] == srcdir]
    if not stubs:
        print("WARNING: no stubs found in routes.json for %s" % srcdir)

    NAME_FALLBACK = re.compile(r"^func_us_([0-9A-Fa-f]{6,8})$")

    targets = []
    unresolved = []
    for stub in stubs:
        addr = next((a for a, n in symbols.items() if n == stub["symbol"]), None)
        # Splatters only name matched symbols in symbols.us.<cfg>.txt. Unmatched
        # stubs carry no file entry, but their own name encodes the vram
        # address (symbol_name_format: us_$VRAM), e.g. func_us_80194D3C. Only
        # plain names are safe: a _from_<donor> suffix embeds the DONOR's
        # address, which is a different overlay.
        if addr is None:
            m = NAME_FALLBACK.match(stub["symbol"])
            if m:
                addr = int(m.group(1), 16)
        if addr is None or not (base <= addr < base + MIPSP_WINDOW):
            unresolved.append(stub["symbol"])
            continue
        targets.append((addr, stub["symbol"], stub.get("route")))

    if not targets:
        sys.exit("no stub symbol could be resolved in %s" % symfile)

    mem_end = max(a for a, _, _ in targets) + 8
    wrapped_dir = os.path.join(TEMP, "wrapped")
    targets_dir = os.path.join(TEMP, "targets")
    run_dir = os.path.join(TEMP, "run")
    out_dir = os.path.join(TEMP, "out", name)
    for d in (wrapped_dir, targets_dir, run_dir, out_dir):
        os.makedirs(d, exist_ok=True)

    elf_path = os.path.join(wrapped_dir, "%s.elf" % name)
    blob_len = build_elf(bin_path, base, mem_end, elf_path)
    print("wrote %s (overlay %d bytes, base 0x%X, mem_end 0x%X)"
          % (elf_path, blob_len, base, mem_end))

    targets_path = os.path.join(targets_dir, "%s.txt" % name)
    with open(targets_path, "w", newline="\n") as f:
        for addr, symbol, route in targets:
            f.write("0x%X %s ; %s\n" % (addr, symbol, route))
    print("wrote %s (%d targets, detail counts below)"
          % (targets_path, len(targets)))
    counts = {}
    for _, _, route in targets:
        counts[route] = counts.get(route, 0) + 1
    print("target route counts: %s" % json.dumps(counts))
    if unresolved:
        print("UNRESOLVED (%d): %s" % (len(unresolved), ", ".join(unresolved)))

    # runner script for WSL; -preScript applies symbols + creates functions,
    # -postScript decompiles the targets and exports C + summary.json
    run_script = os.path.join(run_dir, "%s.sh" % name)
    elf_wsl = to_wsl_path(elf_path)
    sym_wsl = to_wsl_path(symfile)
    targets_wsl = to_wsl_path(targets_path)
    out_wsl = to_wsl_path(out_dir)
    scripts_wsl = to_wsl_path(os.path.join(TEMP, "ghidra_scripts"))
    with open(run_script, "w", newline="\n") as f:
        f.write("""#!/usr/bin/env bash
# Generated by prepare_overlay.py (do not edit; regenerate instead).
set -euo pipefail

NAME="%(name)s"
GHIDRA="${GHIDRA:-/opt/ghidra/support/analyzeHeadless}"
ELF="%(elf)s"
SYM="%(sym)s"
TARGETS="%(tgt)s"
OUT="%(out)s"
PROJ="$HOME/sotn-ghidra/projects"
SCRIPTS="%(scripts)s"

mkdir -p "$OUT" "$PROJ"

"$GHIDRA" "$PROJ" "$NAME" -deleteProject \\
  -import "$ELF" \\
  -processor MIPS:LE:32:default \\
  -scriptPath "$SCRIPTS" \\
  -preScript SotnLabelPreScript.java "$SYM" "$TARGETS" \\
  -postScript SotnExportPostScript.java "$OUT" "$TARGETS" \\
  -analysisTimeoutPerFile 1800 \\
  2>&1 | grep -v "^INFO" | tail -n 60

echo "=== exported files:"
ls -la "$OUT" | head -50
echo "=== target summary:"
python3 - <<'PYEOF'
import json, sys
with open(r"%(out)s/summary.json") as fh:
    d = json.load(fh)
print("decompiled %%d/%%d" %% (d["decompiled"], d["targets"]))
PYEOF
""" % {
        "name": name,
        "elf": elf_wsl,
        "sym": sym_wsl,
        "tgt": targets_wsl,
        "out": out_wsl,
        "scripts": scripts_wsl,
    })
    print("wrote %s" % run_script)
    print("OVERLAY_READY")


if __name__ == "__main__":
    main()
