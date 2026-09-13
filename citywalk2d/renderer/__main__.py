"""Render a demo city to the terminal: ``python3 -m citywalk2d.renderer``.

Reproduces the saved reference render so the cityscape can be eyeballed from
any platform.  By default it renders the *whole* city (no camera window); pass
``--viewport WxH`` to render a camera window centered on the player instead.

Flags::

    --seed N       generation seed (default 42)
    --player-seed N player spawn seed (default 7)
    --viewport WxH render a W-wide, H-tall window centered on the player
    --plain        strip ANSI color (plain characters only)
    --out FILE     write the frame to FILE instead of stdout
"""

from __future__ import annotations

import sys

from ..world import assign_facades, generate_city, spawn_player
from . import render, strip_ansi

DEFAULT_SEED = 42


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    seed = DEFAULT_SEED
    player_seed = 7
    viewport = None
    plain = False
    out = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--seed":
            i += 1
            seed = int(argv[i])
        elif arg == "--player-seed":
            i += 1
            player_seed = int(argv[i])
        elif arg == "--viewport":
            i += 1
            w, _, h = argv[i].partition("x")
            viewport = (int(w), int(h))
        elif arg == "--plain":
            plain = True
        elif arg == "--out":
            i += 1
            out = argv[i]
        else:
            print(f"unknown flag: {arg}", file=sys.stderr)
            return 2
        i += 1

    city = generate_city(seed=seed)
    facades = assign_facades(city)
    player = spawn_player(city, seed=player_seed)

    if viewport is not None:
        frame = render(city, facades, player, viewport_width=viewport[0], viewport_height=viewport[1])
    else:
        frame = render(
            city, facades, player,
            viewport_width=city.width, viewport_height=city.height,
        )
    if plain:
        frame = strip_ansi(frame)

    if out is not None:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(frame + "\n")
    else:
        print(frame)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
