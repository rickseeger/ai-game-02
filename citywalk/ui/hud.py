"""One-line HUD rendered into reserved screen row 0 (DESIGN 5.2, 7.4).

Left: position, facing, fps. Right: hunger/thirst bars plus health and credits.
The bars turn amber at <= NEED_LOW and red when empty -- the "gentle hint" of
the light survival loop (DESIGN 7.2). A short transient message (eat/drink
feedback, "find a restaurant") is drawn between the two zones when present, and
a persistent vendor prompt ``[1] eat meal  [2] buy drink`` shows whenever the
player is within interact range of a vendor.

The framebuffer is ASCII-only (single-byte glyphs, tests enforce 0x20..0x7E),
so the bars use '#' (filled) and '.' (empty) rather than block glyphs.
"""
from .. import config
from ..assets.palettes import PALETTES

FILLED = "#"
EMPTY = "."
BAR_LEN = 10


def _meter_color(value):
    if value <= 0.0:
        return PALETTES["hud_danger"]
    if value <= config.NEED_LOW:
        return PALETTES["hud_warn"]
    return PALETTES["hud_fg"]


def _status_cells(needs):
    """Right-aligned survival status as a list of (glyph, fg-color) cells."""
    fg = PALETTES["hud_fg"]
    dim = PALETTES["hud_dim"]
    cells = []
    for label, value in (("H:", needs.hunger), ("T:", needs.thirst)):
        cells.append((" ", fg))
        cells.append((label, fg))
        filled = int(round(value / config.NEED_START * BAR_LEN))
        color = _meter_color(value)
        for i in range(BAR_LEN):
            cells.append((FILLED if i < filled else EMPTY,
                          color if i < filled else dim))
    cells.append((" hp:%d cr:%d " % (int(round(needs.health)), needs.credits), fg))
    return cells


def _draw_cells(fb, x, y, cells):
    for ch, color in cells:
        for c in ch:               # expand multi-char cells char by char
            if 0 <= x < fb.width:
                fb.set(x, y, c, color, (0, 0, 0))
            x += 1


def _text(fb, x, y, s, color):
    _draw_cells(fb, x, y, [(c, color) for c in s])


def render(fb, cam, fps, clock_text="", needs=None, near_vendor=False):
    w = fb.width
    fg = PALETTES["hud_fg"]
    warn = PALETTES["hud_warn"]
    black = (0, 0, 0)
    for i in range(w):
        fb.set(i, 0, " ", fg, black)

    left = " CITYWALK  pos=(%.1f,%.1f)  fps=%d %s" % (
        cam.x, cam.y, int(fps), clock_text)
    _text(fb, 0, 0, left, fg)

    status_w = 0
    if needs is not None:
        status = _status_cells(needs)
        status_w = sum(len(ch) for ch, _ in status)
        _draw_cells(fb, w - status_w, 0, status)

    msg = ""
    if needs is not None and needs.message:
        msg = needs.message
    elif near_vendor:
        msg = "[1] eat meal  [2] buy drink"
    if msg:
        text = " " + msg + " "
        x = len(left) + 1
        if x + len(text) <= w - status_w - 1:
            _text(fb, x, 0, text, warn)
