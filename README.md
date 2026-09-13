# ai-game-02 — City Walkthrough

A first-person night-city walking game rendered in full-screen colorful ASCII.
The centerpiece is a lively, atmospheric NIGHT cityscape — buildings lit up at
night, streets, lit windows, street lamps — with a light survival loop and a
mission to keep you walking.

Architecture is specified in DESIGN.md (the single source of truth). Tech
stack: Python 3.10+ standard library only, zero third-party dependencies.

## Current status

The game is feature-complete and ships as a cross-platform delivery:

- 2D-DDA grid raycasting extended to 2.5D (per-cell wall height + elevation).
- Truecolor cell framebuffer with 256-color fallback and RLE single-write flush.
- Wall/window sampling, floor + sky casting, distance fog, light pools, and
  emissive lit windows / moon / stars.
- Walk/look camera with smooth movement and collision.
- A seeded, multi-zone procedural night city (DESIGN 5.5): a Manhattan street
  grid with a connected navigable sidewalk network, concentric zoning
  (plaza / downtown / midtown / residential / industrial / park / waterfront),
  lit-window buildings, terrain elevation (sunken harbor, raised parks), street
  lamps, a Harbor Hotel landmark, and commercial corridors lined with
  restaurants (lit storefront + awning + sidewalk tables/chairs).
- A moving night-life population (DESIGN 5.5): cars that drive the street
  grid, pedestrians that walk the sidewalk network, and pets that wander
  sidewalks/parks. All life is a deterministic seeded cell-walk with
  continuous interpolation and is rendered as fog/light-shaded sprites
  that are correctly occluded by walls (per-column z-buffer).
- A light survival loop (DESIGN 7.2): hunger and thirst decay by 1 point per
  60 real seconds (a full bar lasts ~100 minutes); eating/drinking at a
  restaurant/vendor restores them. Stand at a vendor's sidewalk tables/awning
  and press 1 (eat a meal, +35 hunger) or 2 (buy a drink, +30 thirst). At
  <= 20 the HUD bars turn amber; at 0 health drains slowly down to a
  non-lethal floor -- a reason to stop and sit, never a punishment.
- A primary mission (DESIGN 7.3): "Find Maya at the rooftop garden of the
  Harbor Hotel before 2:00 AM." The HUD tracks a three-stage objective:
  (1) walk to the Harbor Hotel -- a compass hint (direction + blocks) points
  the way; (2) press Enter at the glowing rooftop-garden entrance on the
  hotel's city side to ride up; (3) press Enter again to talk to Maya and
  complete the mission for +50 credits. The 2:00 AM deadline is a soft fail:
  past it, Maya "has gone home" and the mission gently resets -- a reason to
  try again, never a game-over. The mission composes with the survival loop
  (the reward lands in the same credit wallet).

Package layout (`citywalk/`: engine / renderer / world / ui / assets) follows
DESIGN.md section 5.

## Install and run

### Requirements

Python 3.10+ for the source path (nothing else — the game is stdlib-only).
For the prebuilt binaries below, no Python is needed at all. Recommended host:
any truecolor/VT terminal (Windows Terminal, gnome-terminal, kitty, alacritty,
wezterm, iTerm2, tmux).

### Linux / macOS — from source

    git clone https://github.com/rickseeger/ai-game-02.git
    cd ai-game-02
    python3 -m unittest discover -s tests     # optional: verify the suite is green
    python3 run.py                            # or: ./run.sh

Optional pip install (exposes a `citywalk` console command):

    python3 -m pip install .
    citywalk

### Windows — from source

1. Install Python 3.10+ from https://www.python.org/ (tick "Add python.exe to
   PATH" during setup).
2. Download or clone this repository.
3. Double-click `run.bat`, or from a command prompt:

    python run.py

Recommended host: Windows Terminal (truecolor). Legacy conhost works at
256-color via the ctypes VT-enable path.

### Prebuilt artifacts (no Python needed)

Standalone one-file builds are committed under `release/` (see
`release/README.md` and `release/SHA256SUMS.txt`). They run with nothing
installed.

Linux x86-64:

    curl -LO https://github.com/rickseeger/ai-game-02/raw/main/release/citywalk-linux-x86_64
    chmod +x citywalk-linux-x86_64
    ./citywalk-linux-x86_64

Windows x86-64: download
`https://github.com/rickseeger/ai-game-02/raw/main/release/citywalk-windows-x86_64.exe`
and double-click it. SmartScreen may warn on the unsigned exe — choose
"More info" -> "Run anyway".

## Controls

WASD move/strafe, Q/E or Left/Right turn, Up/Down look; when standing at a
restaurant/vendor, 1 = eat a meal, 2 = buy a drink, Enter = interact (at the
Harbor Hotel this rides to the rooftop and talks to Maya). Esc or Ctrl-C quit.

## Headless modes (CI / quick check)

    python3 run.py --demo          # scripted fly-through -> citywalk_demo.ans
    python3 run.py --snapshot      # one frame as plain text

The prebuilt binaries accept the same flags (e.g.
`./citywalk-linux-x86_64 --snapshot`).

## Test

    python3 -m unittest discover -s tests

The suite (stdlib `unittest`, no third-party runner) passes on a clean
checkout with no dependencies installed and covers:

- projection/math (DDA, floorcast inverse projection, palette/glyph/LUT, grid);
- the moving-life system (determinism, terrain containment, continuous motion,
  sprite projection + wall occlusion);
- a headless smoke test that renders 60 frames and asserts the framebuffer and
  ANSI output are well-formed (proves the game boots and renders in CI);
- the procedural city generator (determinism, street connectivity, building
  placement, restaurant presence, terrain, border containment);
- the survival loop (decay math, replenish clamping, credit economy,
  non-lethal health drain, eat/drink gated to reachable vendors);
- the primary mission (stages, objective tracking, compass wayfinding, soft
  deadline, credit reward, integration with the generated city).

## Build a standalone binary (optional)

The committed `citywalk.spec` reproduces the `release/` binaries with
PyInstaller `--onefile` (a build-time-only dependency). From a clean checkout:

Linux / macOS:

    python3 -m venv .venv && .venv/bin/pip install pyinstaller
    .venv/bin/pyinstaller --clean citywalk.spec     # -> dist/citywalk

Windows (PowerShell):

    python -m venv .venv; .venv\Scripts\pip install pyinstaller
    .venv\Scripts\pyinstaller --clean citywalk.spec   # -> dist\citywalk.exe

CI (`.github/workflows/ci.yml`) runs the test matrix on `ubuntu-latest` and
`windows-latest` and builds the Windows exe as an artifact.

## Layout

    run.py, run.sh, run.bat    launchers
    citywalk.spec              PyInstaller spec (reproduces release/ binaries)
    citywalk/                  the game package
      engine/                  terminal abstraction, framebuffer, clock
      renderer/                camera, dda, walls, floorcast, sky, lighting,
                               palette, renderer orchestration
      world/                   grid + type table, seeded city generator
      ui/                      HUD
      assets/                  palettes and glyph sets
    tests/                     stdlib unittest suite
    release/                   prebuilt Linux + Windows artifacts + checksums
    .github/workflows/ci.yml   test + package CI
    DESIGN.md                  full architecture / strategy
