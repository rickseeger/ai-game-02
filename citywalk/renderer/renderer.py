"""Per-frame orchestration: sky -> floor -> walls into the framebuffer."""
from . import sky, floorcast, walls


def render_frame(fb, cam, grid, lights, stars, moon, type_table):
    w, h = fb.width, fb.height
    horizon = int(h / 2 + cam.pitch)
    horizon = max(0, min(h, horizon))
    sky.render(fb, cam, horizon, stars, moon)
    floorcast.render(fb, cam, grid, lights, horizon)
    walls.render(fb, cam, grid, lights, horizon, type_table)
