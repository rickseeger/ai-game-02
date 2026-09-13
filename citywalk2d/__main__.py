"""Runnable entrypoint for citywalk2d.

Prints a startup banner and exits cleanly. The real game loop (engine,
world, renderer, input) is wired in by later nodes; this module only
proves the package boots and the entrypoint is runnable on any platform.
"""

from __future__ import annotations

from . import __title__, __version__


def main(argv: list[str] | None = None) -> int:
    """Boot the skeleton and return an exit code (0 on success)."""
    print(f"{__title__} v{__version__} — 2D top-down color-ASCII city walk")
    print("Skeleton ready. Game subsystems land in later nodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
