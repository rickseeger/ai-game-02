"""One-line HUD rendered into reserved screen row 0 (DESIGN 5.2, 7.4)."""
import math

from ..assets.palettes import PALETTES


def render(fb, cam, fps, clock_text=""):
    w = fb.width
    fg = PALETTES["hud_fg"]
    black = (0, 0, 0)
    deg = int(math.degrees(cam.angle) % 360.0)
    text = " CITYWALK  pos=(%.1f,%.1f)  facing=%d  fps=%d %s " % (
        cam.x, cam.y, deg, int(fps), clock_text)
    for i in range(w):
        ch = text[i] if i < len(text) else " "
        fb.set(i, 0, ch, fg, black)
