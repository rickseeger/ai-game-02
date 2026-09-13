"""Entry point: argument parsing, boot, and the main loop.

Modes:
  python3 run.py                 interactive first-person walk (needs a TTY)
  python3 run.py --demo          headless scripted fly-through (writes ANSI)
  python3 run.py --snapshot      render one frame, print plain text
"""
import argparse
import sys
import time

from . import config
from .engine.clock import Clock
from .engine.framebuffer import FrameBuffer
from .engine.terminal import Terminal
from .renderer import renderer, sky
from .renderer.camera import Camera
from .ui import hud
from .world import gen
from .world.grid import TYPE_TABLE


def make_world(seed):
    grid, lights, spawn = gen.build(seed=seed)
    stars = sky.make_stars(seed + 1)
    moon = (0.72, 0.16)
    cam = Camera(spawn[0], spawn[1], spawn[2])
    return grid, lights, cam, stars, moon


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


def _render(fb, cam, grid, lights, stars, moon):
    renderer.render_frame(fb, cam, grid, lights, stars, moon, TYPE_TABLE)


def run_interactive(seed):
    term = Terminal()
    if not term.isatty:
        print("No TTY detected; running the headless demo instead.", file=sys.stderr)
        return run_demo(seed, frames=90, out="citywalk_demo.ans",
                         width=config.DEFAULT_SIZE[0],
                         height=config.DEFAULT_SIZE[1])
    term.init()
    grid, lights, cam, stars, moon = make_world(seed)
    clock = Clock(config.TARGET_FPS)
    try:
        w, h = term.get_size()
        fb = FrameBuffer(w, h)
        while True:
            dt = clock.delta()
            keys = term.poll_keys()
            if "quit" in keys:
                break
            update(cam, grid, keys, dt)
            nw, nh = term.get_size()
            if (nw, nh) != (w, h):
                w, h = nw, nh
                fb = FrameBuffer(w, h)
            _render(fb, cam, grid, lights, stars, moon)
            hud.render(fb, cam, clock.smoothed_fps)
            term.flush(fb.to_ansi(term.color_mode))
            clock.cap()
    finally:
        term.teardown()


def run_snapshot(seed, width, height):
    grid, lights, cam, stars, moon = make_world(seed)
    fb = FrameBuffer(width, height)
    _render(fb, cam, grid, lights, stars, moon)
    print(fb.to_text())


def run_demo(seed, frames, out, width=config.DEFAULT_SIZE[0], height=config.DEFAULT_SIZE[1]):
    grid, lights, cam, stars, moon = make_world(seed)
    fb = FrameBuffer(width, height)
    t0 = time.perf_counter()
    # scripted path: walk forward, slowly pan, gentle look bob
    total_dt = 1.0 / config.TARGET_FPS
    written = []
    for f in range(frames):
        keys = {"forward"}
        if (f // 60) % 2 == 0:
            keys.add("turn_right")
        else:
            keys.add("turn_left")
        update(cam, grid, keys, total_dt)
        _render(fb, cam, grid, lights, stars, moon)
        hud.render(fb, cam, config.TARGET_FPS)
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
