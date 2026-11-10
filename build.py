#!/usr/bin/env python3
"""Build the Neon Scenes SNES ROM.

Requires Python 3 and WLA-DX 10.7 (wla-65816 + wlalink).  The expected
Windows binaries live in tools/wla/wla_dx_v10.7_Win64/.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
SRC = ROOT / "src"
OUT = ROOT / "NeonScenes.sfc"
WLA_DIR = ROOT / "tools" / "wla" / "wla_dx_v10.7_Win64"
WLA = WLA_DIR / "wla-65816.exe"
LINK = WLA_DIR / "wlalink.exe"


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"command failed with exit code {result.returncode}")


def main() -> None:
    if not WLA.exists() or not LINK.exists():
        raise SystemExit(
            "WLA-DX not found. Put wla-65816.exe and wlalink.exe in\n"
            f"  {WLA_DIR}\n"
            "Download WLA-DX v10.7 from https://github.com/vhelin/wla-dx/releases"
        )

    BUILD.mkdir(exist_ok=True)
    # WLA-DX uses tmpfile(); some Windows temp folders are not writable for
    # the assembler, so keep its temporary files inside the build directory.
    wla_tmp = BUILD / "tmp"
    wla_tmp.mkdir(exist_ok=True)
    os.environ["TMP"] = str(wla_tmp)
    os.environ["TEMP"] = str(wla_tmp)
    run([sys.executable, str(ROOT / "generate_assets.py")])
    run([sys.executable, str(ROOT / "generate_scenes.py")])
    run([str(WLA), "-h", "-I", str(SRC), "-o", str(BUILD / "main.o"), str(SRC / "main.asm")])

    linkfile = BUILD / "link.txt"
    linkfile.write_text("[objects]\nbuild/main.o\n", encoding="ascii")
    run([str(LINK), "-S", "-r", str(linkfile), str(OUT)])

    data = bytearray(OUT.read_bytes())
    if len(data) != 512 * 1024:
        raise SystemExit(f"unexpected ROM size: {len(data)} bytes")

    # WLA-DX writes a self-consistent-looking pair, but its sum includes the
    # four checksum bytes themselves.  The standard SNES checksum excludes
    # them.  Rewrite the pair so real hardware / flash cart tools agree too.
    checksum = sum(
        value for offset, value in enumerate(data)
        if offset not in (0x7FDC, 0x7FDD, 0x7FDE, 0x7FDF)
    ) & 0xFFFF
    complement = checksum ^ 0xFFFF
    data[0x7FDC] = complement & 0xFF
    data[0x7FDD] = (complement >> 8) & 0xFF
    data[0x7FDE] = checksum & 0xFF
    data[0x7FDF] = (checksum >> 8) & 0xFF
    OUT.write_bytes(data)
    data = bytes(data)

    title = data[0x7FC0:0x7FC0 + 21].decode("ascii", "replace").rstrip("\x00 ")
    if not title.startswith("NEON SCENES"):
        raise SystemExit(f"bad header title: {title!r}")
    reset = data[0x7FFC] | (data[0x7FFD] << 8)
    if reset != 0x8000:
        raise SystemExit(f"bad reset vector: ${reset:04X}")
    checksum = data[0x7FDE] | (data[0x7FDF] << 8)
    complement = data[0x7FDC] | (data[0x7FDD] << 8)
    if (checksum ^ complement) != 0xFFFF:
        raise SystemExit("checksum/complement mismatch")
    actual = sum(
        value for offset, value in enumerate(data)
        if offset not in (0x7FDC, 0x7FDD, 0x7FDE, 0x7FDF)
    ) & 0xFFFF
    if actual != checksum:
        raise SystemExit(f"checksum is ${checksum:04X}, expected ${actual:04X}")
    digest = hashlib.sha256(data).hexdigest()

    print()
    print(f"ROM:        {OUT}")
    print(f"Size:       {len(data)} bytes (512 KiB LoROM)")
    print(f"Title:      {title}")
    print(f"Reset:      ${reset:04X}")
    print(f"Checksum:   ${checksum:04X} / complement ${complement:04X}")
    print(f"SHA-256:    {digest}")


if __name__ == "__main__":
    main()

