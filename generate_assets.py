#!/usr/bin/env python3
"""Generate all static data used by the SNES Neon Scenes ROM.

The output is a WLA-DX include file (src/generated.inc) containing fonts,
tilemaps, palettes, curve tables, Mode 7 lookup tables and the OAM HUD.
"""
from __future__ import annotations

import colorsys
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "src" / "generated.inc"

# ---------------------------------------------------------------------------
# 5x7 font (the glyphs are placed in the left 5 columns of an 8x8 tile)
# ---------------------------------------------------------------------------
RAW_GLYPHS = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "#": ("01010", "11111", "01010", "01010", "11111", "01010", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    ";": ("00000", "00110", "00110", "00000", "00110", "00100", "01000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "@": ("01110", "10001", "10111", "10101", "10111", "10000", "01111"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "\\": ("10000", "01000", "01000", "00100", "00010", "00010", "00001"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "^": ("00100", "01010", "10001", "00000", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
}


def glyph_pixels(ch: str, drop_shadow: bool = True) -> list[list[int]]:
    """Return an 8x8 color-index grid for a character."""
    rows = RAW_GLYPHS.get(ch, RAW_GLYPHS[" "])
    grid = [[0] * 8 for _ in range(8)]
    for y, row in enumerate(rows):
        for x, bit in enumerate(row):
            if bit == "1":
                grid[y][x + 1] = 1
    if drop_shadow:
        # Drop shadow, offset one pixel down/right, drawn behind the glyph.
        shadow = [[0] * 8 for _ in range(8)]
        for y in range(8):
            for x in range(8):
                if grid[y][x] == 1 and y + 1 < 8 and x + 1 < 8:
                    shadow[y + 1][x + 1] = 1
        for y in range(8):
            for x in range(8):
                if grid[y][x] == 0 and shadow[y][x] == 1:
                    grid[y][x] = 2
    return grid


def tile_2bpp(ch: str) -> bytes:
    # The BG title font is drawn without a shadow so 8px rows stay readable.
    grid = glyph_pixels(ch, drop_shadow=False)
    out = bytearray()
    for y in range(8):
        p0 = 0
        p1 = 0
        for x in range(8):
            c = grid[y][x]
            # 2bpp title font: 1 = white, 2 = shadow.
            if c == 1:
                p0 |= 0x80 >> x
            elif c == 2:
                p1 |= 0x80 >> x
        out += bytes((p0, p1))
    return bytes(out)


def tile_4bpp(ch: str) -> bytes:
    grid = glyph_pixels(ch)
    # 4bpp SNES tiles store planes 0/1 for rows 0-7, then planes 2/3.
    rows01 = bytearray()
    rows23 = bytearray()
    for y in range(8):
        planes = [0, 0, 0, 0]
        for x in range(8):
            c = grid[y][x]
            for p in range(4):
                if c & (1 << p):
                    planes[p] |= 0x80 >> x
        rows01 += bytes((planes[0], planes[1]))
        rows23 += bytes((planes[2], planes[3]))
    return bytes(rows01 + rows23)


DOT_TILES = [
    # Head: large soft glow.
    (
        "..2222..",
        ".211112.",
        "21111112",
        "21133112",
        "21133112",
        "21111112",
        ".211112.",
        "..2222..",
    ),
    # Mid trail: 6x6 glow.
    (
        "........",
        "..2222..",
        ".211112.",
        ".213312.",
        ".211112.",
        "..2222..",
        "........",
        "........",
    ),
    # Tail: 4x4 ember.
    (
        "........",
        "........",
        "..2222..",
        "..2112..",
        "..2112..",
        "..2222..",
        "........",
        "........",
    ),
]


def dot_tile_4bpp(pattern: tuple[str, ...]) -> bytes:
    rows01 = bytearray()
    rows23 = bytearray()
    for row in pattern:
        planes = [0, 0, 0, 0]
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            c = int(ch)
            for p in range(4):
                if c & (1 << p):
                    planes[p] |= 0x80 >> x
        rows01 += bytes((planes[0], planes[1]))
        rows23 += bytes((planes[2], planes[3]))
    return bytes(rows01 + rows23)


# ---------------------------------------------------------------------------
# WLA helpers
# ---------------------------------------------------------------------------
def db_rows(data: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        lines.append("  .DB " + ", ".join(f"${b:02X}" for b in chunk))
    return "\n".join(lines)


def dw_rows(values: list[int], width: int = 12) -> str:
    lines = []
    for i in range(0, len(values), width):
        chunk = values[i : i + width]
        lines.append("  .DW " + ", ".join(f"${v:04X}" for v in chunk))
    return "\n".join(lines)


def rgb555(r: int, g: int, b: int) -> int:
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)


def hex_color(value: str) -> int:
    value = value.lstrip("#")
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return rgb555(r, g, b)


def palette_bytes(colors: list[int]) -> bytes:
    out = bytearray()
    for c in colors:
        out += bytes((c & 0xFF, (c >> 8) & 0xFF))
    return bytes(out)


# ---------------------------------------------------------------------------
# Title screen tilemap
# ---------------------------------------------------------------------------
TITLE_ROWS = [
    # row, text, palette, optional fixed column (otherwise centred)
    (2, "-" * 32, 1, 0),
    (4, "LISSAJOUS", 1, None),
    (6, "DIAGRAMS", 1, None),
    (8, "A SNES GENERATIVE DEMO", 0, None),
    (10, "LEFT / RIGHT", 0, 2),
    (10, "FREQ A", 0, 21),
    (11, "UP / DOWN", 0, 2),
    (11, "FREQ B", 0, 21),
    (12, "L / R", 0, 2),
    (12, "TRAIL", 0, 21),
    (13, "Y", 0, 2),
    (13, "SPEED", 0, 21),
    (14, "A", 0, 2),
    (14, "PAUSE", 0, 21),
    (15, "B", 0, 2),
    (15, "RESET", 0, 21),
    (16, "X", 0, 2),
    (16, "COLOR", 0, 21),
    (17, "SELECT", 0, 2),
    (17, "HELP", 0, 21),
    (18, "START", 0, 2),
    (18, "LAUNCH", 0, 21),
    (21, "PRESS START", 2, None),
    (24, "SEL RETURNS TO THIS SCREEN", 0, None),
    (27, "-" * 32, 1, 0),
]


def title_tilemap() -> bytes:
    entries = [0] * (32 * 32)
    for row, text, pal, fixed_col in TITLE_ROWS:
        if len(text) > 32:
            raise ValueError(f"title row too long: {text!r}")
        col = fixed_col if fixed_col is not None else (32 - len(text)) // 2
        if col < 0 or col + len(text) > 32:
            raise ValueError(f"title row out of bounds: {text!r}")
        for i, ch in enumerate(text):
            code = ord(ch)
            if not (32 <= code < 96):
                raise ValueError(f"unsupported title character {ch!r}")
            tile = code - 32
            entries[row * 32 + col + i] = tile | (pal << 10)
    out = bytearray()
    for e in entries:
        out += bytes((e & 0xFF, e >> 8))
    return bytes(out)


# ---------------------------------------------------------------------------
# OAM HUD template
# ---------------------------------------------------------------------------
OAM_TEMPLATE = bytearray(544)
NEXT_SPRITE = 0


def add_text(text: str, x: int, y: int, palette: int = 0) -> list[int]:
    global NEXT_SPRITE
    indices = []
    for i, ch in enumerate(text):
        idx = NEXT_SPRITE
        NEXT_SPRITE += 1
        if idx >= 128:
            raise ValueError("too many sprites")
        tile = ord(ch) - 32
        attr = 0x30 | (palette << 1)  # priority 3, palette
        base = idx * 4
        OAM_TEMPLATE[base + 0] = x + i * 8
        OAM_TEMPLATE[base + 1] = (y - 1) & 0xFF
        OAM_TEMPLATE[base + 2] = tile & 0xFF
        OAM_TEMPLATE[base + 3] = attr
        indices.append(idx)
    return indices


def build_oam() -> tuple[bytes, dict[str, int]]:
    # Slots 0..95 are the moving comet trail.
    global NEXT_SPRITE
    NEXT_SPRITE = 96
    slots: dict[str, int] = {}
    add_text("A", 8, 8, 1)
    slots["a_t"] = add_text("0", 16, 8, 0)[0]
    slots["a_o"] = add_text("3", 24, 8, 0)[0]
    add_text("B", 48, 8, 1)
    slots["b_t"] = add_text("0", 56, 8, 0)[0]
    slots["b_o"] = add_text("2", 64, 8, 0)[0]
    add_text("S", 176, 8, 1)
    slots["s_t"] = add_text("0", 184, 8, 0)[0]
    slots["s_o"] = add_text("8", 192, 8, 0)[0]
    add_text("T", 216, 8, 1)
    slots["t_t"] = add_text("0", 224, 8, 0)[0]
    slots["t_o"] = add_text("0", 232, 8, 0)[0]
    slots["paused"] = add_text("PAUSED", 96, 24, 7)[0]
    # Slots 96..113 are HUD; 114..127 are unused.  High table stays zero.
    return bytes(OAM_TEMPLATE), slots


# ---------------------------------------------------------------------------
# Shapes / curve tables
# ---------------------------------------------------------------------------
SHAPES = [
    (1, 1, "1:1"),
    (1, 2, "1:2"),
    (2, 3, "2:3"),
    (3, 2, "3:2"),
    (3, 4, "3:4"),
    (4, 3, "4:3"),
    (5, 4, "5:4"),
    (4, 5, "4:5"),
    (5, 2, "5:2"),
    (3, 5, "3:5"),
    (5, 3, "5:3"),
    (7, 5, "7:5"),
]
SPEED_VALUES = [2, 4, 6, 8, 12, 16, 24, 32]
SPEED_CHARS = "2468"  # unused legacy table
TRAIL_MAX = 96
FREQ_MAX = 12


def curve_tables() -> tuple[bytes, bytes]:
    cx, cy = 44, 39
    ax, ay = 36, 33
    xs = bytearray()
    ys = bytearray()
    for i in range(256):
        a = 2.0 * math.pi * i / 256.0
        xs.append(max(0, min(87, int(round(cx + ax * math.sin(a))))))
        ys.append(max(0, min(76, int(round(cy + ay * math.sin(a))))))
    return bytes(xs), bytes(ys)


def screen_curve_tables() -> tuple[bytes, bytes]:
    """Particle centre coordinates in 256x224 screen space."""
    xs = bytearray()
    ys = bytearray()
    for i in range(256):
        a = 2.0 * math.pi * i / 256.0
        xs.append(max(8, min(247, int(round(128 + 96 * math.sin(a))))))
        ys.append(max(8, min(215, int(round(112 + 84 * math.sin(a))))))
    return bytes(xs), bytes(ys)


def shape_order_blocks() -> tuple[list[bytes], list[int]]:
    """For every shape, precompute a*order and b*order for 120 particles."""
    order = [int(round(i * 256.0 / 120.0)) & 0xFF for i in range(120)]
    blocks = []
    for a, b, _label in SHAPES:
        block = bytes((a * o) & 0xFF for o in order)
        block += bytes((b * o) & 0xFF for o in order)
        blocks.append(block)
    return blocks, order


def color_pattern() -> bytes:
    return bytes(2 + (i % 6) for i in range(32))


def frequency_tables(xs: bytes, ys: bytes) -> tuple[list[bytes], list[bytes]]:
    """Precompute screen X/Y for every integer frequency and 8-bit angle."""
    xblocks = []
    yblocks = []
    for f in range(1, FREQ_MAX + 1):
        xb = bytearray()
        yb = bytearray()
        for angle in range(256):
            idx = (f * angle) & 0xFF
            xb.append(xs[idx])
            yb.append(ys[idx])
        xblocks.append(bytes(xb))
        yblocks.append(bytes(yb))
    return xblocks, yblocks


def trail_style_tables() -> tuple[bytes, list[bytes]]:
    """Tile per trail position and three colour-rotation attribute tables."""
    tiles = bytes([64] * 4 + [65] * 24 + [66] * (TRAIL_MAX - 28))
    schemes = []
    for scheme in range(3):
        attrs = bytearray()
        for i in range(TRAIL_MAX):
            if i < 4:
                pal = 0
            elif i < 28:
                pal = 1 + (((i >> 2) + scheme) % 2)
            else:
                pal = 1 + (((i >> 2) + scheme) % 6)
            attrs.append(0x20 | (pal << 1))  # priority 2
        schemes.append(bytes(attrs))
    return tiles, schemes


def decimal_tables() -> tuple[bytes, bytes]:
    tens = bytearray()
    ones = bytearray()
    for value in range(100):
        t = value // 10
        o = value % 10
        tens.append(ord("0") + t - 32)
        ones.append(ord("0") + o - 32)
    return bytes(tens), bytes(ones)


def mode7_maps() -> tuple[bytes, bytes]:
    # Mode 7 map: one byte per VRAM word, row stride = 128 words.
    blobs = []
    for base in (0, 110):
        out = bytearray()
        for row in range(10):
            for col in range(11):
                out.append(base + row * 11 + col)
            out += bytes(117)
        assert len(out) == 1280
        blobs.append(bytes(out))
    return blobs[0], blobs[1]


def lookup_tables() -> tuple[list[int], list[int], list[int]]:
    row_a = []
    row_b = []
    for y in range(77):
        base = (y >> 3) * 704 + (y & 7) * 8
        row_a.append(base)
        row_b.append(base + 7040)
    col = []
    for x in range(88):
        col.append((x >> 3) * 64 + (x & 7))
    return row_a, row_b, col


def make_gradient(stops: list[tuple[float, tuple[int, int, int]]], n: int = 16) -> list[int]:
    colors = []
    for i in range(n):
        t = i / (n - 1)
        for j in range(len(stops) - 1):
            t0, c0 = stops[j]
            t1, c1 = stops[j + 1]
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
                rgb = tuple(int(round(c0[k] + (c1[k] - c0[k]) * u)) for k in range(3))
                colors.append(rgb555(*rgb))
                break
        else:
            colors.append(rgb555(*stops[-1][1]))
    return colors


def game_palettes() -> tuple[bytes, bytes, list[bytes]]:
    base = [
        rgb555(0, 0, 0),
        rgb555(4, 10, 22),
        rgb555(8, 36, 58),
        rgb555(20, 84, 112),
    ]
    # Four 16-colour curve palettes.
    neon = make_gradient(
        [
            (0.0, (0, 120, 255)),
            (0.28, (0, 255, 235)),
            (0.55, (120, 255, 190)),
            (0.78, (255, 90, 230)),
            (1.0, (255, 255, 255)),
        ]
    )
    solar = make_gradient(
        [
            (0.0, (110, 20, 0)),
            (0.35, (255, 110, 0)),
            (0.7, (255, 230, 80)),
            (1.0, (255, 255, 230)),
        ]
    )
    aurora = make_gradient(
        [
            (0.0, (0, 60, 40)),
            (0.3, (0, 220, 130)),
            (0.6, (0, 255, 230)),
            (0.85, (90, 140, 255)),
            (1.0, (235, 255, 255)),
        ]
    )
    mono = make_gradient(
        [
            (0.0, (20, 40, 100)),
            (0.5, (100, 180, 255)),
            (1.0, (255, 255, 255)),
        ]
    )
    # The 16 curve colours live at CGRAM entries 4..19.
    palettes = [palette_bytes(p) for p in (neon, solar, aurora, mono)]
    # Full 0..19 upload.
    full = palette_bytes(base) + palettes[0]
    # Eight 16-colour OBJ palettes at CGRAM 128..255.
    # Palette 0/1 are HUD, 2..7 are curve particle colours.
    sprite_defs = [
        (rgb555(255, 255, 255), rgb555(0, 4, 8), rgb555(255, 255, 255)),
        (rgb555(0, 255, 245), rgb555(0, 30, 80), rgb555(255, 255, 255)),
        (rgb555(0, 180, 255), rgb555(0, 20, 90), rgb555(255, 255, 255)),
        (rgb555(80, 120, 255), rgb555(0, 10, 80), rgb555(235, 245, 255)),
        (rgb555(190, 80, 255), rgb555(50, 0, 90), rgb555(255, 235, 255)),
        (rgb555(255, 80, 210), rgb555(90, 0, 60), rgb555(255, 235, 255)),
        (rgb555(40, 90, 200), rgb555(0, 8, 40), rgb555(180, 220, 255)),
        (rgb555(255, 210, 90), rgb555(90, 45, 0), rgb555(255, 255, 255)),
    ]
    sprites = bytearray()
    for main, halo, highlight in sprite_defs:
        colors = [rgb555(0, 0, 0), main, halo, highlight] + [0] * 12
        sprites += palette_bytes(colors)
    return full, bytes(sprites), palettes


def title_palette() -> bytes:
    colors = [
        rgb555(4, 8, 18),     # 0 backdrop / transparent
        rgb555(235, 245, 255),# 1 white body
        rgb555(6, 16, 28),    # 2 shadow
        rgb555(70, 130, 170), # 3 muted blue (unused)
        rgb555(4, 8, 18),     # 4 palette 1 transparent
        rgb555(0, 235, 255),  # 5 cyan title
        rgb555(0, 24, 36),    # 6 title shadow
        rgb555(255, 255, 255),# 7 white (unused)
        rgb555(4, 8, 18),     # 8 palette 2 transparent
        rgb555(255, 210, 90), # 9 gold prompt
        rgb555(40, 30, 0),    # 10 prompt shadow
        rgb555(255, 245, 190),# 11 pale gold (unused)
    ]
    return palette_bytes(colors)


# ---------------------------------------------------------------------------
# Emit include
# ---------------------------------------------------------------------------
def main() -> None:
    font2 = b"".join(tile_2bpp(chr(c)) for c in range(32, 96))
    font4 = b"".join(tile_4bpp(chr(c)) for c in range(32, 96))
    font4 += b"".join(dot_tile_4bpp(pattern) for pattern in DOT_TILES)
    oam, hud_slots = build_oam()
    curve_x, curve_y = curve_tables()
    screen_x, screen_y = screen_curve_tables()
    freq_x_blocks, freq_y_blocks = frequency_tables(screen_x, screen_y)
    trail_tiles, trail_schemes = trail_style_tables()
    dec_tens, dec_ones = decimal_tables()
    order_blocks, particle_order = shape_order_blocks()
    color_pat = color_pattern()
    map_a, map_b = mode7_maps()
    row_a, row_b, col = lookup_tables()
    full_palette, sprite_palette, curve_palettes = game_palettes()
    title_pal = title_palette()

    shape_a = bytes(s[0] for s in SHAPES)
    shape_b = bytes(s[1] for s in SHAPES)
    labels = [s[2] for s in SHAPES]

    out = []
    out.append("; -----------------------------------------------------------------------------")
    out.append("; AUTO-GENERATED by generate_assets.py. Do not edit by hand.")
    out.append("; -----------------------------------------------------------------------------")
    out.append("")
    out.append(f".DEFINE OAM_A_TENS {hud_slots['a_t']}")
    out.append(f".DEFINE OAM_A_ONES {hud_slots['a_o']}")
    out.append(f".DEFINE OAM_B_TENS {hud_slots['b_t']}")
    out.append(f".DEFINE OAM_B_ONES {hud_slots['b_o']}")
    out.append(f".DEFINE OAM_S_TENS {hud_slots['s_t']}")
    out.append(f".DEFINE OAM_S_ONES {hud_slots['s_o']}")
    out.append(f".DEFINE OAM_T_TENS {hud_slots['t_t']}")
    out.append(f".DEFINE OAM_T_ONES {hud_slots['t_o']}")
    out.append(f".DEFINE OAM_PAUSE0 {hud_slots['paused']}")
    out.append(f".DEFINE SHAPE_COUNT {len(SHAPES)}")
    out.append(f".DEFINE SPEED_COUNT {len(SPEED_VALUES)}")
    out.append(f".DEFINE TITLE_COLOR_COUNT {len(title_pal)//2}")
    out.append(f".DEFINE GAME_COLOR_COUNT {len(full_palette)//2}")
    out.append(f".DEFINE CURVE_PALETTE_COUNT {len(curve_palettes)}")
    out.append(f".DEFINE CURVE_PARTICLES {len(particle_order)}")
    out.append(f".DEFINE DOT_TILE_INDEX {64}")
    out.append(f".DEFINE DOT_MID_INDEX {65}")
    out.append(f".DEFINE DOT_SMALL_INDEX {66}")
    out.append(f".DEFINE TRAIL_MAX {TRAIL_MAX}")
    out.append(f".DEFINE TRAIL_ATTR_SCHEME_SIZE {TRAIL_MAX}")
    out.append(f".DEFINE FREQ_MAX {FREQ_MAX}")
    out.append(f".DEFINE SPRITE_PALETTE_COUNT {len(sprite_palette)//32}")
    out.append("")

    out.append("Font2bpp:")
    out.append(db_rows(font2))
    out.append("")
    out.append("Font4bpp:")
    out.append(db_rows(font4))
    out.append("")
    out.append("TitleTilemap:")
    out.append(db_rows(title_tilemap()))
    out.append("")
    out.append("TitlePalette:")
    out.append(db_rows(title_pal))
    out.append("")
    out.append("GamePalette:")
    out.append(db_rows(full_palette))
    out.append("")
    out.append("SpritePalette:")
    out.append(db_rows(sprite_palette))
    out.append("")
    for i, p in enumerate(curve_palettes):
        out.append(f"CurvePalette{i}:")
        out.append(db_rows(p))
        out.append("")
    out.append("CurveX:")
    out.append(db_rows(curve_x))
    out.append("")
    out.append("CurveY:")
    out.append(db_rows(curve_y))
    out.append("")
    out.append("CurveScreenX:")
    out.append(db_rows(screen_x))
    out.append("")
    out.append("CurveScreenY:")
    out.append(db_rows(screen_y))
    out.append("")
    out.append("ColorPattern:")
    out.append(db_rows(color_pat))
    out.append("")
    out.append("TrailTiles:")
    out.append(db_rows(trail_tiles))
    out.append("")
    out.append("TrailAttrs:")
    for scheme in trail_schemes:
        out.append(db_rows(scheme))
    out.append("")
    out.append("TrailAttrPtrs:")
    out.append("  .DW TrailAttrs, TrailAttrs+" + str(TRAIL_MAX) + ", TrailAttrs+" + str(TRAIL_MAX * 2))
    out.append("")
    for i, block in enumerate(freq_x_blocks, start=1):
        out.append(f"FreqX{i}:")
        out.append(db_rows(block))
        out.append("")
    out.append("FreqXPtrs:")
    out.append("  .DW " + ", ".join(f"FreqX{i}" for i in range(1, FREQ_MAX + 1)))
    out.append("")
    for i, block in enumerate(freq_y_blocks, start=1):
        out.append(f"FreqY{i}:")
        out.append(db_rows(block))
        out.append("")
    out.append("FreqYPtrs:")
    out.append("  .DW " + ", ".join(f"FreqY{i}" for i in range(1, FREQ_MAX + 1)))
    out.append("")
    out.append("DecimalTens:")
    out.append(db_rows(dec_tens))
    out.append("")
    out.append("DecimalOnes:")
    out.append(db_rows(dec_ones))
    out.append("")
    for i, block in enumerate(order_blocks):
        out.append(f"ShapeOrder{i}:")
        out.append(db_rows(block))
        out.append("")
    out.append("ShapeOrderPtrs:")
    out.append("  .DW " + ", ".join(f"ShapeOrder{i}" for i in range(len(order_blocks))))
    out.append("")
    out.append("MapBuffer0:")
    out.append(db_rows(map_a))
    out.append("")
    out.append("MapBuffer1:")
    out.append(db_rows(map_b))
    out.append("")
    out.append("RowTableA:")
    out.append(dw_rows(row_a))
    out.append("")
    out.append("RowTableB:")
    out.append(dw_rows(row_b))
    out.append("")
    out.append("ColTable:")
    out.append(dw_rows(col))
    out.append("")
    out.append("ShapeA:")
    out.append(db_rows(shape_a))
    out.append("")
    out.append("ShapeB:")
    out.append(db_rows(shape_b))
    out.append("")
    for i in range(3):
        out.append(f"ShapeLabel{i}:")
        out.append(db_rows(bytes(ord(labels[j][i]) - 32 for j in range(len(labels)))))
        out.append("")
    out.append("SpeedChars:")
    out.append(db_rows(bytes(ord(c) - 32 for c in SPEED_CHARS)))
    out.append("")
    out.append("SpeedValues:")
    out.append(db_rows(bytes(SPEED_VALUES)))
    out.append("")
    out.append("OamTemplate:")
    out.append(db_rows(oam))
    out.append("")
    out.append("ZeroByte:")
    out.append("  .DB $00")
    out.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="ascii")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"font2={len(font2)} font4={len(font4)} tilemap={len(title_tilemap())} oam={len(oam)}")
    print(f"HUD slots: {hud_slots}")
    print(f"frequency tables: {len(freq_x_blocks)}x256 X + {len(freq_y_blocks)}x256 Y")


if __name__ == "__main__":
    main()
