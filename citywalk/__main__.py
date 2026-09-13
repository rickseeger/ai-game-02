"""Entry point: argument parsing, boot, and the main loop.

Modes:
  python3 run.py                 interactive first-person walk (needs a TTY)
  python3 run.py --demo          headless scripted fly-through (writes ANSI)
  python3 run.py --snapshot      render one frame, print plain text

The light survival loop (node 5) runs in every mode: hunger/thirst decay over
real time and can be replenished at restaurants/vendors with the 1 (eat) and
2 (drink) keys, gated to valid vendor locations by world.interact.
"""
import argparse
import sys
import time
from dataclasses import dataclass

from . import config
from .engine.clock import Clock
from .engine.framebuffer import FrameBuffer
from .engine.terminal import Terminal
from .renderer import renderer, sky
from .renderer.camera import Camera
from .ui import hud
from .world import gen
from .world.entities import LifeSystem
from .world.grid import TYPE_TABLE
from .world.interact import Interactor
from .world.survival import Needs


@dataclass
class Game:
    grid: object
    lights: list
    cam: Camera
    stars: list
    moon: tuple
    life: LifeSystem
    needs: Needs
    interactor: Interactor


def make_world(seed):
    city = gen.generate(seed=seed)
    stars = sky.make_stars(seed + 1)
    moon = (0.72, 0.16)
    cam = Camera(city.spawn[0], city.spawn[1], city.spawn[2])
    life = LifeSystem(city.grid, seed=seed)
    needs = Needs()
    interactor = Interactor(city.grid, city.restaurants)
    return Game(city.grid, city.lights, cam, stars, moon, life, needs, interactor)


def _try_move(cam, grid, dx, dy):
    nx = cam.x + dx
    if not grid.is_solid(int(nx), int(cam.y)):
        cam.x = nx
    ny = cam.y + dy
    if not grid.is_solid(int(cam.x), int(ny)):
        cam.y = ny


def update(cam, grid, keys, dt):
    move = config.MOVE_SPEED * dt
    if "forward" in keys:
        _try_move(cam, grid, cam.dir_x * move, cam.dir_y * move)
    if "back" in keys:
        _try_move(cam, grid, -cam.dir_x * move, -cam.dir_y * move)
    rx, ry = -cam.dir_y, cam.dir_x
    if "strafe_right" in keys:
        _try_move(cam, grid, rx * move, ry * move)
    if "strafe_left" in keys:
        _try_move(cam, grid, -rx * move, -ry * move)
    if "turn_right" in keys:
        cam.turn(config.TURN_SPEED * dt)
    if "turn_left" in keys:
        cam.turn(-config.TURN_SPEED * dt)
    if "look_up" in keys:
        cam.look(config.LOOK_SPEED * dt)
    if "look_down" in keys:
        cam.look(-config.LOOK_SPEED * dt)


def handle_needs(game, keys):
    """Survival actions: eat/drink, gated to valid vendor locations."""
    needs, inter = game.needs, game.interactor
    if "eat" in keys:
        inter.try_eat(needs, game.cam.x, game.cam.y)
    if "drink" in keys:
        inter.try_drink(needs, game.cam.x, game.cam.y)


def _render(fb, game):
    renderer.render_frame(fb, game.cam, game.grid, game.lights, game.stars,
                          game.moon, TYPE_TABLE, game.life)


def _draw_hud(fb, game, fps):
    hud.render(fb, game.cam, fps, "life=%d" % len(game.life.entities),
               needs=game.needs,
               near_vendor=game.interactor.at_vendor(game.cam.x, game.cam.y))


def run_interactive(seed):
    term = Terminal()
    if not term.isatty:
        print("No TTY detected; running the headless demo instead.", file=sys.stderr)
        return run_demo(seed, frames=90, out="citywalk_demo.ans",
                         width=config.DEFAULT_SIZE[0],
                         height=config.DEFAULT_SIZE[1])
    term.init()
    game = make_world(seed)
    clock = Clock(config.TARGET_FPS)
    try:
        w, h = term.get_size()
        fb = FrameBuffer(w, h)
        while True:
            dt = clock.delta()
            keys = term.poll_keys()
            if "quit" in keys:
                break
            update(game.cam, game.grid, keys, dt)
            game.life.update(dt)
            game.needs.tick(dt)
            handle_needs(game, keys)
            nw, nh = term.get_size()
            if (nw, nh) != (w, h):
                w, h = nw, nh
                fb = FrameBuffer(w, h)
            _render(fb, game)
            _draw_hud(fb, game, clock.smoothed_fps)
            term.flush(fb.to_ansi(term.color_mode))
            clock.cap()
    finally:
        term.teardown()


def run_snapshot(seed, width, height):
    game = make_world(seed)
    fb = FrameBuffer(width, height)
    _render(fb, game)
    _draw_hud(fb, game, config.TARGET_FPS)
    print(fb.to_text())


def run_demo(seed, frames, out, width=config.DEFAULT_SIZE[0], height=config.DEFAULT_SIZE[1]):
    game = make_world(seed)
    fb = FrameBuffer(width, height)
    t0 = time.perf_counter()
    total_dt = 1.0 / config.TARGET_FPS
    written = []
    for f in range(frames):
        keys = {"forward"}
        if (f // 60) % 2 == 0:
            keys.add("turn_right")
        else:
            keys.add("turn_left")
        update(game.cam, game.grid, keys, total_dt)
        game.life.update(total_dt)
        game.needs.tick(total_dt)
        _render(fb, game)
        _draw_hud(fb, game, config.TARGET_FPS)
        written.append(fb.to_ansi("truecolor"))
    dt = time.perf_counter() - t0
    fps = frames / dt
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("".join(written))
    print("demo: %d frames in %.2fs (%.1f fps) -> %s" % (frames, dt, fps, out))
    print("--- final frame (plain text) ---")
    print(fb.to_text())


def main(argv=None):
    p = argparse.ArgumentParser(prog="citywalk",
                                description="First-person color-ASCII night city")
    p.add_argument("--demo", action="store_true",
                   help="headless scripted fly-through, writes ANSI frames")
    p.add_argument("--snapshot", action="store_true",
                   help="render one frame and print it as plain text")
    p.add_argument("--frames", type=int, default=180)
    p.add_argument("--out", default="citywalk_demo.ans")
    p.add_argument("--width", type=int, default=config.DEFAULT_SIZE[0])
    p.add_argument("--height", type=int, default=config.DEFAULT_SIZE[1])
    p.add_argument("--seed", type=int, default=20260913)
    args = p.parse_args(argv)

    if args.snapshot:
        run_snapshot(args.seed, args.width, args.height)
    elif args.demo:
        run_demo(args.seed, args.frames, args.out, args.width, args.height)
    else:
        run_interactive(args.seed)


if __name__ == "__main__":
    main()
