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
  engine/          main loop, clock, input   (reserved)
  world/           grid model (grid.py), facades, entities
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

Grid model implemented (streets, blocks, building footprints) and covered by
unit tests. Facades, movement, input, and renderer are owned by later nodes in
tree G10.
