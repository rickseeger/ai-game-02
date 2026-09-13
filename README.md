# ai-game-02 — City Walkthrough

A first-person night-city walking game rendered in full-screen colorful ASCII.
The centerpiece is a lively, atmospheric NIGHT cityscape — buildings lit up at
night, streets, lit windows, street lamps — with (in later nodes) a light
survival loop and a mission to keep you walking.

Architecture is specified in DESIGN.md (the single source of truth). Tech
stack: Python 3.10+ standard library only, zero third-party dependencies.

## Current status

The core first-person 3D ASCII renderer is implemented and tested:

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

Package layout (`citywalk/`: engine / renderer / world / ui / assets) follows
DESIGN.md section 5.

## Run

Linux / macOS / any VT terminal:

    python3 run.py            # interactive first-person walk

Windows:

    run.bat                   # or: python run.py

Controls: WASD move/strafe, Q/E or Left/Right turn, Up/Down look, Esc or
Ctrl-C quit. Recommended host: Windows Terminal (truecolor); legacy conhost
works at 256-color.

Headless (no TTY, for CI / quick check):

    python3 run.py --demo          # scripted fly-through -> citywalk_demo.ans
    python3 run.py --snapshot      # one frame as plain text

Requires Python 3.10+.

## Test

    python3 -m unittest discover -s tests

This runs the projection/math unit tests (DDA, floorcast inverse projection,
palette/glyph/LUT, grid) plus a headless smoke test that renders 60 frames and
asserts the framebuffer and ANSI output are well-formed, and the procedural
city generator tests (determinism, street connectivity, building placement,
restaurant presence, terrain, border containment).

## Layout

    run.py, run.sh, run.bat    launchers
    citywalk/                  the game package
      engine/                  terminal abstraction, framebuffer, clock
      renderer/                camera, dda, walls, floorcast, sky, lighting,
                               palette, renderer orchestration
      world/                   grid + type table, seeded city generator
      ui/                      HUD
      assets/                  palettes and glyph sets
    tests/                     stdlib unittest suite
    DESIGN.md                  full architecture / strategy
