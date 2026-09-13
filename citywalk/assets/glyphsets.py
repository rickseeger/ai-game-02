"""Glyph sets: the luminance ramp and emissive detail glyphs.

The ramp is fixed and documented (DESIGN.md section 5.4), ordered dark ->
bright. v1 renderer glyphs are pure ASCII so the framebuffer stays a single
bytearray and every glyph is single-width on both Linux and Windows.
"""

RAMP = r''' .'`^",:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$'''

# Emissive / detail glyphs (ASCII only in v1 renderer).
EMISSIVE_GLYPHS = {
    "window": "o",
    "lamp": "*",
    "moon": "o",
    "star": ".",
}


def ramp_glyph(lum):
    """Map luminance in [0, 1] to a ramp glyph (0 = darkest, 1 = brightest)."""
    lum = 0.0 if lum < 0.0 else (1.0 if lum > 1.0 else lum)
    idx = int(round(lum * (len(RAMP) - 1)))
    return RAMP[idx]


def luminance(rgb):
    """Perceptual luminance of an RGB triple, normalized to [0, 1]."""
    r, g, b = rgb
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
