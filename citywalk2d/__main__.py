"""Runnable entrypoint for citywalk2d.

Prints a startup banner and exits cleanly by default.  ``--demo`` generates a
city with the grid model and prints it, so the data layer can be eyeballed
from any platform::

    python3 run.py --demo

The real game loop (engine, world, renderer, input) is wired in by later
nodes; this module only proves the package boots and the grid model works.
"""

from __future__ import annotations

import sys

from . import __title__, __version__


def main(argv: list[str] | None = None) -> int:
    """Boot the skeleton and return an exit code (0 on success)."""
    if argv is None:
        argv = sys.argv[1:]

    if "--demo" in argv:
        from .world import generate_city

        city = generate_city()
        print(f"{__title__} v{__version__} — generated city ({city.width}x{city.height}, "
              f"{len(city.blocks)} blocks, {len(city.buildings)} buildings)")
        print(city.render())
        return 0

    print(f"{__title__} v{__version__} — 2D top-down color-ASCII city walk")
    print("Skeleton ready. Game subsystems land in later nodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
