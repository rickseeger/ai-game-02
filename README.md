# ai-game-02 — citywalk2d

A 2D top-down color-ASCII city-walk game.

This is a **clean skeleton** for the 2D game. The previous 3D raycast
`citywalk/` code from the failed G8 attempt has been removed entirely.

## Stack

Python 3.10+ standard library only — zero third-party dependencies. The game
is terminal-based color ASCII; the renderer and game subsystems land in later
nodes.

## Layout

```
citywalk2d/
  __init__.py      package metadata
  __main__.py      runnable entrypoint
  config.py        central tunables (placeholder)
  engine/          main loop, clock, input   (reserved)
  world/           grid, facades, entities   (reserved)
  renderer/        top-down ASCII output     (reserved)
  ui/              HUD and overlays          (reserved)
tests/             stdlib unittest suite
run.py             cross-platform launcher
run.sh             Linux/macOS run script
run.bat            Windows run script
pyproject.toml     dependency manifest
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

## Test

```
python3 -m unittest discover -s tests
```

## Status

Skeleton only. No grid, facades, movement, input, or renderer yet — each is
owned by a later node in tree G10.
