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

## Run

Linux / macOS / any VT terminal:

    python3 run.py            # interactive first-person walk

Windows:

    run.bat                   # or: python run.py

Controls: WASD move/strafe, Q/E or Left/Right turn, Up/Down look; when
standing at a restaurant/vendor, 1 = eat a meal, 2 = buy a drink, Enter =
interact (at the Harbor Hotel this rides to the rooftop and talks to Maya).
Esc or Ctrl-C quit. Recommended host: Windows Terminal (truecolor); legacy
conhost works at 256-color.

Headless (no TTY, for CI / quick check):

    python3 run.py --demo          # scripted fly-through -> citywalk_demo.ans
    python3 run.py --snapshot      # one frame as plain text

Requires Python 3.10+.

## Test

    python3 -m unittest discover -s tests

This runs the projection/math unit tests (DDA, floorcast inverse projection,
palette/glyph/LUT, grid), the moving-life tests (determinism, terrain
containment, continuous motion, sprite projection + wall occlusion), plus a
headless smoke test that renders 60 frames and asserts the framebuffer and
ANSI output are well-formed, the procedural city generator tests
(determinism, street connectivity, building placement, restaurant presence,
terrain, border containment), and the survival/interaction tests (decay math,
replenish clamping, credit economy, non-lethal health drain, and eat/drink
gated to reachable vendor locations).

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
