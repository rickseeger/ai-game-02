# City Walkthrough — Technical Design Document

Tree: G8 · Node 1 · Strategy resolution
Version: 1.0 · Date: 2026-09-13 · Author: the gardener <root@g.seeger.net>
Status: APPROVED baseline. This document resolves every open strategy decision.
Implementation nodes read this file and begin coding with no further design choices.

---

## 0. Purpose and scope

This document is the single source of truth for the game's architecture. It names the
renderer technique, the full-screen color-ASCII output approach, the module/data layout,
the tech stack, and the cross-platform build/test/package plan, plus the concrete game
design (night-cityscape centerpiece, light survival loop, primary mission) that the
architecture must support.

Explicit v1 non-goals: audio/music, combat, day/night cycle, save-file encryption,
online play, localization, mobile/touch, and non-ASCII (CJK/emoji) glyphs in the renderer.

---

## 1. Decisions at a glance (no open strategy remains)

| Strategic question | Decision | Section |
|---|---|---|
| 3D-to-ASCII renderer technique | 2D-DDA grid raycasting, extended to 2.5D (per-cell wall height + floor elevation); NO SDF raymarching | 2 |
| Full-screen output approach | Truecolor cell buffer with 256-color fallback; RLE single-write flush | 3 |
| Windows terminal compatibility | ctypes VT enablement + WT_SESSION truecolor detect + 256-color conhost fallback | 3.4 |
| Tech stack | Python 3.10+ standard library only, zero third-party dependencies | 4 |
| Module layout | `citywalk/` package: engine / renderer / world / ui split | 5 |
| World representation | 2D integer grid + type table; procedural generator; JSON save | 5.3, 5.5 |
| Linux build/package | source + launcher; optional wheel (no deps) | 6.1 |
| Windows build/package | source + run.bat; optional PyInstaller onefile exe | 6.2 |
| Testing | stdlib unittest + headless framebuffer smoke test + CI matrix | 6.3 |
| Survival | slow hunger/thirst 0..100, eat/drink at vendors, non-dominant | 7.2 |
| Primary mission | "Find Maya at the Harbor Hotel rooftop garden" + wayfinding | 7.3 |

---

## 2. Renderer technique

### 2.1 Chosen technique

Grid-based DDA raycasting (the Wolfenstein-3D / Lodev technique), extended to 2.5D:

- The world is a 2D grid of cells. Each cell carries a type, a wall height
  (0 = open, 1..N = floors), and a floor elevation (z, default 0).
- For each screen column, cast one ray from the camera through the screen plane using
  the integer DDA algorithm (fast, exact, no epsilon issues). The first non-empty cell
  hit yields that column's wall sample.
- Perpendicular distance gives the wall's projected height; wall strips are drawn from
  the cell's base elevation up to `floor_z + height`, scaled by perspective.
- Floor and ceiling are drawn by floorcasting: for each row, invert the projection to
  recover the world point, sample the floor/elevation map, and shade it. Rows above the
  horizon (and above all walls) sample the night-sky gradient.
- Emissive night lighting: light sources (street lamps, neon signs, lit windows, moon)
  contribute additive glow that is NOT attenuated by distance fog — producing the
  "city lit up at night" look.

Why not SDF raymarching: the city is rectilinear (buildings, streets, plazas). Grid
raycasting is the minimal, correct, fastest match, and at ASCII cell resolution the extra
geometric flexibility of SDF is invisible. SDF also costs more per-pixel in pure Python,
hurting the frame budget. Decided: no raymarching in v1. A future node wanting curved
architecture would add a per-feature SDF then, not now.

Why not a full polygon rasterizer: the scene has no free-form meshes, and per-column
raycasting integrates naturally with the per-column ASCII cell buffer.

### 2.2 Camera and projection

- World units: 1.0 = one grid cell = one meter.
- Camera: continuous position (x, y), facing angle theta, plus a small clamped vertical
  look offset for the horizon.
- Horizontal FOV: 66 degrees. Projection-plane distance `d = (W/2) / tan(FOV/2)`.
- Screen columns 0..W-1 map to ray angles theta ± FOV/2; rows 0..H-1 map to vertical
  angles via the same projection with eye height = 0.5 cell above the floor elevation.

### 2.3 Per-column DDA (concrete algorithm)

Reference: Lode Vandevenne, "Lode's Computer Graphics Tutorial — Raycasting"
(lodev.org/raycasting). Implemented verbatim in integer math:

```
cameraX   = 2*x/W - 1
rayDirX   = dirX + planeX*cameraX
rayDirY   = dirY + planeY*cameraX
mapX,mapY = int(posX), int(posY)
deltaDistX = abs(1/rayDirX) if rayDirX else INF    # likewise deltaDistY
if rayDirX < 0: stepX=-1; sideDistX=(posX-mapX)*deltaDistX
else:           stepX=+1; sideDistX=(mapX+1-posX)*deltaDistX
# (same pattern for Y)
loop: step to the next grid line; on the first non-empty cell, break with
      side (0=x-face, 1=y-face) and the hit mapX/mapY.
perpWallDist = (sideDistX-deltaDistX) if side==0 else (sideDistY-deltaDistY)
lineHeight   = int(H / perpWallDist)      # projected wall height in rows
```

DDA terminates by a maximum step bound (512 cells) to guard against rays that never hit
a wall (open sky) — those columns fall through to floor/ceiling/sky casting.

### 2.4 Wall, window, and sign sampling

- On hit, look up the cell's type-table entry: material id, base color ramp, glyph set,
  emissive map.
- For each row inside the wall strip, compute the fractional face coordinate u and the
  fractional vertical position v (0..1 across the strip):
  - x-face: `u = frac(posY + perpWallDist*rayDirY)`; y-face: `u = frac(posX + perpWallDist*rayDirX)`.
  - v maps the row to the building's vertical span.
- Window grid: each building type has a window pattern (window width, sill spacing, lit
  fraction). A row is a "window" when (u,v) falls in a window cell. Lit windows are chosen
  deterministically from a per-building seed; a lit window renders an emissive warm glyph
  (e.g. 'o' or the block '■') in a warm fg color over the darker facade bg.
- Signs/neon: facade cells flagged by the cell data (restaurant/bar fronts) render letter
  glyphs in a saturated neon fg color with a glow halo (a few brighter bg cells around them).

### 2.5 Floor / ceiling and sky casting

Standard floorcasting (Lodev floorcasting chapter), with elevation. Eye height = 0.5:

```
for each row y below horizon:
  rowDistance = (0.5 * H) / (y - horizon)
  for each column x (stepped by 2):
    worldX, worldY = inverse-project(x, y, rowDistance)
    cell = grid[worldX][worldY]; base = cell.floor_elevation
    color = floor material sampled at frac(worldX, worldY), lit by light pools + fog
```

- Sky: rows above the horizon sample a vertical night gradient (deep navy -> near-black at
  zenith), plus a fixed moon and a small deterministic star field. Moon/stars are emissive.
- Because floor/sky casting is O(W x H) in pure Python, it is rendered at HALF horizontal
  resolution (2-column step) and reused — an explicit, non-negotiable optimization to hold
  30 fps. Wall columns are always full resolution.

### 2.6 Lighting model (night, emissive)

- Base scene is dark: every surface is rendered at its pre-darkened night albedo.
- Distance fog: `color = lerp(surface, fogColor, min(1, dist/fogDist))`; fogColor =
  RGB (8,10,24), fogDist = 24 cells.
- Light pools: each light source has position, radius, color, falloff. When a sample point
  is within radius, add `glow = color * (1 - d/radius)^2 * intensity`. Cells are pre-tagged
  with the lights that reach them at load time, so the inner loop is O(1) per sample.
- Emissive surfaces (lit windows, signs, lamps, moon) are added at full brightness AFTER
  fog so they cut through the dark.

### 2.7 ASCII sampling and the cell buffer

The renderer never writes to the terminal. It fills a W x H framebuffer; a separate flush
step serializes the buffer to one ANSI string (Section 3).

Each cell's shading pass produces a final (surfaceRGB, materialID, luminance, emissive?):

- bg color = surfaceRGB (post-lighting).
- glyph:
  - emissive detail present -> the detail glyph, fg = emissive color.
  - else material has a texture glyph set -> a glyph from that set, indexed by (u,v hash +
    luminance), fg = surfaceRGB brightened slightly.
  - else -> luminance-ramp glyph, fg = surfaceRGB brightened.

Result: a genuine color-ASCII image — color carries palette/lighting, glyphs carry texture
and luminance, preserving the ASCII aesthetic without losing atmosphere.

---

## 3. Full-screen color-ASCII output

### 3.1 Cell buffer and frame flush

- Framebuffer: W x H cells, each = (glyph 1-char, fg RGB, bg RGB). Stored as three flat
  structures for speed: glyphs as a bytearray, fg/bg as `array('B')`.
- Each frame, after the render pass, the flusher:
  1. Builds ONE string: cursor home (`\x1b[H`) + per-cell escape codes, run-length
     encoding consecutive cells that share the same fg/bg to minimize escape sequences.
  2. Writes the whole string in a single `os.write(1, ...)` (POSIX) / buffered
     `sys.stdout.write` + flush (Windows) to avoid tearing.
- Hide cursor on start (`\x1b[?25l`), restore on exit. Enter alternate screen
  (`\x1b[?1049h`) where supported; on legacy Windows conhost, clear-screen + home instead.
- Target 30 fps (33 ms/frame). If profiling shows the flush string is the bottleneck, the
  RLE color-run encoding (already specified) is tightened — resolution is not reduced.

### 3.2 Color: truecolor primary, 256-color fallback

- Preferred: 24-bit truecolor `\x1b[38;2;R;G;Bm` / `\x1b[48;2;R;G;Bm`.
- Fallback: 256-color. All palette colors are defined in 24-bit and quantized ONCE at
  startup into the 256-color cube (6x6x6 = 216) plus 16 base colors and a 24-step
  grayscale — a fixed 256-entry LUT. The flusher emits `\x1b[38;5;Nm` / `\x1b[48;5;Nm`
  using the LUT index.
- Capability detection order:
  1. `COLORTERM` contains `truecolor` or `24bit` -> truecolor.
  2. `WT_SESSION` set (Windows Terminal) -> truecolor.
  3. `TERM` contains `256color` (or `xterm-256color`, `screen-256color`) -> 256-color.
  4. otherwise -> 256-color fallback (once VT is on), or 16-color as documented degraded mode.
- The renderer always works in 24-bit internally; the flusher downgrades at the boundary,
  so the code is color-depth agnostic.

### 3.3 Resolution detection

- Linux: `shutil.get_terminal_size()` (TIOCGWINSZ); re-query on SIGWINCH via a handler that
  sets a resize flag.
- Windows: `shutil.get_terminal_size()` (GetConsoleScreenBufferInfo); poll each frame (cheap).
- Minimum supported: 80x24 (runs, just narrow). Target: ~200x50. W and H adapt each frame;
  no hardcoded resolution.

### 3.4 Windows terminal compatibility (concrete)

- On startup (Windows backend only), enable VT processing via ctypes:
  - `kernel32.GetStdHandle(-11)` (STD_OUTPUT_HANDLE) and `-10` (STD_INPUT_HANDLE).
  - `GetConsoleMode` -> `SetConsoleMode(mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)
    | ENABLE_PROCESSED_OUTPUT (0x0001))`.
  - Input: `SetConsoleMode(mode | ENABLE_WINDOW_INPUT (0x0008))`; poll keys with
    `msvcrt.kbhit()` + `msvcrt.getwch()`.
- Legacy conhost: after enabling VT, default to 256-color (conhost truecolor is historically
  unreliable); Windows Terminal (`WT_SESSION` set) uses truecolor.
- Recommended host: Windows 11 / Windows Terminal. Legacy conhost remains fully playable at
  256-color.
- Code points: renderer glyphs are restricted to ASCII (0x20-0x7E) plus block/shade
  (U+2580-U+259F) and box-drawing (U+2500-U+257F) — all single-width in VT, so cell-width
  assumptions hold on both OSes. No emoji, no wide CJK in the renderer.

### 3.5 Input

- Non-blocking polling loop in raw mode:
  - Linux: `termios.tcgetattr`/`tcsetattr` (raw, no echo) + `tty.setraw`; poll stdin with
    `select.select` (0 timeout).
  - Windows: `msvcrt.kbhit()` + `msvcrt.getwch()`.
- Key map (v1): W/Up forward, S/Down back, A/Left strafe-left, D/Right strafe-right,
  Q/E turn-left/right, Arrow keys turn (when not strafing), Enter/E interact, I inventory,
  M map, Esc menu/pause, Ctrl-C quit. (WASD move/strafe, arrows turn; Q/E turn — see 7.4.)
- All keys pass through a platform-neutral `KeyEvent` abstraction; the engine never touches
  platform APIs.

---

## 4. Tech stack

- Language/runtime: Python 3.10+ (3.14 tested in dev). Standard library ONLY. Zero
  third-party dependencies.
- Why Python: one codebase for Linux and Windows; no compilation; the renderer is integer
  arithmetic, well within budget at W~200 x H~50; fastest path from a clean checkout (both
  OSes ship a Python interpreter).
- Why zero deps: "clean checkout" means `git clone` then run — no pip, no wheels, no C
  extensions. The stdlib covers terminal I/O (termios, msvcrt, ctypes, os, sys, shutil,
  select), math (math), data (array, json, random, struct), and testing (unittest).
- Optional build-time-only (never runtime): PyInstaller for a standalone Windows .exe and a
  self-contained Linux binary (Section 6).
- Python version floor: 3.10 (for `X | Y` hints and `match`); avoid 3.12+ only features so
  Windows Python 3.10/3.11 installs keep working.

---

## 5. Module and data architecture

### 5.1 Directory layout (final)

```
ai-game-02/
  DESIGN.md                (this document)
  README.md                (run instructions per OS)
  LICENSE                  (MIT)
  .gitignore
  pyproject.toml           (optional packaging; no deps)
  run.py                   (thin launcher)
  run.sh                   (Linux launcher)
  run.bat                  (Windows launcher)
  citywalk/
    __init__.py
    __main__.py            (entry point: arg parsing, boot, main loop)
    config.py              (all tunables in one place; defaults)
    engine/
      __init__.py
      clock.py             (fixed-timestep loop, fps cap)
      terminal.py          (platform abstraction: raw mode, size, colors, keys)
      framebuffer.py       (cell buffer + RLE flush)
    renderer/
      __init__.py
      camera.py            (pos/dir/plane, FOV)
      dda.py               (per-column DDA, pure integer)
      walls.py             (wall/window/sign sampling)
      floorcast.py         (floor + ceiling + sky + stars/moon)
      lighting.py          (distance fog, light pools, emissive add)
      palette.py           (color ramps, 256 LUT, glyph ramps)
      renderer.py          (orchestrates per-frame framebuffer fill)
    world/
      __init__.py
      grid.py              (grid world + type table)
      gen.py               (procedural city generator, seeded)
      entities.py          (player, NPCs, vendors, doors)
      interact.py          (interaction system)
      survival.py          (hunger/thirst state + decay + replenish)
      quests.py            (mission definitions + progression)
      save.py              (JSON save/load)
    ui/
      __init__.py
      hud.py               (status bar: hunger/thirst/mission/time)
      text.py              (message log, dialogs, menus)
    assets/
      glyphsets.py         (material glyph sets + luminance ramp)
      palettes.py          (named color palettes: night, neon, lamp, ...)
  tests/
    test_dda.py  test_grid.py  test_floorcast.py  test_lighting.py
    test_survival.py  test_quests.py  test_save.py
    test_framebuffer.py  test_palette.py
  .github/workflows/ci.yml
```

### 5.2 Module responsibilities

- `engine.terminal` — the ONLY module that imports platform-specific APIs (termios/tty on
  POSIX; msvcrt/ctypes on Windows). Exposes `init()`, `teardown()`, `get_size()`,
  `color_mode()`, `poll_keys() -> list[KeyEvent]`, `flush(string)`. Everything else is
  platform-neutral.
- `engine.framebuffer` — holds the W x H cell arrays; `set(x,y,glyph,fg,bg)`;
  `to_ansi(color_mode) -> str` with color RLE; `clear()`.
- `renderer.renderer` — owns the camera and calls dda -> walls -> floorcast -> lighting ->
  framebuffer, in that order.
- `world.grid` — `Cell = (type_id, height, floor_z, seed)`; grid stored as a flat
  `array('H')` of type ids plus three parallel flat arrays (height, floor_z, seed). A type
  table maps type_id -> material/behavior. Neighbor and line-of-sight ops are pure functions.
- `world.gen` — deterministic procedural city (Section 5.5) from a seed.
- `world.survival` — pure state + `tick(dt)` + `eat()`/`drink()`; emits events the UI reads.
  No rendering.
- `world.quests` — declarative quest definitions (Python dicts) + a small progression state
  machine (stages, objectives, completion).
- `ui.hud` — renders the 1-line status bar into reserved screen row 0; the 3D view occupies
  rows 1..H-1. The HUD does not share the 3D framebuffer but is merged at flush time.

### 5.3 Data formats

- World grid (runtime): flat `array('H')` type ids + parallel arrays; compact and fast.
- Save file (`saves/save.json`): player pos/angle, hunger, thirst, health, clock time,
  quest stage, inventory, RNG seed, visited flags. JSON, human-readable, versioned with
  `schema_version`.
- Config (`config.py`): every tunable (FOV, fog distance, decay rates, light radii, palette
  names, key bindings) as module constants with comments. config.py IS the config in v1.
- Quest/mission definitions: Python dicts in `quests.py` (not JSON) so they can reference
  code hooks; documented schema.
- Palettes (`assets/palettes.py`): named dicts of RGB triples — the single source for all
  color, so art direction is changeable in one place.

### 5.4 Glyph sets and palettes (concrete)

Luminance ramp (dark -> bright), ASCII only, for shaded surfaces:

```
ramp = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
```

Map luminance in [0,1] -> `index = round(lum * (len(ramp)-1))` (0 = darkest ' ', highest
= brightest '$'). This mapping is fixed and documented.

Emissive/detail glyphs (allowed set: ASCII 0x20-0x7E plus block/shade U+2580-U+259F and
box-drawing U+2500-U+257F):

- lit window: 'o' or '■'. Neon sign: the sign's text glyphs (e.g. 'B','A','R') in neon fg.
- street lamp head: '*'. Moon: 'o' (bright white). Star: '.'.

Palettes (24-bit RGB, named and fixed — implementation may ADD entries, not rename):

```
night_fog (8,10,24)     sky_zenith (2,3,12)    sky_horizon (16,20,48)
moon (230,232,240)      lamp_warm (255,196,120)  lamp_pool (255,180,90)
neon_red (255,64,90)    neon_cyan (64,220,255)   neon_pink (255,80,200)
neon_green (80,255,140) neon_yellow (255,220,80)
window_warm (255,200,120)  window_cool (150,200,255)
brick (70,50,48)   concrete (60,62,70)   glass (40,60,80)
steel (50,55,65)   wood (60,44,30)
asphalt (28,30,36)  sidewalk (50,52,58)  cobble (45,42,50)  grass (18,42,24)
awning_red (150,40,40)  awning_green (40,120,60)  table (70,50,30)  chair (60,48,34)
hud_fg (200,210,220)  hud_warn (255,120,60)  hud_danger (255,60,60)
```

### 5.5 Procedural city generator (concrete algorithm)

- Seeded RNG (`random.Random(seed)`), fully deterministic (byte-identical cross-platform).
- Grid size: default 96x96 cells (tunable).
- Street grid: block size 12-18 cells; Manhattan grid of 2-cell-wide streets with 1-cell
  sidewalks on each side.
- Zoning per block: downtown (6-12 floors), midtown (3-6), residential (1-3), industrial
  (1-2), park (0 floors, trees as low non-wall decor), waterfront (edge blocks with water
  cells), plaza (open, fountain/decor).
- Buildings: within a block, subdivide into lots; each lot gets a building with a per-lot
  seed -> height, material, window pattern, lit-window fraction, optional sign text for
  commercial streets.
- Commercial corridors: streets adjacent to midtown/downtown get restaurants and vendors at
  fixed intervals; each has sidewalk tables/chairs, an awning, and a sign. These are the
  eat/drink interactables.
- Street lamps: on sidewalk corners and every N cells along streets; each is a light source
  with a warm pool radius ~2.5 cells.
- Landmarks: the Harbor Hotel (a tall distinctive building near the waterfront) with a
  rooftop garden (marked interactable), plus signposts naming districts.
- Player spawn: a plaza near the center, facing a lit street.
- The generator is the only world producer in v1. If a node wants a hand-tuned map, it edits
  gen.py parameters/seed, not a separate map file.

---

## 6. Build, test, and package plan

### 6.1 Linux

- Run: `python3 run.py` (or `./run.sh`). No build step (pure Python). Requires Python 3.10+.
- Terminal: works in any VT-capable terminal (gnome-terminal, kitty, alacritty, wezterm,
  xterm-256color, tmux). truecolor if `COLORTERM` advertises it.
- Package (optional): `python -m build` produces a wheel/sdist via `pyproject.toml`
  (setuptools backend, no dependencies); installing yields a `citywalk` console entry point.
  Not required to run the game.
- Standalone (optional): PyInstaller `--onefile` on Linux to produce a self-contained
  `citywalk` binary (build-time-only dependency).

### 6.2 Windows

- Run: double-click `run.bat` (which runs `python run.py`) or `python run.py`. Requires
  Python 3.10+ in PATH.
- Recommended host: Windows Terminal (truecolor, alt-screen, full key support). Legacy
  conhost is supported at 256-color via the ctypes VT-enable path (Section 3.4).
- Package (the shipped artifact for Andrew): PyInstaller `--onefile --console` to produce
  `citywalk.exe` (no Python needed on the target machine). Build command (documented in
  README): `pyinstaller --onefile --name citywalk run.py`. Build-time-only dependency, run
  on a Windows machine or CI.
- CI (optional but recommended): GitHub Actions `windows-latest` builds the exe and uploads
  it as a release asset; `ubuntu-latest` runs tests + a Linux package.

### 6.3 Testing

- Framework: stdlib `unittest` (no pytest) -> `python -m unittest discover -s tests` works
  identically on both OSes.
- Unit tests (pure, no terminal):
  - `test_dda.py`: ray hits correct cell/side for known maps; perpendicular distance correct;
    DDA terminates on open sky (step bound).
  - `test_grid.py`: grid indexing, neighbors, type-table lookup, save/load round-trip.
  - `test_floorcast.py`: inverse projection maps rows/cols to expected world coords.
  - `test_lighting.py`: fog lerp at distance, light-pool falloff, emissive add order.
  - `test_survival.py`: decay-rate math, eat/drink clamp to [0,100], low-level warnings,
    health drain.
  - `test_quests.py`: stage transitions, objective completion, mission-complete flag.
  - `test_palette.py` / `test_glyphsets.py`: palettes are valid RGB triples; ramp monotonic;
    glyphs single-width; 256 LUT covers the full range.
- Headless smoke test (the key CI test): `test_framebuffer.py` runs the full renderer for 60
  frames against a `StringIO`-backed terminal stub (no real TTY) and asserts the framebuffer
  is W x H, every cell has a 1-char glyph and valid RGB, and the generated ANSI string is
  non-empty and well-formed. This proves the game boots and renders on a clean checkout in CI.
- Determinism test: the city generator produces byte-identical grids for the same seed on
  Linux and Windows (guards against RNG/platform drift).
- CI (`.github/workflows/ci.yml`): matrix `ubuntu-latest` + `windows-latest`; steps: checkout,
  `python -m unittest discover`, smoke test, (Windows) PyInstaller build.

---

## 7. Game design (what the architecture must support)

### 7.1 Centerpiece — the night cityscape

The pleasure is walking and looking. The renderer/design already commit to:

- A lively night city: warm pools of streetlight, lit windows, neon signs, a moon and stars,
  distance fog that makes distant blocks glow.
- Atmospheric details (all supported by the renderer): restaurant tables/chairs on sidewalks,
  awnings, neon storefronts, park trees, a waterfront with moonlight on water.
- Movement is smooth (30 fps, continuous position/angle), and looking around (turn plus
  optional vertical look) is itself satisfying.
- The city feels alive without combat: the light, the district variation, and the sense of
  "there is a lit restaurant over there" invite exploration.

### 7.2 Light survival loop (non-dominant)

- Hunger and thirst are 0-100 (100 = full). Decay: 1 point per 60 real seconds (a full bar
  lasts 100 minutes). Intentionally slow — it provides pacing, not pressure.
- Replenish: interacting with a restaurant/vendor opens a simple menu: "eat a meal" (+35
  hunger, costs credits) or "buy a drink" (+30 thirst). Vendors are marked and plentiful; the
  player is never more than ~2 blocks from food.
- Consequences: at hunger/thirst <= 20, show a gentle HUD hint; at 0, health drains slowly
  (1 point / 10 s) until the player eats/drinks. Health never drops below a non-lethal floor
  in v1 (no death by starvation) — the loop is a reason to stop and sit at a restaurant, not
  a punishment.
- Economy: the player starts with a small amount of credits; mission rewards and a few free
  "vendor samples" keep it trivial. No grinding.
- This is a "stopping to eat/drink at restaurants" flavor loop, never the dominant mechanic.

### 7.3 Primary mission (an excuse to keep walking)

- Mission: "Find Maya at the rooftop garden of the Harbor Hotel before 2:00 AM."
- Structure (3 stages): (1) locate the Harbor Hotel (city-map item + signposts + the hotel's
  distinctive skyline), (2) enter and reach the rooftop garden (a marked interactable), (3)
  talk to Maya (dialogue) -> mission complete, credits reward.
- Wayfinding: a map (M key) shows the target district highlighted, and the HUD shows a compass
  hint ("Harbor Hotel — NE, 4 blocks"). Signposts at intersections name districts. No minimap
  on the main screen (keeps the view immersive).
- Optional side tasks (flavor, not required): buy a drink at a vendor (tutorializes the
  survival loop), deliver a note. One or two only; the primary mission is the spine.
- Time: in-game clock, night ~10 PM -> 2 AM (4 in-game hours = ~20-30 real minutes at default
  time scale). The deadline is generous and atmospheric; running out of time fails softly
  (retry at the hotel) rather than game-over.

### 7.4 Controls and UX (final)

- WASD move/strafe; arrows turn; Q/E turn (configurable); Enter/E interact; I inventory;
  M map; Esc menu; Ctrl-C quit. Vertical look via Up/Down (small, clamped) — optional but
  included.
- HUD (top row): left = district name + compass direction to objective; center = in-game
  clock; right = hunger/thirst bars (e.g. `H:███░░ T:████░`) + credits.
- All text/menus use the same cell buffer (no separate console line), keeping single-write
  flush and truecolor everywhere.

### 7.5 Explicit non-goals for v1

- No audio/music. No combat. No day/night cycle (always night). No save-file encryption.
  No online play. No mobile/touch. No CJK/emoji glyphs in the renderer.

---

## 8. Implementation phase breakdown (each node starts with zero strategy)

Each phase maps 1:1 to decisions already made above. (The harness may slice these
differently; the mapping is unambiguous.)

1. Engine skeleton + terminal abstraction + framebuffer + headless smoke test. (Sections 3,
   5.2, 6.3.)
2. DDA raycasting + walls + basic floor/sky (grayscale first). (2.3-2.5.)
3. Color palettes + glyph sets + lighting (fog, lamps, emissive) + neon signs/windows.
   (2.6, 2.7, 5.4.)
4. Procedural city generator + grid world + save/load. (5.3, 5.5.)
5. Movement + input + camera + HUD. (2.2, 3.5, 7.4.)
6. Interactables (restaurants/vendors, tables, doors) + survival loop + economy. (7.2.)
7. Mission system + wayfinding + NPC Maya + quest completion. (7.3.)
8. Packaging (run.sh/run.bat, pyproject, PyInstaller exe) + CI + README + LICENSE. (6.)

Each node's "done" is defined by its test file plus the smoke test still passing. No node
requires a new strategic decision.

---

## 9. Acceptance criteria for this document

- [x] Renderer technique named and fully specified (2D-DDA raycasting, 2.5D heightfield)
      with the concrete algorithm and why-not-SDF rationale.
- [x] Output approach named (full-screen truecolor cell buffer + RLE single-write flush)
      with 256-color fallback and explicit Windows VT/ctypes handling.
- [x] Module/data architecture laid out (directory tree, responsibilities, data formats,
      glyph/palette tables).
- [x] Tech stack chosen (Python 3.10+ stdlib-only) with clean-checkout rationale.
- [x] Build/test/package plan for Linux and Windows (run, package, unit + headless tests,
      CI matrix).
- [x] Game design concretely scoped (centerpiece, light survival, primary mission) with
      explicit non-goals.
- [x] Implementation broken into nodes with no residual strategy decisions.
