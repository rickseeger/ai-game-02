# ai-game-02 — citywalk2d

A 2D top-down color-ASCII city-walk game.

This is a clean scaffold for the 2D game. The previous 3D raycast
`citywalk/` code from the failed G8 attempt has been removed entirely.

## Stack

Python 3.10+ standard library only — zero third-party dependencies. The game
is terminal-based color ASCII.

## Layout

```
citywalk2d/
  __init__.py      package metadata
  __main__.py      runnable entrypoint (interactive game, --demo, --script)
  config.py        central tunables (world + viewport defaults)
  engine/          main game loop (assembles world + input + renderer)
  input/           keyboard input (WASD/arrows -> Action)
  world/           grid model (grid.py), facades, player
  renderer/        color-ASCII frame buffer, camera, scene renderer
  ui/              HUD and overlays          (reserved)
tests/             stdlib unittest suite
run.py             cross-platform launcher
run.sh             Linux/macOS run script
run.bat            Windows run script
pyproject.toml     dependency manifest
```

## City grid model

The foundational data layer lives in `citywalk2d/world/grid.py`. Every cell
in the city is exactly one of three kinds: `STREET` (walkable road),
`BUILDING` (impassable footprint), or `INTERIOR` (open ground inside a block).
`generate_city()` carves a connected street grid into city blocks and fills
each block with non-overlapping rectangular buildings, deterministically, from
a seed.

```python
from citywalk2d.world import generate_city

city = generate_city(seed=42)
city.is_walkable(x, y)      # -> bool
city.building_at(x, y)      # -> Building | None
for b in city.buildings:    # footprint rect + block membership
    print(b.rect, b.block_id)
print(city.render())        # '#' building, '.' street, ' ' interior
```

## Player & movement

The player lives in `citywalk2d/world/player.py`. `spawn_player(city)` drops a
player onto a guaranteed street cell; `Player.move(direction)` advances exactly
one cell per step and only into walkable street cells, so buildings, block
interiors, and the map edge all block movement. Movement consumes a canonical
`Direction` (UP / DOWN / LEFT / RIGHT) -- raw key decoding is the input node's
job.

```python
from citywalk2d.world import Direction, generate_city, spawn_player

city = generate_city(seed=42)
player = spawn_player(city)
moved = player.move(Direction.RIGHT)   # True if the cell was a street cell
print(player.position)
```

## Keyboard input

The input layer lives in `citywalk2d/input`. It maps raw terminal bytes and
escape sequences onto a canonical `Action` enum whose movement members carry
the matching `Direction`:

```python
from citywalk2d.input import Action, KeyReader

with KeyReader() as keys:
    action = keys.read()          # blocks for one keypress
    if action is Action.QUIT:
        ...
    elif action is not None:
        player.move(action.direction)
```

Recognised keys are WASD (plus their shifted forms) and the arrow keys.
Arrow keys are decoded from the ANSI escape sequences a POSIX terminal emits
(`ESC [ A/B/C/D`) and from the virtual-key pairs a Windows console emits
(`\xe0`/`\x00` followed by `H/P/K/M`). `q`, `Q`, Ctrl-C and Escape all map
to `Action.QUIT`. The byte -> action table is pure and deterministic and is
covered by `tests/test_input.py`; the raw terminal reading itself
(termios / msvcrt) must be exercised interactively on a real keyboard.

## Renderer and camera

The renderer lives in `citywalk2d/renderer`. It composes the city grid,
building facades, and player into a single ANSI 256-color top-down frame, and
a camera follows the player with a viewport window clamped to the map edge.

```python
from citywalk2d.renderer import Camera, render
from citywalk2d.world import assign_facades, generate_city, spawn_player

city = generate_city(seed=42)
facades = assign_facades(city)
player = spawn_player(city, seed=23)

print(render(city, facades, player))                  # 80x24 window
print(render(city, facades, player, viewport_width=40, viewport_height=20))
```

`render(...)` returns a string; `render_frame(...)` returns the underlying
`FrameBuffer` (a grid of `Cell` values, each one character plus optional
256-color foreground/background) for callers that want to compose before
serializing. The camera is exposed directly too:

```python
px, py = player.position
camera = Camera.centered_on(px, py, 40, 20, city.width, city.height)
```

Every cell type has a distinct look: streets are painted asphalt, block
interiors are concrete, buildings carry their seeded facade pattern and color,
and the player is a highlighted `@`. Reference renders are saved under
`docs/` (`reference_render.txt` and `reference_render_viewport.txt` hold the
ANSI frames; the `_plain` variants are human-readable and strip the escapes).

## Engine / game loop

The engine (`citywalk2d/engine`) is the glue that assembles the grid,
facades, movement, input, and renderer into a single running loop: init the
world, render the viewport, read an action, move the player one cell,
re-render, repeat until quit. The core loop is I/O-agnostic so it can be
driven by a real keyboard (`run_interactive`) or by a scripted sequence of
actions (`run_script`), which is what the integration test uses.

```python
from citywalk2d.engine import build_city, run_script
from citywalk2d.input import Action

city, facades, player = build_city(seed=42)          # grid + facades + player
frames = run_script(                                  # drive a scripted walk
    city, facades, player,
    [Action.RIGHT, Action.RIGHT, Action.DOWN, Action.QUIT],
    color=False,
)
print(player.position, "in", frames, "frames")
```

## Install & run

Two ways to run the game: use a prebuilt standalone binary (no Python needed),
or run from source (Python 3.10+).

### Prebuilt binaries (recommended — no Python required)

Standalone one-file executables are committed under `release/` and run with no
dependencies installed.

Linux x86-64:

```
chmod +x release/citywalk2d-linux-x86_64
./release/citywalk2d-linux-x86_64
```

Windows x86-64: double-click `release\citywalk2d-windows-x86_64.exe` (a
console app; Windows Terminal recommended). On first run SmartScreen may warn
because the exe is unsigned — choose "More info" -> "Run anyway".

SHA-256 checksums are in `release/SHA256SUMS.txt`; see `release/README.md` for
verification and headless modes. Both binaries are rebuilt cleanly from source
by the `package` jobs in `.github/workflows/ci.yml` (see `citywalk2d.spec`).

### Run from source (needs Python 3.10+)

Play interactively (WASD / arrow keys to move, `q` / Esc / Ctrl-C to quit):

Linux / macOS:

```
./run.sh
```

Windows:

```
run.bat
```

Or directly:

```
python3 -m citywalk2d
```

Render one static demo city:

```
python3 -m citywalk2d --demo
```

Drive the loop headlessly from a script of actions (one per line:
`up`/`down`/`left`/`right`, WASD letters, or `quit`; `#` comments and blank
lines are ignored):

```
python3 -m citywalk2d --script walk.txt --no-color --seed 7
```

Other options: `--seed N`, `--width W`, `--height H`, `--viewport WxH`,
`--no-color`.

## Test

```
python3 -m unittest discover -s tests
```

## Status

Grid model, building facades, player movement, keyboard input mapping,
renderer/camera, and the assembled game loop (engine) are implemented and
covered by unit tests -- including an integration test that drives a scripted
walk around the city. Cross-platform packaging (node 8) ships prebuilt
Linux and Windows one-file executables under `release/`, with reproducible
PyInstaller builds in CI. The HUD (ui) remains owned by a later node in tree
G10.

