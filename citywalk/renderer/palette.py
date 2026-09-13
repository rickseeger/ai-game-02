"""Color math, distance fog, and the 256-color quantization LUT."""
import math

from .. import config
from ..assets.palettes import PALETTES


def clamp_rgb(rgb):
    return tuple(max(0, min(255, int(round(c)))) for c in rgb)


def lerp(a, b, t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return (int(round(a[0] + (b[0] - a[0]) * t)),
            int(round(a[1] + (b[1] - a[1]) * t)),
            int(round(a[2] + (b[2] - a[2]) * t)))


def add_rgb(a, b):
    return (min(255, a[0] + b[0]), min(255, a[1] + b[1]), min(255, a[2] + b[2]))


def brighten(rgb, factor=1.3):
    return clamp_rgb((rgb[0] * factor, rgb[1] * factor, rgb[2] * factor))


def scale(rgb, factor):
    return (int(round(rgb[0] * factor)), int(round(rgb[1] * factor)),
            int(round(rgb[2] * factor)))


def fog(surface, dist):
    """Distance fog: lerp surface toward the night fog color."""
    t = min(1.0, dist / config.FOG_DIST)
    return lerp(surface, config.FOG_COLOR, t)


# -- 256-color LUT (xterm: 6x6x6 cube + grayscale ramp) -------------------
_CUBE_LEVELS = (0, 95, 135, 175, 215, 255)


def _cube_level(v):
    best, bd = 0, 1000
    for i, lv in enumerate(_CUBE_LEVELS):
        d = abs(v - lv)
        if d < bd:
            bd, best = d, i
    return best


def rgb_to_256(rgb):
    r, g, b = rgb
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + (r - 8) // 10
    return 16 + 36 * _cube_level(r) + 6 * _cube_level(g) + _cube_level(b)
