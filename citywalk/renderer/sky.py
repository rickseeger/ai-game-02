"""Night sky: vertical gradient, deterministic stars, and the moon."""
import random

from .. import config
from ..assets.palettes import PALETTES
from .palette import lerp, add_rgb, scale, clamp_rgb


def make_stars(seed, count=120):
    """Deterministic star field in fractional screen coords (x, y, bright)."""
    rng = random.Random(seed)
    stars = []
    for _ in range(count):
        stars.append((rng.random(), rng.random() * 0.6, 0.3 + 0.7 * rng.random()))
    return stars


def render(fb, cam, horizon, stars, moon):
    w, h = fb.width, fb.height
    step = config.FLOOR_STEP
    zenith = PALETTES["sky_zenith"]
    horizon_c = PALETTES["sky_horizon"]
    # vertical gradient: row 0 (top) -> zenith, row horizon-1 -> horizon color
    for y in range(0, min(horizon, h)):
        t = y / max(1, horizon - 1)
        color = lerp(zenith, horizon_c, t)
        for x in range(0, w, step):
            end = min(w, x + step)
            for xx in range(x, end):
                fb.set(xx, y, " ", color, color)
    # stars (only those above the horizon)
    for sx, sy, bright in stars:
        yy = int(sy * h)
        xx = int(sx * w)
        if 0 <= yy < horizon and 0 <= xx < w:
            c = scale((220, 225, 235), bright)
            fb.set(xx, yy, ".", c, horizon_c if yy >= 0 else zenith)
    # moon + small halo
    mx = int(moon[0] * w)
    my = int(moon[1] * h)
    moon_c = PALETTES["moon"]
    if 0 <= my < horizon:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                px, py = mx + dx, my + dy
                if 0 <= px < w and 0 <= py < h and py < horizon:
                    if dx == 0 and dy == 0:
                        fb.set(px, py, "o", moon_c, moon_c)
                    else:
                        halo = lerp(horizon_c, moon_c, 0.25)
                        fb.set(px, py, " ", horizon_c, halo)
