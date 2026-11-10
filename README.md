# Neon Scenes

A SNES cartridge demo for real hardware: six generative sci-fi scenes, a
scene selector, smooth fade transitions and a hands-off party mode.  The
original Lissajous comet is still here, joined by a wireframe Holo Planet, a
Pulse Analyzer, a neon Vector City, a Bohr-style Atomic scene and a synthwave
Neon City.

![Scene selector](screenshots/title.png)
![Holo Planet](screenshots/scene-holo.png)
![Pulse Analyzer](screenshots/scene-pulse.png)
![Vector City](screenshots/scene-city.png)
![Atomic](screenshots/scene-atomic.png)
![Neon City](screenshots/scene-neon.png)
![Lissajous](screenshots/scene-lissajous.png)
![Party mode](screenshots/party.png)

## Play

- **ROM:** `NeonScenes.sfc` (512 KiB, LoROM, NTSC)
- **Tested:** Snes9x 1.63 and SUPER ZSNES 0.320b; the ROM uses standard
  LoROM/Mode 7/OAM/HDMA features and is intended to run on real hardware and
  accurate emulators as well.
- **Hardware target:** LoROM, 512 KiB, NTSC, no expansion chip.  Intended for
  SNES flash carts (FXPAK Pro, EverDrive, etc.) and real NTSC consoles.
- **Startup:** the reset handler disables NMI/HDMA, clears the low 8 KiB of
  WRAM, and waits for two vblanks before touching the PPU.  This avoids the
  intermittent black screen seen when a flash cart hands over with stale
  registers or when the PPU is still warming up.

Load the `.sfc` and press **START**.

### Scene selector

| Input | Action |
| --- | --- |
| Up / Down | Choose a scene |
| Left / Right | Toggle party mode |
| Select | Toggle party mode |
| Start | Launch the selected scene |

The selector remembers the last scene and the party-mode setting when you
return to it with **Select** during a scene.

### During a scene

| Input | Action |
| --- | --- |
| L / R | Previous / next scene (fades through black) |
| Start | Toggle party mode |
| Select | Return to the scene selector |
| A | Blackout on / off (smooth fade) |
| B | Pause / resume |
| X | Cycle the four colour themes |
| Y | Show / hide the scene-name HUD |
| Up / Down | Brightness (party mode, and all non-Lissajous scenes) |
| Left / Right | Lissajous: frequency A |
| Up / Down | Lissajous: frequency B |

Party mode auto-cycles through the six scenes every ten seconds, advances the
colour theme on each cycle, and shows the scene name in gold.  Brightness and
blackout are available everywhere; the scene-name HUD can be hidden with **Y**.

## Scenes

- **Holo Planet** — a rotating wireframe sphere with latitude rings, a tilted
  planetary ring, two orbiting moons and a white core glow.
- **Pulse Analyzer** — ten spectrum bars with peak-hold markers, a live
  waveform, a BPM pulse ring and a perspective-style grid.
- **Vector City** — a neon skyline in Mode 7 with parallel scrolling, flying
  cars, a moon, perspective ground lines and a per-scanline HDMA wave.
- **Atomic** — three tilted electron orbits, glowing electrons and trails, a
  three-part nucleus and an energy ring.
- **Lissajous** — the original 96-sprite comet trail, now on a precomputed
  Mode 7 oscilloscope grid.
- **Neon City** — a synthwave outrun scene rebuilt around
  `References/NeonCityConcept.jpg`: a striped sunset over a dense, silhouetted
  skyline and a Mode 7 floor whose grid converges on the vanishing point and
  drives towards the camera, with a rear-view sports car on the road.

## Build

Requirements:

- Python 3.9+
- WLA-DX 10.7 (`wla-65816` and `wlalink`)

The bundled build expects the Windows WLA-DX binaries in
`tools/wla/wla_dx_v10.7_Win64/`.  If they are missing, download WLA-DX v10.7
from <https://github.com/vhelin/wla-dx/releases> and extract the Windows
archive there.

```text
python build.py
```

The script regenerates `src/generated.inc`, `src/scenes_shared.inc` and the
per-bank scene includes, assembles the ROM, links it, checks the size, reset
vector and checksum pair, and writes `NeonScenes.sfc`.

The assembler is invoked with `-h` (16-bit label references by default); the
source explicitly marks 8-bit immediates with `.B` where needed.

## Files

```text
NeonScenes.sfc     final ROM (512 KiB)
NeonScenes.sym     WLA symbol map for debugging
build.py                  one-command build + ROM validation
generate_assets.py        fonts, palettes, Lissajous frequency tables, tilemaps
generate_scenes.py        scene art, OAM frames, themes, selector maps, HDMA
src/main.asm              65816 source
src/generated.inc         generated shared data (checked in for convenience)
src/scenes_shared.inc     generated scene metadata for bank 1
src/bankNN.inc            generated scene backgrounds and OAM frames
src/scene_banks.inc       bank/include glue for the scene data
screenshots/              native 256x224 captures
tools/wla/                WLA-DX 10.7 binaries used by build.py
```

## Architecture

- **Banks.** Bank 0 holds the 65816 code and the original Lissajous tables.
  Bank 1 holds shared scene metadata, selector maps, theme palettes, sprite
  tiles, texture descriptors and the Vector City HDMA table.  Banks 2–15 hold
  the precomputed Mode 7 backgrounds, OAM frames, the extra sprite tiles and
  the Neon City scanline tables.  The ROM header is in bank 0 at `$FFC0`.
- **Scene engine.** Every scene is described by a 16-byte descriptor: Mode 7
  background pointer and size, OAM-frame table pointer and count, scroll
  parameters, flags, scale and HUD name.  `StartScene` loads the descriptor,
  uploads the background and palettes, sets the Mode 7 matrix and starts the
  appropriate update path.  Flags are `$01` Lissajous real-time trail, `$02`
  Vector City scroll and `$04` Neon City perspective floor.
- **OAM frames.** The five new scenes stream precomputed frames of 96 sprites
  each from ROM (384 bytes of OAM entries + 24 bytes of OAM high-table bits per
  frame).  This keeps the 65816 main loop at 60 Hz and makes the animation
  deterministic.  Slots 0–95 are the scene particles; slots 96–127 are the HUD.
  Neon City needs a single frame: the car is static and all of the motion comes
  from the Mode 7 floor.
- **VRAM.** Mode 7 backgrounds occupy VRAM word 0 onward (14,080 bytes for the
  88×77 scenes, 28,160 bytes for the 176×77 Vector City).  Neon City uploads
  the entire 32 KiB Mode 7 plane: the top-left corner holds a 176-texel-wide
  skyline and the rest is one seamless 64×32-texel grid/road cell.  Sprite
  tiles start at word `$4000` (byte `$8000`): the 4bpp font and original dot
  tiles, followed by scene tiles at word `$4430` (now including the car in
  tiles 144–201).
- **HDMA.** Vector City uses channel 4 to write a gentle per-scanline `M7VOFS`
  wave.  Neon City uses channels 1–3, one 16-bit write per scanline each:
  `M7A` (perspective scale), `M7B` (the shear that puts the vanishing point on
  the screen centre) and `M7D` (the depth scale, so `texel_y = y·M7D/256`).
  Above the horizon the same tables hold the skyline at its native width; below
  it they implement a real 1/(depth) floor.  `M7D` comes from 32 precomputed
  tables and the main loop only swaps the HDMA source pointer, so a step costs
  three register writes.  The plane band the floor samples is periodic, which
  makes the wrap at the end of each table invisible.
- **Colour.** Four themes (NEON, SOLAR, AURORA, MONO) are precomputed for the
  background and OBJ palettes.  Party mode advances the theme on each scene
  change; **X** cycles it manually.  Neon City has its own 32-colour background
  palette (deep indigo sky, orange/pink sun, cyan grid, magenta road lines) and
  object palette 4 is a dedicated red ramp so the car can be shaded.
- **Safety.** VRAM/CGRAM updates run with NMI off and forced blank.  During
  gameplay only OAM is updated, by a 544-byte DMA inside the vblank NMI.
  Precomputed OAM frames are copied into the OAM shadow with two small DMAs
  (entries and high table) before the OAM DMA.

## Header / checksum

```text
Title:      NEON SCENES
Mapper:     LoROM (slow ROM)
Cart type:  ROM only ($00)
ROM size:   512 KiB (header value $09)
Region:     USA / NTSC ($01)
Checksum:   $D3A2 / complement $2C5D
SHA-256:    d5f12d7aceec21da291a9a3a746eeeb1925210e9c858b8bf4019d77bf53adb25
```

The checksum is recomputed after linking by `build.py` with the standard
SNES algorithm (the four checksum bytes themselves are excluded).  WLA-DX's
own value includes those bytes, which made some flash-cart tools disagree.

## Notes

- Snes9x 1.63 verification: all six scenes, the selector and the title screen
  were checked with native 256x224 captures.
- This is a 60 Hz NTSC release.  On a PAL console the picture will still run,
  but at 50 Hz and with PAL borders.
- A genuine original cartridge needs the CIC lockout chip and a compatible
  board; a flash cart is the simplest way to run it on real hardware.
- The demo is silent by design; no SPC700 sound driver is included.
- The comet trail is intentionally made of discrete embers rather than a
  solid polygon.  That keeps the effect within the SNES sprite limits and
  makes the fast-sweep persistence work nicely on a CRT.
- The Neon City floor is a real perspective projection, not a scrolling
  picture: `M7A`, `M7B` and `M7D` are rewritten per scanline so the grid
  converges on a vanishing point hidden behind the skyline, and stepping the
  `M7D` tables makes the cells rush towards the viewer at the correct
  accelerating rate.  The car is the only sprite in the scene, so one OAM frame
  is enough and the whole frame budget goes into the floor.
- The scene-name HUD is deliberately tiny: it is the only sprite text drawn
  during a scene, and it can be hidden completely with **Y**.

## References

- [WLA-DX](https://github.com/vhelin/wla-dx) — assembler/linker used here.
- [fullsnes / nocash SNES specifications](https://problemkaputt.de/fullsnes.htm) —
  Mode 7, OAM, DMA, HDMA and CGRAM details.
- [Super Famicom Development Wiki: Backgrounds](https://wiki.superfamicom.org/backgrounds) —
  Mode 7 VRAM/map layout.

