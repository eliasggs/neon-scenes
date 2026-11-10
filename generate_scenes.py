#!/usr/bin/env python3
"""Generate the scene engine data for the Neon Scenes SNES demo.

Outputs:
  src/scenes_shared.inc   selector maps, theme palettes, HDMA tables,
                          extra sprite tiles, scene descriptors and names
  src/bankNN.inc          per-bank backgrounds and precomputed OAM frames
  src/scene_banks.inc     WLA bank/include glue for the scene data banks

The four new scenes are rendered with pre-computed OAM frames (96 sprites
each) over a Mode 7 background.  Keeping the frame math on the PC side makes
the 65816 main loop small and deterministic; the Lissajous scene keeps its
original real-time trail code.
"""
from __future__ import annotations

import colorsys
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Every periodic motion in a precomputed scene must complete a whole number
# of cycles across FRAME_COUNT.  Fractional terms make frame 119 jump back to
# frame 0; that was the Holo Planet / Atomic snap at the loop point.
FRAME_COUNT = 120
FRAME_SIZE = 408          # 96 OAM entries * 4 + 24 high-table bytes
SPRITE_SLOTS = 96
SCENE_COUNT = 6

# Sprite tile indices (the first 64 tiles are the 4bpp font).
DOT_LARGE = 64
DOT_MID = 65
DOT_SMALL = 66
STAR = 67
HLINE = 68
VLINE = 69
SQUARE = 70
RING = 71
GLOW16 = 80               # uses 80/81/96/97
BAR16 = 112               # uses 112/113/128/129
EXTRA_FIRST = 67
EXTRA_LAST = 201          # 67..143 shared scene tiles, 144..183 the neon car

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
def rgb555(r: int, g: int, b: int) -> int:
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)


def hx(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def palette_bytes(colors: list[int]) -> bytes:
    out = bytearray()
    for c in colors:
        out += bytes((c & 0xFF, (c >> 8) & 0xFF))
    return bytes(out)


def grad(stops: list[tuple[float, tuple[int, int, int]]], n: int = 16) -> list[tuple[int, int, int]]:
    colors = []
    for i in range(n):
        t = i / (n - 1)
        for j in range(len(stops) - 1):
            t0, c0 = stops[j]
            t1, c1 = stops[j + 1]
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
                colors.append(tuple(int(round(c0[k] + (c1[k] - c0[k]) * u)) for k in range(3)))
                break
        else:
            colors.append(stops[-1][1])
    return colors


THEME_NAMES = ["NEON", "SOLAR", "AURORA", "MONO"]


def transform_color(rgb: tuple[int, int, int], theme: int) -> tuple[int, int, int]:
    if theme == 0:
        return rgb
    r, g, b = (v / 255.0 for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if theme == 1:          # SOLAR: warm orange/red
        h = (h + 0.55) % 1.0
        s = min(1.0, s * 1.12)
        v = min(1.0, v * 1.04)
    elif theme == 2:        # AURORA: green/cyan
        h = (h - 0.28) % 1.0
        s = min(1.0, s * 1.05)
        v = min(1.0, v * 1.02)
    else:                   # MONO: cool white/blue
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        r = lum * 0.82
        g = lum * 0.90
        b = min(1.0, lum * 1.18)
        return tuple(int(round(x * 255)) for x in (r, g, b))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return tuple(int(round(x * 255)) for x in (r, g, b))


def build_bg_palette(theme: int) -> list[int]:
    neon = grad([
        (0.00, hx("001040")),
        (0.12, hx("0030A0")),
        (0.26, hx("0060FF")),
        (0.40, hx("00A0FF")),
        (0.54, hx("00E0FF")),
        (0.66, hx("00FFD0")),
        (0.78, hx("78FFB4")),
        (0.88, hx("FF5AE6")),
        (1.00, hx("FFFFFF")),
    ])
    base = [
        hx("000008"), hx("020612"), hx("071028"), hx("0A2050"),
    ] + neon + [
        hx("080010"), hx("180028"), hx("300040"), hx("500060"),
        hx("140800"), hx("301400"), hx("602800"), hx("A05000"),
        hx("3C3C46"), hx("64646E"), hx("A0A0AA"), hx("DCDCE6"),
    ]
    assert len(base) == 32
    return [rgb555(*transform_color(c, theme)) for c in base]


OBJ_BASE = [
    ("FFFFFF", "1E2846", "FFFFFF"),   # 0 white HUD
    ("00DCFF", "001E46", "DCFFFF"),   # 1 cyan
    ("3C78FF", "00143C", "C8DCFF"),   # 2 blue
    ("AA50FF", "1E003C", "F0DCFF"),   # 3 violet
    ("FF4040", "8A1018", "FFB4A8"),   # 4 red (Neon City car, tail lights)
    ("FF9628", "3C1400", "FFF0C8"),   # 5 orange
    ("3CFF96", "003220", "DCFFE6"),   # 6 green
    ("FFD246", "3C2800", "FFFFF0"),   # 7 gold
]

# Palette 4 is a dedicated red ramp so the car can be shaded like the concept
# art: 1 bright, 4-10 stepping down to near black, 11/13/3 highlights, 12
# chrome, 14-15 black.
OBJ_RED = (
    "000000",
    "FF4040", "8A1018", "FFB4A8", "E02434", "C01C2A", "A21624", "7E101E",
    "5E0A16", "400610", "2A0208", "FF6A5A", "B0B0BC", "FF3020", "000000",
    "000000",
)


def build_obj_palettes(theme: int) -> list[list[int]]:
    out = []
    for index, (main, dark, high) in enumerate(OBJ_BASE):
        if index == 4:
            out.append([rgb555(*transform_color(hx(c), theme)) for c in OBJ_RED])
            continue
        m = transform_color(hx(main), theme)
        d = transform_color(hx(dark), theme)
        h = transform_color(hx(high), theme)
        shades = []
        for i in range(4):
            u = i / 3.0
            shades.append(tuple(int(round(m[k] + (d[k] - m[k]) * u * 0.55)) for k in range(3)))
        colors = [rgb555(0, 0, 0), rgb555(*m), rgb555(*d), rgb555(*h)]
        colors += [rgb555(*c) for c in shades]
        colors += [rgb555(0, 0, 0)] * 8
        assert len(colors) == 16
        out.append(colors)
    return out


# ---------------------------------------------------------------------------
# Tile graphics
# ---------------------------------------------------------------------------
def tile_4bpp(pattern: list[str]) -> bytes:
    rows01 = bytearray()
    rows23 = bytearray()
    for y in range(8):
        planes = [0, 0, 0, 0]
        for x, ch in enumerate(pattern[y]):
            if ch == ".":
                continue
            c = int(ch, 16)
            for p in range(4):
                if c & (1 << p):
                    planes[p] |= 0x80 >> x
        rows01 += bytes((planes[0], planes[1]))
        rows23 += bytes((planes[2], planes[3]))
    return bytes(rows01 + rows23)


def blank_tile() -> bytes:
    return bytes(32)


def glow16_tiles() -> dict[int, bytes]:
    grid = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            dx = x - 7.5
            dy = y - 7.5
            d = math.sqrt(dx * dx + dy * dy)
            if d < 2.6:
                grid[y][x] = 1
            elif d < 5.6:
                grid[y][x] = 2
            elif d < 7.7:
                grid[y][x] = 3
    out = {}
    for qy in range(2):
        for qx in range(2):
            pat = []
            for y in range(8):
                row = ""
                for x in range(8):
                    row += str(grid[qy * 8 + y][qx * 8 + x]) if grid[qy * 8 + y][qx * 8 + x] else "."
                pat.append(row)
            idx = GLOW16 + qx + qy * 16
            out[idx] = tile_4bpp(pat)
    return out


def bar16_tiles() -> dict[int, bytes]:
    grid = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if y == 0:
                grid[y][x] = 3
            elif x == 0 or x == 15:
                grid[y][x] = 2
            elif y == 15:
                grid[y][x] = 2
            else:
                # subtle vertical shading
                grid[y][x] = 1 if y < 10 else 2
    out = {}
    for qy in range(2):
        for qx in range(2):
            pat = []
            for y in range(8):
                row = ""
                for x in range(8):
                    row += str(grid[qy * 8 + y][qx * 8 + x]) if grid[qy * 8 + y][qx * 8 + x] else "."
                pat.append(row)
            out[BAR16 + qx + qy * 16] = tile_4bpp(pat)
    return out


def build_extra_tiles() -> bytes:
    tiles = [blank_tile() for _ in range(EXTRA_LAST - EXTRA_FIRST + 1)]

    def put(idx: int, pattern: list[str]) -> None:
        tiles[idx - EXTRA_FIRST] = tile_4bpp(pattern)

    put(STAR, [
        "........",
        "...1....",
        "...1....",
        "..121...",
        "1112111.",
        "..121...",
        "...1....",
        "........",
    ])
    put(HLINE, [
        "........",
        "........",
        "........",
        "11111111",
        "12222221",
        "........",
        "........",
        "........",
    ])
    put(VLINE, [
        "...11...",
        "...11...",
        "...21...",
        "...21...",
        "...21...",
        "...21...",
        "...11...",
        "...11...",
    ])
    put(SQUARE, [
        "........",
        "........",
        "..1111..",
        "..1221..",
        "..1221..",
        "..1111..",
        "........",
        "........",
    ])
    put(RING, [
        "........",
        "..1111..",
        ".1....1.",
        "1......1",
        "1......1",
        ".1....1.",
        "..1111..",
        "........",
    ])
    for idx, data in glow16_tiles().items():
        tiles[idx - EXTRA_FIRST] = data
    for idx, data in bar16_tiles().items():
        tiles[idx - EXTRA_FIRST] = data
    for idx, data in car_tile_map().items():
        tiles[idx - EXTRA_FIRST] = data
    out = b"".join(tiles)
    assert len(out) == (EXTRA_LAST - EXTRA_FIRST + 1) * 32
    return out


# ---------------------------------------------------------------------------
# Mode 7 image packing
# ---------------------------------------------------------------------------
def build_m7(pixels: list[list[int]]) -> list[int]:
    width = len(pixels[0])
    assert width % 8 == 0
    # Mode 7 works in 8x8 tiles; pad the bottom to a tile boundary.  The
    # visible window is still 224 scanlines, so the extra rows are unseen.
    height = (len(pixels) + 7) // 8 * 8
    pixels = pixels + [[0] * width for _ in range(height - len(pixels))]
    tiles_x = width // 8
    tiles_y = height // 8
    total_words = tiles_x * tiles_y * 64
    words = [0] * total_words
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            t = ty * tiles_x + tx
            for py in range(8):
                for px in range(8):
                    c = pixels[ty * 8 + py][tx * 8 + px]
                    if c:
                        words[t * 64 + py * 8 + px] |= c << 8
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            t = ty * tiles_x + tx
            idx = ty * 128 + tx
            words[idx] = (words[idx] & 0xFF00) | t
    return words


# ---------------------------------------------------------------------------
# Background art
# ---------------------------------------------------------------------------
def new_image(w: int, h: int) -> list[list[int]]:
    return [[0] * w for _ in range(h)]


def put(img: list[list[int]], x: int, y: int, c: int) -> None:
    if 0 <= y < len(img) and 0 <= x < len(img[0]):
        img[y][x] = c


def line(img: list[list[int]], x0: int, y0: int, x1: int, y1: int, c: int) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        put(img, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def add_stars(img: list[list[int]], count: int, seed: int, ymax: int | None = None) -> None:
    rnd = random.Random(seed)
    h = len(img)
    w = len(img[0])
    ymax = h if ymax is None else ymax
    for _ in range(count):
        x = rnd.randrange(w)
        y = rnd.randrange(ymax)
        r = rnd.random()
        if r < 0.72:
            c = rnd.choice([1, 2, 3])
        elif r < 0.93:
            c = rnd.choice([5, 6, 7, 8])
        else:
            c = 19
        put(img, x, y, c)
        if c >= 7:
            put(img, x + 1, y, c - 2)
            put(img, x, y + 1, c - 2)


def make_planet_bg() -> list[list[int]]:
    img = new_image(88, 77)
    # faint nebula bands
    for y in range(77):
        for x in range(88):
            v = math.sin(x * 0.11 + y * 0.07) + math.sin(x * 0.05 - y * 0.13)
            if v > 1.35:
                img[y][x] = 1
            elif v > 1.05:
                img[y][x] = 2
    # halo behind the planet
    for y in range(77):
        for x in range(88):
            d = math.sqrt((x - 44) ** 2 + (y - 39) ** 2)
            if 17 < d < 29:
                img[y][x] = max(img[y][x], 1)
            elif 13 < d <= 17:
                img[y][x] = max(img[y][x], 2)
    add_stars(img, 150, 11)
    return img


def make_pulse_bg() -> list[list[int]]:
    img = new_image(88, 77)
    # top glow
    for y in range(8):
        c = 2 if y < 2 else 1
        for x in range(88):
            img[y][x] = c
    # horizontal grid
    for y in range(8, 77, 8):
        c = 2 if (y // 8) % 4 == 0 else 1
        for x in range(88):
            img[y][x] = c
    # vertical grid / bar slots
    for x in range(8, 88, 8):
        for y in range(8, 77):
            if img[y][x] == 0:
                img[y][x] = 1
    # baseline and frame
    for x in range(88):
        img[62][x] = 3
        img[69][x] = max(img[69][x], 2)
    for y in range(77):
        img[y][0] = max(img[y][0], 2)
        img[y][87] = max(img[y][87], 2)
    return img


def make_city_bg() -> list[list[int]]:
    """Build one seamless 88px period, then duplicate it to 176px."""
    pw, h = 88, 77

    def putp(img: list[list[int]], x: int, y: int, c: int) -> None:
        if 0 <= y < h:
            img[y][x % pw] = c

    def linep(img: list[list[int]], x0: int, y0: int, x1: int, y1: int, c: int) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            putp(img, x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    img = new_image(pw, h)
    rnd = random.Random(23)
    for _ in range(62):
        x = rnd.randrange(pw)
        y = rnd.randrange(0, 40)
        r = rnd.random()
        c = rnd.choice([1, 2, 3]) if r < 0.75 else rnd.choice([5, 6, 8, 19])
        putp(img, x, y, c)
    # moon
    for y in range(h):
        for x in range(pw):
            d = math.sqrt((x - 58) ** 2 + (y - 12) ** 2)
            if d < 4.2:
                img[y][x] = 19
            elif d < 5.6:
                img[y][x] = 2
            elif d < 7.5:
                img[y][x] = max(img[y][x], 1)
    # horizon glow
    for y in range(40, 48):
        c = (14, 13, 12, 6, 3, 2, 1, 1)[y - 40]
        for x in range(pw):
            if img[y][x] == 0:
                img[y][x] = c
    # perspective ground grid
    for y in [48, 52, 57, 63, 70, 76]:
        for x in range(pw):
            img[y][x] = max(img[y][x], 2 if y < 60 else 3)
    for bx in range(0, pw, 8):
        steps = 30
        for s in range(steps + 1):
            t = s / steps
            x = int(round(44 + (bx - 44) * (t ** 1.55)))
            y = int(round(44 + (76 - 44) * t))
            if 0 <= y < h:
                putp(img, x, y, 2 if t < 0.6 else 3)
    # skyline: generate the buildings and their window patterns once.
    buildings = []
    x = 1
    while x < 86:
        bw = rnd.randint(6, 12)
        bh = rnd.randint(13, 34)
        style = rnd.random()
        windows = []
        for yy in range(44 - bh + 3, 43, 3):
            for xx in range(x + 2, x + bw - 2, 3):
                if rnd.random() < 0.45:
                    windows.append((xx, yy, 19 if rnd.random() < 0.22 else 18))
        buildings.append((x, bw, bh, style, windows))
        x += bw + rnd.randint(2, 7)
    for (bx, bw, bh, style, windows) in buildings:
        top = 44 - bh
        fill = 1 if style < 0.5 else 2
        edge = 7 if style < 0.5 else 14
        high = 8 if style < 0.5 else 15
        for yy in range(top, 44):
            for xx in range(bx, bx + bw):
                putp(img, xx, yy, fill)
        for yy in range(top, 44):
            putp(img, bx, yy, edge)
            putp(img, bx + bw - 1, yy, edge)
        for xx in range(bx, bx + bw):
            putp(img, xx, top, high)
        for (xx, yy, c) in windows:
            putp(img, xx, yy, c)
        if bh > 28:
            ax = bx + bw // 2
            for yy in range(top - 4, top):
                if 0 <= yy < h:
                    putp(img, ax, yy, 6)
    # foreground silhouette
    for y in range(74, h):
        for x in range(pw):
            img[y][x] = 1 if img[y][x] == 0 else img[y][x]
        for x in range(pw):
            img[74][x] = max(img[74][x], 3)
    return [row + row for row in img]


# ---------------------------------------------------------------------------
# Neon City: synthwave skyline over a perspective Mode 7 floor
# ---------------------------------------------------------------------------
# The screen is split in two by HDMA.  Above NEON_HORIZON the Mode 7 matrix
# shows the 176x49 skyline at 1.45 screen pixels per texel.  Below it the
# matrix is rewritten on every scanline so the plane becomes a real floor:
# M7A = scale, M7B = shear (puts the vanishing point on the screen centre) and
# M7VOFS = the texture row, all derived from one 1/(depth) curve.  M7VOFS is
# taken from 32 precomputed tables; stepping through them slides the grid
# towards the camera.  The plane below the skyline is one seamless 64x64 grid
# cell, so the wrap at the end of each table is invisible.
NEON_PLANE = 1024
NEON_SKY_W = 176
NEON_SKY_H = 49
NEON_HORIZON = 140
NEON_D0 = 67.0          # depth offset: the true vanishing point hides behind the city
NEON_C = 63650.0        # texels * depth of the virtual horizon line
NEON_FOCAL = 424.3      # screen pixels per texel at unit depth
NEON_CELL = 64          # row spacing, in texels
NEON_CELL_COL = 32      # column spacing, in texels
NEON_ROAD_HALF = 78     # road half width, in texels
NEON_GRID_PHASE = 96    # puts the first grid line just outside the road edge
NEON_PHASES = 32
NEON_PHASE_STEP = 2     # texels of forward travel per precomputed table
NEON_FRAMES = 1         # the car is static; the floor supplies the motion
NEON_FLOOR_ROW = 128    # first plane row that carries the floor texture

# Background palette used by scene 5 only (theme transform still applies).
NEON_BG_BASE = (
    "000000",                                            # 0  black
    "020320", "030330", "040240", "060250", "070260",     # 1  sky
    "090272", "0A0282", "0C0292", "0E02A2", "1002B2",     # 6
    "1200BE",                                            # 11 horizon glow
    "E8472A", "FF6A30", "FF8A3C", "ED2E74", "D82BC8",     # 12 sun
    "A828E0",                                            # 17
    "0A0314", "160628", "2A0A40", "5E1668",               # 18 skyline
    "00C8DC", "58E8F8", "04303A",                         # 22 grid
    "081826", "182A40", "20344C",                         # 25 ground / road
    "FF3CC8", "FFD24A", "B8BCC8", "FFFFFF",               # 28 accents
)


def build_neon_bg_palette(theme: int) -> list[int]:
    assert len(NEON_BG_BASE) == 32
    return [rgb555(*transform_color(hx(c), theme)) for c in NEON_BG_BASE]


def neon_scale(y: int) -> int:
    """M7A for one scanline: the skyline is shown at 176 texels across."""
    if y < NEON_HORIZON:
        return NEON_SKY_W
    d = y - NEON_HORIZON
    return max(1, min(0x7FFF, int(round(256.0 * NEON_C / (NEON_FOCAL * (d + NEON_D0))))))


def neon_shear(y: int) -> int:
    """M7B: shear that keeps every floor scanline centred on x = 128."""
    if y < NEON_HORIZON:
        return 0
    return -int(round(128.0 * neon_scale(y) / y))


def neon_row(y: int, phase: int = 0) -> int:
    """Texture row the scanline must sample; phase walks the floor forward."""
    if y < NEON_HORIZON:
        return (y * NEON_SKY_H) // NEON_HORIZON
    d = y - NEON_HORIZON
    return int(round(NEON_C / (d + NEON_D0))) + phase * NEON_PHASE_STEP


def neon_depth(y: int, phase: int = 0) -> int:
    """M7D for one scanline: the PPU samples row sy * M7D / 256.

    The register only takes integers, so pick the value whose truncation lands
    exactly on the intended row instead of rounding the depth.
    """
    if y == 0:
        return 0
    row = neon_row(y, phase)
    lo = (256 * row + y - 1) // y
    hi = (256 * (row + 1) - 1) // y
    if lo <= hi:
        return lo
    return int(round(256.0 * row / y))


def neon_hdma_table(values) -> bytes:
    """Mode 2 HDMA table: one 16-bit write per scanline, then a terminator."""
    out = bytearray()
    for value in values:
        v = value & 0xFFFF
        out += bytes((0x01, v & 0xFF, v >> 8))
    out.append(0x00)
    return bytes(out)


def neon_hdma_tables() -> tuple[bytes, bytes, list[bytes]]:
    scale = neon_hdma_table([neon_scale(y) for y in range(224)])
    shear = neon_hdma_table([neon_shear(y) for y in range(224)])
    tables = [neon_hdma_table([neon_depth(y, p) for y in range(224)]) for p in range(NEON_PHASES)]
    return scale, shear, tables


def _neon_sky() -> list[list[int]]:
    w, h = NEON_SKY_W, NEON_SKY_H
    img = new_image(w, h)
    bayer = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

    # Vertical gradient: flat bands with a one-row checker blend, which keeps
    # the synthwave banding without the screen-door dither noise.
    for y in range(h):
        f = (y / (h - 1)) ** 2.2 * 10.0
        i0 = min(int(f), 9)
        lo = 1 + i0
        hi = min(11, lo + 1)
        frac = f - i0
        if frac < 0.25:
            img[y] = [lo] * w
        elif frac > 0.75:
            img[y] = [hi] * w
        else:
            img[y] = [hi if (x & 1) else lo for x in range(w)]

    # Dark cloud streaks in the upper sky.
    rnd = random.Random(77)
    for _ in range(18):
        cy = rnd.randrange(2, 26)
        cx = rnd.randrange(-12, w)
        ln = rnd.randrange(10, 52)
        for xx in range(max(0, cx), min(w, cx + ln)):
            if img[cy][xx] > 2:
                img[cy][xx] -= 1
        if rnd.random() < 0.45 and cy + 1 < h:
            for xx in range(max(0, cx), min(w, cx + ln // 2)):
                if img[cy + 1][xx] > 2:
                    img[cy + 1][xx] -= 1

    # Striped sun: orange crown, pink belly, one-texel gaps that show the sky.
    sun_cx, sun_cy, sun_rx, sun_ry = 88.0, 29.5, 41.3, 18.6
    colours = (12, 12, 13, 13, 14, 15, 15, 16, 16, 17, 17)
    first, last = 11, h - 1
    bands: list[tuple[int, int, int | None]] = []
    ci = 0
    y = first
    while y <= last:
        thick = 3 if y - first < 21 else 2
        thick = min(thick, last - y + 1)
        bands.append((y, y + thick - 1, colours[min(ci, len(colours) - 1)]))
        ci += 1
        y += thick
        if y <= last:
            bands.append((y, y, None))
            y += 1
    band_of_row: dict[int, int | None] = {}
    for (a, b, c) in bands:
        for yy in range(a, b + 1):
            band_of_row[yy] = c
    for y in range(first, last + 1):
        col = band_of_row.get(y)
        if col is None:
            continue
        for x in range(w):
            if ((x - sun_cx) / sun_rx) ** 2 + ((y - sun_cy) / sun_ry) ** 2 <= 1.0:
                img[y][x] = col

    # Solid skyline base with a magenta glow leaking between the towers.
    for y in range(h - 4, h):
        for x in range(w):
            img[y][x] = 18
    for y in range(h - 2, h):
        for x in range(w):
            img[y][x] = 28

    # Skyline: dense blocks with a few landmark towers, like the concept art.
    rnd = random.Random(9182)
    blocks: list[tuple[int, int, int, float]] = []
    x = -2
    while x < w:
        bw = rnd.choice((5, 6, 6, 7, 8, 9, 10))
        bh = rnd.choice((4, 5, 6, 7, 8, 9, 10, 11))
        blocks.append((x, bw, bh, rnd.random()))
        x += bw + rnd.choice((0, 1, 1, 2))
    blocks += [(20, 7, 15, 0.15), (30, 5, 13, 0.2), (116, 4, 17, 0.25),
               (130, 7, 15, 0.3), (140, 8, 12, 0.4), (50, 5, 14, 0.35),
               (94, 5, 16, 0.45)]
    for (bx, bw, bh, st) in blocks:
        top = h - 1 - bh
        body = 18 if st < 0.5 else 19
        for y in range(max(0, top), h):
            for x in range(bx, bx + bw):
                if 0 <= x < w:
                    img[y][x] = body
        for x in range(bx, bx + bw):
            if 0 <= x < w:
                img[top][x] = 20
        if bh >= 14:
            ax = bx + bw // 2
            for y in range(top - 2, top):
                if 0 <= y and 0 <= ax < w:
                    img[y][ax] = 20

    # A handful of lit windows keeps the skyline alive without confetti.
    for (wx, wy, c) in ((26, 44, 29), (63, 45, 29), (88, 45, 29),
                        (119, 44, 29), (146, 45, 29), (35, 45, 29)):
        if 0 <= wx < w:
            img[wy][wx] = c
    return img


def neon_floor_colour(u: int, v: int) -> int:
    """One texel of the floor: road in the middle, neon grid on both sides.

    Columns are spaced every 32 texels and rows every 64 texels; on screen at
    the bottom of the road that reads as cells a little wider than they are
    deep, which is what the concept art shows.
    """
    su = u if u < NEON_PLANE // 2 else u - NEON_PLANE
    au = abs(su)
    vm = v & (NEON_CELL - 1)
    if au <= NEON_ROAD_HALF:
        if au <= 2 and 8 <= vm < 44:
            return 29                       # centre dashes
        if au >= NEON_ROAD_HALF - 4:
            return 28                       # neon road edge
        if au >= NEON_ROAD_HALF - 8:
            return 27                       # inner edge highlight
        return 26                           # asphalt
    um = (u - NEON_GRID_PHASE) & (NEON_CELL_COL - 1)
    lu = um < 2
    lv = vm < 2
    if lu and lv:
        return 23                           # intersection
    if lu or lv:
        return 22                           # cyan grid
    if um < 4 or vm < 4:
        return 24                           # faint bloom beside the line
    return 25                               # ground


def _neon_floor_rows() -> list[bytes]:
    rows = []
    for vm in range(NEON_CELL):
        rows.append(bytes(neon_floor_colour(u, vm) for u in range(NEON_PLANE)))
    return rows


def make_neon_city_plane() -> bytearray:
    """1024x1024 Mode 7 plane: skyline above, seamless floor texture below."""
    px = bytearray(NEON_PLANE * NEON_PLANE)
    sky = _neon_sky()
    for y, row in enumerate(sky):
        base = y * NEON_PLANE
        px[base:base + NEON_SKY_W] = bytes(row)
    floor_rows = _neon_floor_rows()
    for y in range(NEON_FLOOR_ROW, NEON_PLANE):
        base = y * NEON_PLANE
        px[base:base + NEON_PLANE] = floor_rows[y & (NEON_CELL - 1)]
    return px


def build_m7_plane(px: bytearray) -> list[int]:
    """Pack the full plane into Mode 7 words, deduplicating 8x8 tiles."""
    words = [0] * 16384
    tiles: dict[bytes, int] = {}
    for ty in range(128):
        for tx in range(128):
            pat = bytes(px[(ty * 8 + py) * NEON_PLANE + tx * 8 + px_x]
                        for py in range(8) for px_x in range(8))
            idx = tiles.get(pat)
            if idx is None:
                idx = len(tiles)
                if idx >= 256:
                    raise ValueError("mode 7 plane needs more than 256 tiles")
                tiles[pat] = idx
                for py in range(8):
                    for pxx in range(8):
                        c = pat[py * 8 + pxx]
                        if c:
                            words[idx * 64 + py * 8 + pxx] |= c << 8
            words[ty * 128 + tx] = (words[ty * 128 + tx] & 0xFF00) | idx
    return words


CAR_FIRST = 144
CAR_COLS, CAR_ROWS = 5, 2
CAR_X, CAR_Y = 88, 168
CAR_W, CAR_H = CAR_COLS * 16, CAR_ROWS * 16

# Rear view traced from References/NeonCityConcept.jpg, 64x32, drawn with the
# red object palette 4 (see OBJ_RED): roof rim, black rear window, red tail
# lights and a dark bumper.
CAR_ART = (
"00000000000000000000000000000000000000000000000000000000000000000000000000000000",
"00000000000000000000000000000000000000000000000000000000000000000000000000000000",
"00000000000000000000006556666666666665B66666666666666666666000000000000000000000",
"00000000000000000000075555555555555555555555555555555555555700000000000000000000",
"00000000000000000000762777777777777777777777777777777777722560000000000000000000",
"00000000000000000006677770000000000000000000000000000000772266000000000000000000",
"00000000000000000656777900000000000000000000000000000000087722570000000000000000",
"00000000000000006666770000000000000000000000000000000000000777266000000000000000",
"00000000000000066662700000000000000000000000000000000000000087266600000000000000",
"00000000000000766678000000000000000000000000000000000000000008766667000000000000",
"00000009889007622780000000000000000000000000000000000000000000976267009889000000",
"00000008889977222788888888888888888888888888888888888888888888872267799999000000",
"00000000008766266666666666627777777777777777777777772226666666662226678000000000",
"00000000006666277722266662277778888888888888888888877726666666627772256000000000",
"00000000056662798888777777889A000000000000000000000A9877222227788977226570000000",
"00000007622278985444444444469900000000000000000000098644444444446898726656000000",
"000000667777997B1D444444444589A00000000000000000000985444444444D1128972226500000",
"00000066777796111D444444444589A00000000000000000000985444444444D11B5977276500000",
"000000667789961DDD444444444699A0000000000000000000098544444444441116998776500000",
"000000667780A8726666662222279900000000000000000000099722226666666228009776500000",
"00000066777888777722227777778888888888888888888888888777772222222777888726500000",
"00000066778777777772277777777777777777777777777777777777222222222777777776600000",
"00000077799999998888888889999999999999999999999999999988888888888889999977700000",
"00000077799999999999999999999999999999999999999999999999999999999999999977700000",
"00000077799999999999999999999999999999999999999999999999999999999999999977800000",
"00000009799999999999999999999999999999999999999999999999999999999999999979000000",
"00000000899000000000000000000000000000000000000000000000000000000000009989000000",
"00000000000000000000000000000000000000000000000000000000000000000000000000000000",
"00000000000000000000000000000000000000000000000000000000000000000000000000000000",
"00000000000000000000000000000000000000000000000000000000000000000000000000000000",
"00000000000000000000000000000000000000000000000000000000000000000000000000000000",
"00000000000000000000000000000000000000000000000000000000000000000000000000000000",
)


def make_car_art() -> list[list[int]]:
    img = [[int(ch, 16) for ch in row] for row in CAR_ART]
    assert len(img) == CAR_H and len(img[0]) == CAR_W
    # The concept art picked up pale road-glow reflections along the flanks;
    # keep the body red and reserve chrome for the plate.
    for y in range(CAR_H):
        for x in range(CAR_W):
            if img[y][x] == 12:
                img[y][x] = 8
    # Contact shadow so the car sits on the asphalt.
    for i, (x0, x1) in enumerate(((6, 57), (10, 53), (15, 48), (21, 42), (27, 36))):
        for x in range(x0, x1 + 1):
            img[27 + i][x] = 10
    _draw_car_wheels(img)
    _fill_car_holes(img)
    return img


def _draw_car_wheels(img: list[list[int]]) -> None:
    """Two dark rear tyres tucked under the haunches, with a chrome glint.

    The rear view hides most of the wheels, but without them the car reads as
    a floating slab, so the tyres poke out below the bumper line.
    """
    h, w = len(img), len(img[0])
    for (x0, x1) in ((5, 18), (61, 74)):
        for y in range(24, 30):
            inset = 2 if y == 29 else 0
            for x in range(x0 + inset, x1 - inset + 1):
                if 0 <= x < w:
                    img[y][x] = 14
        # A dark red lip keeps the tyre readable against the bumper above it.
        for x in range(x0 + 1, x1):
            if 0 <= x < w:
                img[24][x] = 9
        # Chrome rim glint on the outer top corner.
        for (gx, gy) in ((x0 + 1, 25), (x0 + 1, 26), (x1 - 1, 25), (x1 - 1, 26)):
            if 0 <= gx < w and 0 <= gy < h:
                img[gy][gx] = 12
        # Faint tread sheen across the contact patch.
        for x in range(x0 + 4, x1 - 3):
            if 0 <= x < w:
                img[27][x] = 8


def _fill_car_holes(img: list[list[int]]) -> None:
    """Paint the glass and the plate: transparent holes must not show the road.

    Pixels that are transparent but enclosed by the body are holes; the big one
    is the rear window, the small one is the plate panel between the lights.
    """
    h, w = len(img), len(img[0])
    outside = [[False] * w for _ in range(h)]
    stack: list[tuple[int, int]] = []
    for x in range(w):
        for y in (0, h - 1):
            if img[y][x] == 0 and not outside[y][x]:
                outside[y][x] = True
                stack.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if img[y][x] == 0 and not outside[y][x]:
                outside[y][x] = True
                stack.append((x, y))
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not outside[ny][nx] and img[ny][nx] == 0:
                outside[ny][nx] = True
                stack.append((nx, ny))

    holes: list[tuple[int, int]] = [(x, y) for y in range(h) for x in range(w)
                                    if img[y][x] == 0 and not outside[y][x]]
    seen: set[tuple[int, int]] = set()
    for start in holes:
        if start in seen:
            continue
        comp = [start]
        seen.add(start)
        stack = [start]
        while stack:
            x, y = stack.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and img[ny][nx] == 0 and not outside[ny][nx] and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    comp.append((nx, ny))
                    stack.append((nx, ny))
        xs = [p[0] for p in comp]
        ys = [p[1] for p in comp]
        if min(ys) < 12:
            # Rear window: near-black glass with a soft top reflection.
            for (x, y) in comp:
                img[y][x] = 10
            for x in range(min(xs), max(xs) + 1):
                if img[min(ys)][x] == 10:
                    img[min(ys)][x] = 8
        elif len(comp) >= 40:
            # Centre panel between the lights, with the plate on it.
            for (x, y) in comp:
                img[y][x] = 8
            cx = (min(xs) + max(xs)) // 2
            cy = (min(ys) + max(ys)) // 2
            for y in range(cy - 1, cy + 1):
                for x in range(cx - 3, cx + 4):
                    if 0 <= y < h and 0 <= x < w:
                        img[y][x] = 12
            for x in range(cx - 2, cx + 3):
                if 0 <= cy + 1 < h and 0 <= x < w:
                    img[cy + 1][x] = 14
        else:
            # Pinholes from the tracing: just close them with body shadow.
            for (x, y) in comp:
                img[y][x] = 2


def car_sprite_base(row: int, col: int) -> int:
    """Tile number of one car sprite; 16x16 sprites use n, n+1, n+16, n+17."""
    return CAR_FIRST + row * 32 + col * 2


def car_tile_map() -> dict[int, bytes]:
    art = make_car_art()
    out: dict[int, bytes] = {}
    for row in range(CAR_ROWS):
        for col in range(CAR_COLS):
            base = car_sprite_base(row, col)
            for qy in range(2):
                for qx in range(2):
                    pat = []
                    for y in range(8):
                        line = ""
                        for x in range(8):
                            line += "0123456789ABCDEF"[art[row * 16 + qy * 8 + y][col * 16 + qx * 8 + x]]
                        pat.append(line)
                    out[base + qy * 16 + qx] = tile_4bpp(pat)
    return out


def make_atomic_bg() -> list[list[int]]:
    img = new_image(88, 77)
    for y in range(77):
        for x in range(88):
            d = math.sqrt((x - 44) ** 2 + (y - 39) ** 2)
            if d < 4:
                img[y][x] = 8
            elif d < 8:
                img[y][x] = 6
            elif d < 11:
                img[y][x] = 5
    # dotted circular guides
    for radius in (16, 24, 32):
        for a in range(0, 360, 6):
            x = int(round(44 + radius * math.cos(math.radians(a))))
            y = int(round(39 + radius * math.sin(math.radians(a)) * 0.55))
            if 0 <= x < 88 and 0 <= y < 77 and img[y][x] == 0:
                img[y][x] = 3
    # crosshair
    for x in range(10, 78):
        if img[39][x] == 0:
            img[39][x] = 1
    for y in range(8, 70):
        if img[y][44] == 0:
            img[y][44] = 1
    add_stars(img, 90, 31)
    return img


def make_lissajous_bg() -> list[list[int]]:
    img = new_image(88, 77)
    for x in range(88):
        img[1][x] = 6
        img[75][x] = 6
    for y in range(77):
        img[y][1] = 6
        img[y][86] = 6
    for x in range(1, 87):
        img[39][x] = 3
    for y in range(1, 76):
        img[y][44] = 3
    # faint dotted sub-grid
    for y in range(8, 77, 8):
        for x in range(8, 88, 8):
            if img[y][x] == 0:
                img[y][x] = 1
    return img


# ---------------------------------------------------------------------------
# OAM frame building
# ---------------------------------------------------------------------------
class Frame:
    def __init__(self) -> None:
        self.sprites: list[tuple[int, int, int, int, bool]] = []

    def add(self, x: int, y: int, tile: int, pal: int, large: bool = False, priority: int = 2) -> None:
        if len(self.sprites) >= SPRITE_SLOTS:
            raise ValueError("too many sprites in frame")
        self.sprites.append((x, y, tile, (priority << 4) | (pal << 1), large))

    def data(self) -> bytes:
        low = bytearray()
        high = [0] * 24
        for i in range(SPRITE_SLOTS):
            if i < len(self.sprites):
                x, y, tile, attr, large = self.sprites[i]
                low += bytes((x & 0xFF, (y - 1) & 0xFF, tile & 0xFF, attr & 0xFF))
            else:
                low += bytes((0, 0xF0, 0, 0))
                large = False
            if large:
                high[i >> 2] |= 1 << (((i & 3) * 2) + 1)
        return bytes(low) + bytes(high)


def clamp(v: float, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(v))))


def holo_frames() -> list[bytes]:
    frames = []
    lats = [-72, -45, -18, 18, 45, 72]
    nlon = 9
    radius = 52.0
    for f in range(FRAME_COUNT):
        fr = Frame()
        t = f / FRAME_COUNT
        rot = 2.0 * math.pi * t
        points: list[tuple[float, int, int, int, int]] = []  # z, x, y, tile, pal
        for lat_deg in lats:
            lat = math.radians(lat_deg)
            for j in range(nlon):
                lon = 2.0 * math.pi * j / nlon + rot
                x3 = math.cos(lat) * math.sin(lon)
                y3 = math.sin(lat)
                z3 = math.cos(lat) * math.cos(lon)
                s = 1.0 + 0.10 * z3
                px = int(round(128 + radius * x3 * s))
                py = int(round(104 + radius * y3 * s))
                if z3 > 0.35:
                    tile, pal = DOT_LARGE, 1
                elif z3 > -0.15:
                    tile, pal = DOT_MID, 3
                else:
                    tile, pal = DOT_SMALL, 2
                points.append((z3, px, py, tile, pal))
        # Planetary ring.  The ring is deliberately static: a fraction of a
        # turn per loop would make the whole scene jump when frame 119 wraps
        # back to frame 0.
        for j in range(24):
            u = 2.0 * math.pi * j / 24
            px = int(round(128 + 80 * math.cos(u)))
            py = int(round(104 + 25 * math.sin(u)))
            z = math.sin(u)
            if z > 0.05:
                tile, pal = DOT_MID, 4
            else:
                tile, pal = DOT_SMALL, 2
            points.append((z, px, py, tile, pal))
        points.sort(key=lambda p: p[0])
        for z, px, py, tile, pal in points:
            fr.add(px, py, tile, pal)
        # Moons and their faint trails.  One whole orbit per loop keeps the
        # wrap from frame 119 to frame 0 invisible.
        for m in range(2):
            ang = 2.0 * math.pi * (t + m * 0.5) + 0.7
            mx = 128 + int(round(104 * math.cos(ang)))
            my = 104 + int(round(42 * math.sin(ang)))
            pal = 5 if m == 0 else 7
            for k in (4, 3, 2, 1):
                ta = ang - k * 0.035
                tx = 128 + int(round(104 * math.cos(ta)))
                ty = 104 + int(round(42 * math.sin(ta)))
                fr.add(tx, ty, DOT_SMALL, pal)
            fr.add(mx - 8, my - 8, GLOW16, pal, large=True)
        fr.add(128 - 8, 104 - 8, GLOW16, 0, large=True)
        frames.append(fr.data())
    return frames


def pulse_frames() -> list[bytes]:
    xs = [20 + i * 23 for i in range(10)]
    baseline = 184
    levels = [[0] * FRAME_COUNT for _ in range(10)]
    for i in range(10):
        for f in range(FRAME_COUNT):
            t = f / FRAME_COUNT
            v = (0.50
                 + 0.22 * math.sin(i * 0.55 + 2 * math.pi * t * 2)
                 + 0.16 * math.sin(i * 1.70 - 2 * math.pi * t * 3)
                 + 0.12 * math.sin(i * 3.20 + 2 * math.pi * t * 5))
            levels[i][f] = max(0, min(4, int(v * 5)))
    peaks = [[0] * FRAME_COUNT for _ in range(10)]
    for i in range(10):
        for f in range(FRAME_COUNT):
            peaks[i][f] = max(levels[i][(f - k) % FRAME_COUNT] for k in range(0, 14))
    frames = []
    for f in range(FRAME_COUNT):
        fr = Frame()
        t = f / FRAME_COUNT
        for i, x in enumerate(xs):
            lv = levels[i][f]
            for b in range(lv):
                y = baseline - 16 * (b + 1)
                pal = (4, 3, 2, 1)[b]
                fr.add(x, y, BAR16, pal, large=True)
            cap_y = baseline - 16 * lv - 4
            fr.add(x + 4, cap_y, STAR, 0)
            pk = peaks[i][f]
            fr.add(x + 4, baseline - 16 * pk - 8, STAR, 7)
        # waveform
        for i in range(24):
            x = 8 + i * 10
            y = (204
                 + 12 * math.sin(i * 0.55 + 2 * math.pi * t * 3)
                 + 4 * math.sin(i * 1.70 - 2 * math.pi * t * 5))
            fr.add(x, int(round(y)), DOT_SMALL if i % 2 else DOT_MID, 6)
        # BPM pulse ring
        beat = (f % 30) / 30.0
        rr = 15 + 11 * (1.0 - beat)
        pal = 0 if beat < 0.55 else 7
        for j in range(12):
            a = 2.0 * math.pi * j / 12
            x = 128 + int(round(rr * 2.0 * math.cos(a)))
            y = 48 + int(round(rr * 0.55 * math.sin(a)))
            fr.add(x, y, DOT_SMALL, pal)
        frames.append(fr.data())
    return frames


def city_frames() -> list[bytes]:
    frames = []
    rnd = random.Random(41)
    cars = []
    for i in range(24):
        cars.append((
            rnd.randrange(256),
            1 + (i % 3),
            42 + (i * 17) % 140,
            (i % 3),
            i % 2,
        ))
    stars = [(rnd.randrange(256), rnd.randrange(20, 110), i) for i in range(6)]
    for f in range(FRAME_COUNT):
        fr = Frame()
        for i, (base, speed, y, kind, direction) in enumerate(cars):
            if direction:
                x = (base + f * speed * 2) % 256
            else:
                x = (base - f * speed * 2) % 256
            pal = (5, 7, 4)[kind]
            fr.add(x, y, HLINE, pal)
        for i in range(6):
            x = (i * 43 + 20) % 256
            y = 30 + (i * 29 + f * 3) % 150
            fr.add(x, y, VLINE, 6)
        for (x, y, i) in stars:
            if (f + i * 13) % 80 < 44:
                fr.add(x, y, STAR, 0)
        frames.append(fr.data())
    return frames


def neon_city_frames() -> list[bytes]:
    """The rear-view car, stamped once.

    Everything that moves in this scene is the Mode 7 floor, so a single frame
    is enough: the car sprite sits on top of the moving grid and the OAM
    pipeline keeps refreshing it every frame.
    """
    car = [(CAR_X + col * 16, CAR_Y + row * 16, car_sprite_base(row, col))
           for row in range(CAR_ROWS) for col in range(CAR_COLS)]
    fr = Frame()
    for (x, y, tile) in car:
        fr.add(x, y, tile, 4, large=True)
    return [fr.data()]


def atomic_frames() -> list[bytes]:
    frames = []
    orbits = [(78, 30, math.radians(0)), (72, 26, math.radians(60)), (66, 34, math.radians(120))]
    for f in range(FRAME_COUNT):
        fr = Frame()
        t = f / FRAME_COUNT
        precess = 0.18 * math.sin(2 * math.pi * t)
        for oi, (a, b, tilt0) in enumerate(orbits):
            tilt = tilt0 + precess * (1 if oi % 2 == 0 else -1)
            ct, st = math.cos(tilt), math.sin(tilt)
            # No fractional turn here: the old 0.30-turn drift made the whole
            # orbit snap every time the 120-frame loop restarted.  The dotted
            # guide ellipse is steady and the precession supplies its motion.
            phase0 = oi * 0.7
            for j in range(16):
                p = 2 * math.pi * j / 16 + phase0
                ex = a * math.cos(p)
                ey = b * math.sin(p)
                x = 128 + ex * ct - ey * st
                y = 104 + ex * st + ey * ct
                fr.add(int(round(x)), int(round(y)), DOT_SMALL, 2 if oi != 1 else 3)
            # electron and trail
            ep = 2 * math.pi * (t * 2.0 + oi / 3.0) + phase0
            pal = (1, 4, 7)[oi]
            for k in (4, 3, 2, 1):
                p = ep - k * 0.055
                ex = a * math.cos(p)
                ey = b * math.sin(p)
                x = 128 + ex * ct - ey * st
                y = 104 + ex * st + ey * ct
                fr.add(int(round(x)), int(round(y)), DOT_SMALL, pal)
            ex = a * math.cos(ep)
            ey = b * math.sin(ep)
            x = 128 + ex * ct - ey * st
            y = 104 + ex * st + ey * ct
            fr.add(int(round(x)) - 8, int(round(y)) - 8, GLOW16, pal, large=True)
        # nucleus cluster
        pulse = 1.5 * math.sin(2 * math.pi * t * 4)
        for k, (ox, oy, pal) in enumerate(((0, -2, 0), (-7, 5, 5), (7, 4, 7))):
            x = 128 + ox + int(round(pulse * (1 if k else 0.5)))
            y = 104 + oy + int(round(pulse * (0.6 if k == 1 else -0.4)))
            fr.add(x - 8, y - 8, GLOW16, pal, large=True)
        # energy ring
        rr = 16 + 3 * math.sin(2 * math.pi * t * 4)
        for j in range(12):
            a = 2 * math.pi * j / 12
            fr.add(int(round(128 + rr * math.cos(a))),
                   int(round(104 + rr * 0.6 * math.sin(a))), DOT_SMALL, 6)
        frames.append(fr.data())
    return frames


# ---------------------------------------------------------------------------
# Selector tilemaps
# ---------------------------------------------------------------------------
SCENE_NAMES = ["HOLO PLANET", "PULSE ANALYZER", "VECTOR CITY", "ATOMIC",
               "LISSAJOUS", "NEON CITY"]


def selector_map(sel: int, party: bool) -> bytes:
    entries = [0] * (32 * 32)

    def text(row: int, col: int, s: str, pal: int) -> None:
        if col < 0 or col + len(s) > 32:
            raise ValueError((row, col, s))
        for i, ch in enumerate(s):
            code = ord(ch)
            if not (32 <= code < 96):
                raise ValueError(f"bad char {ch!r}")
            entries[row * 32 + col + i] = (code - 32) | (pal << 10)

    def centered(row: int, s: str, pal: int) -> None:
        text(row, (32 - len(s)) // 2, s, pal)

    centered(0, "-" * 32, 1)
    centered(2, "NEON SCENES", 1)
    centered(3, "A SNES GENERATIVE SCENE DEMO", 0)
    centered(5, "SCENE SELECTOR", 1)
    for i, name in enumerate(SCENE_NAMES):
        row = 7 + i
        marker = "> " if i == sel else "  "
        s = f"{marker}{i + 1} {name}"
        text(row, 3, s, 2 if i == sel else 0)
    centered(13, f"PARTY MODE: {'ON ' if party else 'OFF'}", 2 if party else 0)
    centered(15, "UP/DOWN SELECT  LEFT/RIGHT PARTY", 0)
    centered(17, "START LAUNCH     SELECT PARTY", 0)
    centered(19, "DEMO: L/R SCENE  A BLACKOUT", 0)
    centered(21, "X THEME   Y HUD   B PAUSE", 0)
    centered(23, "SELECT RETURNS TO THIS MENU", 0)
    centered(25, "PRESS START", 2)
    centered(27, "-" * 32, 1)
    out = bytearray()
    for e in entries:
        out += bytes((e & 0xFF, e >> 8))
    return bytes(out)


# ---------------------------------------------------------------------------
# WLA emission helpers
# ---------------------------------------------------------------------------
def db_rows(data: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        lines.append("  .DB " + ", ".join(f"${b:02X}" for b in chunk))
    return "\n".join(lines)


def dw_words(words: list[int], width: int = 12) -> str:
    lines = []
    for i in range(0, len(words), width):
        chunk = words[i:i + width]
        lines.append("  .DW " + ", ".join(f"${w:04X}" for w in chunk))
    return "\n".join(lines)


def ptr_bytes(label: str) -> str:
    return f".DB <{label}, >{label}, :{label}"


# ---------------------------------------------------------------------------
# Layout / main
# ---------------------------------------------------------------------------
class BankAllocator:
    def __init__(self, first: int) -> None:
        self.bank = first
        self.offset = 0
        self.banks: dict[int, list[tuple[str, bytes, str]]] = {}
        self.locations: dict[str, tuple[int, int]] = {}

    def _new_bank(self) -> None:
        self.bank += 1
        self.offset = 0

    def add(self, label: str, data: bytes, kind: str = "db", at_bank_start: bool = False) -> None:
        if at_bank_start:
            if self.offset != 0:
                self._new_bank()
        if self.offset + len(data) > 0x8000:
            self._new_bank()
        if self.offset + len(data) > 0x8000:
            raise ValueError(f"item {label} ({len(data)} bytes) does not fit a bank")
        self.locations[label] = (self.bank, self.offset)
        self.banks.setdefault(self.bank, []).append((label, data, kind))
        self.offset += len(data)


def main() -> None:
    SRC.mkdir(parents=True, exist_ok=True)

    themes_bg = [build_bg_palette(t) for t in range(4)]
    themes_neon = [build_neon_bg_palette(t) for t in range(4)]
    themes_obj = [[c for pal in build_obj_palettes(t) for c in pal] for t in range(4)]
    extra_tiles = build_extra_tiles()

    bg_builders = [make_planet_bg, make_pulse_bg, make_city_bg, make_atomic_bg,
                   make_lissajous_bg]
    frame_builders = [holo_frames, pulse_frames, city_frames, atomic_frames,
                      None, neon_city_frames]
    bg_data = [build_m7(bg()) for bg in bg_builders]
    bg_data.append(build_m7_plane(make_neon_city_plane()))
    frame_data = [builder() if builder else None for builder in frame_builders]
    for scene, frames in enumerate(frame_data):
        if frames is None:
            continue
        for i, f in enumerate(frames):
            if len(f) != FRAME_SIZE:
                raise ValueError(f"scene {scene} frame {i} has {len(f)} bytes")

    neon_scale_tbl, neon_shear_tbl, neon_v_tbls = neon_hdma_tables()

    alloc = BankAllocator(first=2)
    alloc.add("ExtraTiles", extra_tiles, at_bank_start=True)
    alloc.add("NeonScaleTable", neon_scale_tbl, at_bank_start=True)
    alloc.add("NeonShearTable", neon_shear_tbl)
    for i, table in enumerate(neon_v_tbls):
        alloc.add(f"NeonVTable{i}", table)
    bg_labels = []
    frame_table_labels = []
    for scene, bg in enumerate(bg_data):
        label = f"SceneBg{scene}"
        alloc.add(label, b"".join(w.to_bytes(2, "little") for w in bg), kind="dw", at_bank_start=True)
        bg_labels.append(label)
        frames = frame_data[scene]
        if frames is not None:
            ft_label = f"SceneFramePtrs{scene}"
            frame_table_labels.append(ft_label)
            framelabels = []
            for fi, fdata in enumerate(frames):
                flabel = f"Scene{scene}Frame{fi}"
                alloc.add(flabel, fdata, kind="db")
                framelabels.append(flabel)
            # Stash the frame labels on the allocator for later.
            setattr(alloc, f"framelabels{scene}", framelabels)
        else:
            frame_table_labels.append(None)

    # Emit bank includes.
    last_bank = max(alloc.banks)
    for bank, items in sorted(alloc.banks.items()):
        lines = [f"; scene data bank {bank:02d} - auto-generated", ""]
        for label, data, kind in items:
            lines.append(f"{label}:")
            if kind == "dw":
                words = [data[i] | (data[i + 1] << 8) for i in range(0, len(data), 2)]
                lines.append(dw_words(words))
            else:
                lines.append(db_rows(data))
            lines.append("")
        text = "\n".join(lines) + "\n"
        size = sum(len(d) for _, d, _ in items)
        if size > 0x8000:
            raise ValueError(f"bank {bank} overflows: {size}")
        (SRC / f"bank{bank:02d}.inc").write_text(text, encoding="ascii")
        print(f"bank {bank:02d}: {size} bytes, {len(items)} items")

    # Shared include (bank 1).
    sh: list[str] = []
    sh.append("; -----------------------------------------------------------------------------")
    sh.append("; AUTO-GENERATED by generate_scenes.py. Do not edit by hand.")
    sh.append("; -----------------------------------------------------------------------------")
    sh.append("")
    sh.append(f".DEFINE SCENE_COUNT {SCENE_COUNT}")
    sh.append(f".DEFINE FRAME_COUNT {FRAME_COUNT}")
    sh.append(f".DEFINE FRAME_SIZE {FRAME_SIZE}")
    sh.append(f".DEFINE HUD_NAME0 96")
    sh.append(f".DEFINE HUD_NAME_LEN 14")
    sh.append(f".DEFINE HUD_INFO0 110")
    sh.append(f".DEFINE HUD_INFO_LEN 13")
    sh.append(f".DEFINE HUD_STATUS0 123")
    sh.append(f".DEFINE HUD_STATUS_LEN 5")
    sh.append(f".DEFINE EXTRA_FIRST_TILE {EXTRA_FIRST}")
    sh.append(f".DEFINE EXTRA_TILE_COUNT {EXTRA_LAST - EXTRA_FIRST + 1}")
    extra_bytes = (EXTRA_LAST - EXTRA_FIRST + 1) * 32
    sh.append(f".DEFINE EXTRA_TILE_BYTES_LO ${extra_bytes & 0xFF:02X}")
    sh.append(f".DEFINE EXTRA_TILE_BYTES_HI ${extra_bytes >> 8:02X}")
    sh.append(f".DEFINE NEON_PHASES {NEON_PHASES}")
    sh.append("")

    # Selector maps: index = scene * 2 + party
    for sel in range(SCENE_COUNT):
        for party in (False, True):
            idx = sel * 2 + int(party)
            sh.append(f"SelectorMap{idx}:")
            sh.append(db_rows(selector_map(sel, party)))
            sh.append("")

    # Theme palettes
    for t in range(4):
        sh.append(f"ThemeBg{t}:")
        sh.append(db_rows(palette_bytes(themes_bg[t])))
        sh.append("")
        sh.append(f"ThemeObj{t}:")
        sh.append(db_rows(palette_bytes(themes_obj[t])))
        sh.append("")
    sh.append("ThemeBgPtrs:")
    sh.append("  .DW " + ", ".join(f"ThemeBg{t}" for t in range(4)))
    sh.append("ThemeBgBanks:")
    sh.append("  .DB " + ", ".join(f":ThemeBg{t}" for t in range(4)))
    sh.append("ThemeObjPtrs:")
    sh.append("  .DW " + ", ".join(f"ThemeObj{t}" for t in range(4)))
    sh.append("ThemeObjBanks:")
    sh.append("  .DB " + ", ".join(f":ThemeObj{t}" for t in range(4)))
    for t in range(4):
        sh.append(f"ThemeBgNeon{t}:")
        sh.append(db_rows(palette_bytes(themes_neon[t])))
        sh.append("")
    sh.append("ThemeBgNeonPtrs:")
    sh.append("  .DW " + ", ".join(f"ThemeBgNeon{t}" for t in range(4)))
    sh.append("ThemeBgNeonBanks:")
    sh.append("  .DB " + ", ".join(f":ThemeBgNeon{t}" for t in range(4)))
    sh.append("")
    sh.append("NeonVTablePtrs:")
    for i in range(NEON_PHASES):
        sh.append("  " + ptr_bytes(f"NeonVTable{i}"))
    sh.append("")

    # Scene names: length byte followed by 15 tile bytes (max 14 chars used)
    sh.append("SceneNameTable:")
    for name in SCENE_NAMES:
        vals = [len(name)] + [ord(c) - 32 for c in name]
        vals += [0] * (16 - len(vals))
        sh.append("  .DB " + ", ".join(f"${v:02X}" for v in vals))
    sh.append("")

    # Scene descriptors, 16 bytes each.
    # 0-2 bg ptr, 3-5 frame ptr table, 6 frame count, 7 scroll rate,
    # 8 flags, 9-10 mode7 scale, 11 must be zero, 12-13 bg bytes, 14-15 name ptr
    sh.append("SceneDesc:")
    for scene in range(SCENE_COUNT):
        if scene == 4:
            sh.append("  " + ptr_bytes(bg_labels[4]))
            sh.append("  .DB $00, $00, $00")
            sh.append("  .DB $00, $00, $01, $58, $00, $00")
            sh.append(f"  .DW ${len(bg_data[4]) * 2:04X}")
            sh.append(f"  .DW SceneNameTable+{scene * 16}")
        else:
            frame_count = NEON_FRAMES if scene == 5 else FRAME_COUNT
            scroll = 188 if scene == 2 else 0
            flags = 0x02 if scene == 2 else (0x04 if scene == 5 else 0)
            scale = 80 if scene == 2 else 88
            bg_bytes = len(bg_data[scene]) * 2
            sh.append("  " + ptr_bytes(bg_labels[scene]))
            label = frame_table_labels[scene]
            sh.append("  " + ptr_bytes(label))
            sh.append(f"  .DB ${frame_count:02X}, ${scroll:02X}, ${flags:02X}, ${scale:02X}, $00, $00")
            sh.append(f"  .DW ${bg_bytes & 0xFFFF:04X}")
            sh.append(f"  .DW SceneNameTable+{scene * 16}")
    sh.append("")

    # Frame pointer tables (3 bytes per frame).
    for scene in range(SCENE_COUNT):
        if frame_data[scene] is None:
            continue
        labels = getattr(alloc, f"framelabels{scene}")
        sh.append(f"SceneFramePtrs{scene}:")
        for label in labels:
            sh.append("  " + ptr_bytes(label))
        sh.append("")

    # HDMA table for Vector City: one 2-byte M7VOFS value per scanline.
    sh.append("CityHdmaTable:")
    for i in range(224):
        off = int(round(2.5 * math.sin(2.0 * math.pi * i / 56.0))) & 0xFFFF
        sh.append(f"  .DB $01, ${off & 0xFF:02X}, ${off >> 8:02X}")
    sh.append("  .DB $00")
    sh.append("")

    # City scroll bob table (0..7)
    sh.append("CityBob:")
    bob = [int(round(3.5 + 3.0 * math.sin(2 * math.pi * f / FRAME_COUNT))) for f in range(FRAME_COUNT)]
    sh.append("  .DB " + ", ".join(str(max(0, min(7, b))) for b in bob))
    sh.append("")

    (SRC / "scenes_shared.inc").write_text("\n".join(sh) + "\n", encoding="ascii")
    shared_size = sum(len(x) for x in [])  # textual; binary size checked by WLA
    print(f"scenes_shared.inc written ({len(sh)} lines)")

    # Bank glue.
    glue = [f"; auto-generated bank layout ({last_bank} banks of scene data)", ""]
    glue.append(".BANK 1 SLOT 0")
    glue.append(".ORGA $8000")
    glue.append('.INCLUDE "scenes_shared.inc"')
    glue.append("")
    for bank in range(2, last_bank + 1):
        glue.append(f".BANK {bank} SLOT 0")
        glue.append(".ORGA $8000")
        glue.append(f'.INCLUDE "bank{bank:02d}.inc"')
        glue.append("")
    (SRC / "scene_banks.inc").write_text("\n".join(glue), encoding="ascii")
    print(f"scene_banks.inc: banks 2..{last_bank}")


if __name__ == "__main__":
    main()



