"""Per-frame orchestration: sky -> floor -> walls -> sprites into the
framebuffer. A per-column z-buffer (wall perpendicular depth) is filled by the
wall pass so the sprite pass can correctly occlude life behind walls."""
from . import sky, floorcast, walls, sprites

INF = float("inf")


def render_frame(fb, cam, grid, lights, stars, moon, type_table, life=None):
    w, h = fb.width, fb.height
    horizon = int(h / 2 + cam.pitch)
    horizon = max(0, min(h, horizon))
    sky.render(fb, cam, horizon, stars, moon)
    floorcast.render(fb, cam, grid, lights, horizon)
    zbuffer = [INF] * w
    walls.render(fb, cam, grid, lights, horizon, type_table, zbuffer)
    sprites.render(fb, cam, lights, horizon, life, zbuffer)
