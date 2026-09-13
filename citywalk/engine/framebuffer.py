"""The W x H color-ASCII cell buffer and its single-write RLE flush.

The renderer never talks to the terminal; it fills this buffer, and
to_ansi() serializes the whole frame into one ANSI string (DESIGN 3.1).
Glyphs are single-byte ASCII so the glyph buffer is a bytearray. fg/bg are
flat array('B') of interleaved RGB triples.
"""
from array import array

from ..renderer.palette import rgb_to_256


class FrameBuffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        n = width * height
        self.glyph = bytearray(b" " * n)
        self.fg = array("B", bytes(3 * n))
        self.bg = array("B", bytes(3 * n))

    def set(self, x, y, glyph, fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0)):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        i = (y * self.width + x) * 3
        self.glyph[y * self.width + x] = ord(glyph[0]) & 0xFF
        self.fg[i], self.fg[i + 1], self.fg[i + 2] = fg_rgb
        self.bg[i], self.bg[i + 1], self.bg[i + 2] = bg_rgb

    def clear(self):
        self.glyph[:] = b" " * (self.width * self.height)

    def to_ansi(self, color_mode="truecolor"):
        """Serialize the whole buffer to one ANSI string (home + per-row cursor,
        color run-length encoding, one glyph per cell)."""
        out = []
        ap = out.append
        ap("\x1b[H")
        w, h = self.width, self.height
        fg, bg, glyph = self.fg, self.bg, self.glyph
        prev_fg = None
        prev_bg = None
        for y in range(h):
            ap("\x1b[%d;1H" % (y + 1))
            base = y * w
            for x in range(w):
                i = (base + x) * 3
                cr, cg, cb = fg[i], fg[i + 1], fg[i + 2]
                br, bb, bk = bg[i], bg[i + 1], bg[i + 2]
                if color_mode == "truecolor":
                    key = (cr, cg, cb)
                    if key != prev_fg:
                        ap("\x1b[38;2;%d;%d;%dm" % key)
                        prev_fg = key
                    key = (br, bb, bk)
                    if key != prev_bg:
                        ap("\x1b[48;2;%d;%d;%dm" % key)
                        prev_bg = key
                else:
                    fi = rgb_to_256((cr, cg, cb))
                    bi = rgb_to_256((br, bb, bk))
                    if fi != prev_fg:
                        ap("\x1b[38;5;%dm" % fi)
                        prev_fg = fi
                    if bi != prev_bg:
                        ap("\x1b[48;5;%dm" % bi)
                        prev_bg = bi
                ap(chr(glyph[base + x]))
        ap("\x1b[0m")
        return "".join(out)

    def to_text(self):
        """Plain-text (no color) rendering, one line per row — for snapshots/logs."""
        rows = []
        for y in range(self.height):
            base = y * self.width
            rows.append(bytes(self.glyph[base:base + self.width]).decode("ascii", "replace"))
        return "\n".join(rows)
