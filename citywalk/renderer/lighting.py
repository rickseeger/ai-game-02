"""Night lighting: light pools (additive glow) — emissive surfaces are added
separately at full brightness by the samplers (DESIGN 2.6)."""
import math

from .. import config


def light_contribution(x, y, z, lights):
    """Sum the additive glow of every light reaching a world point (x, y, z).

    Lights are (lx, ly, lz, r, g, b, radius, intensity) tuples. Returns an
    additive (r, g, b) triple that is clamped only at the point of addition.
    """
    r = g = b = 0
    for lx, ly, lz, cr, cg, cb, radius, intensity in lights:
        dx = x - lx
        dy = y - ly
        dz = z - lz
        d2 = dx * dx + dy * dy + dz * dz
        if d2 >= radius * radius:
            continue
        d = math.sqrt(d2)
        f = (1.0 - d / radius) ** config.LIGHT_FALLOFF * intensity
        r += cr * f
        g += cg * f
        b += cb * f
    return (int(r), int(g), int(b))


def make_light(x, y, z, rgb, radius, intensity=1.0):
    r, g, b = rgb
    return (x, y, z, r, g, b, radius, intensity)
