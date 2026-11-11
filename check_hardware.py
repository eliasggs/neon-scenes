#!/usr/bin/env python3
"""Static hardware checks for the Neon Scenes LoROM.

This does not replace a test on a real console or flash cart.  It catches the
things that emulators often hide: a wrong/absent header, a non-standard
checksum, vectors outside bank 0, DMA blobs that cross a 32 KiB bank, and
malformed HDMA tables.

Usage:
    python check_hardware.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
ROM_PATH = ROOT / "NeonScenes.sfc"
SYM_PATH = ROOT / "NeonScenes.sym"

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    print(("PASS  " if condition else "FAIL  ") + message)
    if not condition:
        failures.append(message)


def rom_offset(bank: int, addr: int) -> int:
    """LoROM: 32 KiB banks mapped at $8000-$FFFF."""
    return bank * 0x8000 + (addr - 0x8000)


def main() -> int:
    rom = ROM_PATH.read_bytes()
    lines = SYM_PATH.read_text(encoding="utf-8", errors="replace").splitlines()

    labels: dict[str, tuple[int, int]] = {}
    sizes: dict[str, int] = {}
    for line in lines:
        match = re.match(r"^([0-9a-fA-F]{2}):([0-9a-fA-F]{4}) (\S+)$", line)
        if match:
            labels[match.group(3)] = (int(match.group(1), 16), int(match.group(2), 16))
            continue
        match = re.match(r"^([0-9a-fA-F]{8}) _sizeof_(\S+)$", line)
        if match:
            sizes[match.group(2)] = int(match.group(1), 16)

    print("== cartridge header ==")
    check(len(rom) == 512 * 1024, f"file size is 512 KiB (got {len(rom)} bytes)")
    title = rom[0x7FC0:0x7FC0 + 21].decode("ascii", "replace").rstrip("\x00 ")
    check(title.startswith("NEON SCENES"), f"title is {title!r}")
    for name, offset, expected, detail in (
        ("map mode", 0x7FD5, 0x20, "LoROM / slow"),
        ("cartridge type", 0x7FD6, 0x00, "ROM only"),
        ("ROM size", 0x7FD7, 0x09, "512 KiB"),
        ("SRAM size", 0x7FD8, 0x00, "none"),
        ("country", 0x7FD9, 0x01, "USA / NTSC"),
        ("licensee", 0x7FDA, 0x00, "none"),
        ("version", 0x7FDB, 0x00, "1.0"),
    ):
        check(rom[offset] == expected,
              f"{name} is ${rom[offset]:02X} (expected ${expected:02X}, {detail})")

    checksum = int.from_bytes(rom[0x7FDE:0x7FE0], "little")
    complement = int.from_bytes(rom[0x7FDC:0x7FDE], "little")
    summed = sum(
        value for offset, value in enumerate(rom)
        if offset not in (0x7FDC, 0x7FDD, 0x7FDE, 0x7FDF)
    )
    standard = (summed + 0x01FE) & 0xFFFF  # checksum field treated as FF FF 00 00
    check(checksum == standard,
          f"checksum is ${checksum:04X} (standard ${standard:04X})")
    check((checksum ^ complement) == 0xFFFF,
          f"complement is ${complement:04X} (checksum xor complement = FFFF)")

    print("== reset and exception vectors ==")
    reset = int.from_bytes(rom[0x7FFC:0x7FFE], "little")
    nmi = int.from_bytes(rom[0x7FEA:0x7FEC], "little")
    irq = int.from_bytes(rom[0x7FEE:0x7FF0], "little")
    check(reset == 0x8000, f"RESET vector is ${reset:04X}")
    check(0x8000 <= nmi < 0x10000, f"native NMI vector is ${nmi:04X} (bank 0)")
    check(0x8000 <= irq < 0x10000, f"native IRQ vector is ${irq:04X} (bank 0)")
    for name, offset in (("emu COP", 0x7FF4), ("emu ABORT", 0x7FF8),
                         ("emu NMI", 0x7FFA), ("emu IRQ", 0x7FFE)):
        vector = int.from_bytes(rom[offset:offset + 2], "little")
        check(0x8000 <= vector < 0x10000, f"{name} vector is ${vector:04X}")

    # sei / cld / clc / xce / rep #$30 / ldx #$1FFF / txs / lda #0 / tcd
    # / sep #$20 / lda #0 / pha / plb / stz $4200 / stz $420C / stz $420D
    # / lda #$8F / sta $2100
    reset_stub = bytes.fromhex(
        "78 D8 18 FB C2 30 A2 FF 1F 9A A9 00 00 5B E2 20 A9 00 48 AB "
        "9C 00 42 9C 0C 42 9C 0D 42 A9 8F 8D 00 21"
    )
    check(rom.startswith(reset_stub),
          "reset enters native mode, sets SP=$1FFF/DP=0/DBR=0, disables NMI+HDMA, forces blank")
    check(bytes.fromhex("A2 02 00 2C 12 42 10") in rom[:0x200],
          "reset waits for two vblank periods")
    check(rom[rom_offset(0, nmi):rom_offset(0, nmi) + 8]
          == bytes.fromhex("08 C2 30 48 DA 5A E2 20"),
          "NMI handler starts with php/rep #$30/pha/phx/phy/sep #$20")

    print("== DMA blobs stay inside one 32 KiB bank ==")
    checked_blobs = 0
    blob_errors = 0
    for name, (bank, addr) in sorted(labels.items()):
        size = sizes.get(name)
        if not size or size > 0x8000 or addr < 0x8000:
            continue
        checked_blobs += 1
        start = rom_offset(bank, addr)
        end = start + size
        limit = (bank + 1) * 0x8000
        if end > limit:
            check(False, f"{name} (${bank:02X}:{addr:04X}, ${size:X} bytes) crosses bank end")
            blob_errors += 1
    check(blob_errors == 0,
          f"{checked_blobs} sized blobs checked, none cross a bank")

    print("== scene descriptors ==")
    bank, addr = labels["SceneDesc"]
    table = rom_offset(bank, addr)
    for scene in range(6):
        entry = rom[table + scene * 16:table + (scene + 1) * 16]
        bg = entry[0] | (entry[1] << 8) | (entry[2] << 16)
        frame = entry[3] | (entry[4] << 8) | (entry[5] << 16)
        count = entry[6]
        bg_size = entry[12] | (entry[13] << 8)
        if bg:
            start = rom_offset(bg >> 16, bg & 0xFFFF)
            check(start + bg_size <= ((bg >> 16) + 1) * 0x8000,
                  f"scene {scene}: Mode 7 background ${bg:06X}+${bg_size:X} fits its bank")
        if frame and count:
            start = rom_offset(frame >> 16, frame & 0xFFFF)
            check(start + count * 3 <= ((frame >> 16) + 1) * 0x8000,
                  f"scene {scene}: {count} frame pointers at ${frame:06X} fit their bank")

    print("== HDMA tables ==")
    hdma_labels = ["CityHdmaTable", "NeonScaleTable", "NeonShearTable"]
    hdma_labels += [f"NeonVTable{i}" for i in range(32)]
    for name in hdma_labels:
        bank, addr = labels[name]
        start = rom_offset(bank, addr)
        table = rom[start:start + 673]
        structure_ok = (
            len(table) == 673
            and all(table[i] == 0x01 for i in range(0, 672, 3))
            and table[672] == 0x00
        )
        check(structure_ok, f"{name}: 224 one-line 16-bit entries + terminator")
        check(start + 673 <= (bank + 1) * 0x8000,
              f"{name}: 673 bytes fit its bank")

    print("== Pulse Analyzer NMI write lists ==")
    bank, addr = labels["MagiUpdatePtrs"]
    table = rom_offset(bank, addr)
    max_count = 0
    lists_ok = True
    for frame in range(128):
        pointer = rom[table + frame * 3:table + frame * 3 + 3]
        ptr = pointer[0] | (pointer[1] << 8) | (pointer[2] << 16)
        start = rom_offset(ptr >> 16, ptr & 0xFFFF)
        count = rom[start]
        max_count = max(max_count, count)
        if count > 64 or start + 1 + count * 4 > ((ptr >> 16) + 1) * 0x8000:
            lists_ok = False
    check(lists_ok, "128 frame lists are valid and fit their bank")
    check(max_count <= 64, f"largest frame list is {max_count} writes (fits vblank)")

    print()
    if failures:
        print(f"HARDWARE CHECK: {len(failures)} FAILURE(S)")
        return 1
    print("HARDWARE CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
