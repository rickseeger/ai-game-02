# ai-game-02 — citywalk2d

A 2D top-down color-ASCII city-walk game.

This is a clean scaffold for the 2D game. The previous 3D raycast
`citywalk/` code from the failed G8 attempt has been removed entirely.

## Stack

Python 3.10+ standard library only — zero third-party dependencies. The game
is terminal-based color ASCII; the renderer and game subsystems land in later
nodes.

## Layout

```
citywalk2d/
  __init__.py      package metadata
  __main__.py      runnable entrypoint (--demo renders a generated city)
  config.py        central tunables (placeholder)
  engine/          main loop, clock, state   (reserved)
  input/           keyboard input (WASD/arrows -> Action)
  world/           grid model (grid.py), facades, player
  renderer/        top-down ASCII output     (reserved)
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

## Run

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
python3 run.py
```

Render a demo city:

```
python3 run.py --demo
```

## Test

```
python3 -m unittest discover -s tests
```

## Status

Grid model, building facades, player movement, and keyboard input mapping
are implemented and covered by unit tests. The renderer and the main game
loop are owned by later nodes in tree G10.
