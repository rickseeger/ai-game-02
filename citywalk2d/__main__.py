"""Runnable entrypoint for citywalk2d.

``python -m citywalk2d`` launches the interactive game -- the grid, facades,
movement, input, and renderer assembled into a single running loop.  Also::

    python -m citywalk2d --demo                   # one static city render
    python -m citywalk2d --script walk.txt        # scripted, headless loop
    python -m citywalk2d --no-color               # plain ASCII (no escapes)
    python -m citywalk2d --seed 7 --width 48 --height 32 --viewport 40x20

A script file holds one action per line (blank lines and ``#`` comments are
skipped): ``up``/``down``/``left``/``right``, the WASD letters, or
``quit``/``q``/``exit``.  Use ``-`` as the path to read the script from stdin.
"""

from __future__ import annotations

import argparse
import sys

from . import __title__, __version__
from . import config
from .engine import build_city, parse_script_action, run_interactive, run_script
from .world import generate_city


def _parse_viewport(text: str) -> tuple[int, int]:
    """Parse a ``WxH`` viewport string into ``(w, h)`` ints."""
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(f"viewport must be WxH, got {text!r}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="citywalk2d",
        description=f"{__title__} v{__version__} -- 2D top-down color-ASCII city walk",
    )
    parser.add_argument("--demo", action="store_true",
                        help="render one static city and exit")
    parser.add_argument("--seed", type=int, default=None, help="world seed")
    parser.add_argument("--width", type=int, default=None, help="world width in cells")
    parser.add_argument("--height", type=int, default=None, help="world height in cells")
    parser.add_argument("--viewport", metavar="WxH", type=_parse_viewport,
                        default=None, help="viewport size, e.g. 40x20")
    parser.add_argument("--no-color", action="store_true",
                        help="disable ANSI color escapes")
    parser.add_argument("--script", metavar="FILE", default=None,
                        help="run the loop from a script of actions ('-' = stdin)")
    return parser


def _load_script(path: str):
    """Yield one ``Action`` per recognised line of a script file (or stdin)."""
    stream = sys.stdin if path == "-" else open(path, "r", encoding="utf-8")
    try:
        for lineno, line in enumerate(stream, 1):
            action = parse_script_action(line)
            if action is None:
                token = line.strip()
                if token and not token.startswith("#"):
                    print(
                        f"citywalk2d: warning: ignoring unrecognised action "
                        f"{token!r} (line {lineno})",
                        file=sys.stderr,
                    )
                continue
            yield action
    finally:
        if stream is not sys.stdin:
            stream.close()


def _viewport_or_none(args) -> tuple[int | None, int | None]:
    if args.viewport is None:
        return None, None
    return args.viewport


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested mode; returns an exit code."""
    if argv is None:
        argv = sys.argv[1:]
    args = _build_parser().parse_args(argv)

    width = args.width if args.width is not None else config.CITY_WIDTH
    height = args.height if args.height is not None else config.CITY_HEIGHT
    seed = args.seed if args.seed is not None else config.CITY_SEED
    color = not args.no_color
    vw, vh = _viewport_or_none(args)

    if args.demo:
        city = generate_city(width=width, height=height, seed=seed)
        print(
            f"{__title__} v{__version__} -- generated city "
            f"({city.width}x{city.height}, {len(city.blocks)} blocks, "
            f"{len(city.buildings)} buildings, seed={seed})"
        )
        print(city.render())
        return 0

    if args.script is not None:
        city, facades, player = build_city(width=width, height=height, seed=seed)
        frames = run_script(
            city, facades, player, _load_script(args.script),
            write_frame=print,
            viewport_width=vw, viewport_height=vh, color=color,
        )
        print(
            f"-- script finished: player at {player.position} after {frames} frames",
            file=sys.stderr,
        )
        return 0

    if not sys.stdin.isatty():
        print(
            f"{__title__}: interactive mode needs a terminal -- "
            f"try `--demo` or `--script FILE`",
            file=sys.stderr,
        )
        return 1

    city, facades, player = build_city(width=width, height=height, seed=seed)
    run_interactive(city, facades, player, viewport_width=vw, viewport_height=vh, color=color)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
