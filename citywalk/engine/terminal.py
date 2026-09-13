"""Platform abstraction: the ONLY module that imports platform-specific APIs.

Exposes init()/teardown(), get_size(), color_mode(), poll_keys(), flush().
Everything else in the engine/renderer is platform-neutral (DESIGN 5.2).
"""
import os
import shutil
import sys


class KeyEvent:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name


class Terminal:
    def __init__(self):
        self.isatty = sys.stdin.isatty() and sys.stdout.isatty()
        self.os_name = os.name  # 'posix' or 'nt'
        self._saved = None
        self.color_mode = self._detect_color_mode()

    # -- color capability detection (DESIGN 3.2) -------------------------
    def _detect_color_mode(self):
        ct = os.environ.get("COLORTERM", "")
        if "truecolor" in ct or "24bit" in ct:
            return "truecolor"
        if os.environ.get("WT_SESSION"):
            return "truecolor"
        term = os.environ.get("TERM", "")
        if "256color" in term:
            return "256"
        return "256"  # graceful fallback once VT is enabled

    # -- lifecycle -------------------------------------------------------
    def init(self):
        if not self.isatty:
            return
        if self.os_name == "posix":
            import termios
            import tty
            fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(fd)
            tty.setraw(fd)
        else:
            self._enable_vt_windows()
        self.flush("\x1b[?1049h\x1b[?25l\x1b[?7l")

    def teardown(self):
        if not self.isatty:
            return
        self.flush("\x1b[?7h\x1b[?25h\x1b[?1049l")
        if self.os_name == "posix":
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, self._saved)

    def _enable_vt_windows(self):
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            ENABLE_VT = 0x0004
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint32()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VT | 0x0001)
        except Exception:
            pass  # best effort; conhost still renders at 256-color

    # -- size ------------------------------------------------------------
    def get_size(self):
        try:
            sz = shutil.get_terminal_size()
            w, h = sz.columns, sz.lines
        except Exception:
            w, h = 100, 40
        return (max(80, w), max(24, h))

    # -- input (non-blocking, platform-neutral KeyEvent) -----------------
    def poll_keys(self):
        keys = []
        if not self.isatty:
            return keys
        if self.os_name == "posix":
            import select
            while select.select([sys.stdin], [], [], 0)[0]:
                ch = os.read(sys.stdin.fileno(), 1)
                if ch == b"\x1b":
                    rest = b""
                    if select.select([sys.stdin], [], [], 0)[0]:
                        rest += os.read(sys.stdin.fileno(), 2)
                    name = self._map_escape(ch + rest)
                else:
                    name = self._map_char(ch)
                if name:
                    keys.append(name)
        else:
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    ch = msvcrt.getwch()
                    name = self._map_arrow_win(ch)
                else:
                    name = self._map_char_win(ch)
                if name:
                    keys.append(name)
        return keys

    @staticmethod
    def _map_char(ch):
        m = {
            b"w": "forward", b"W": "forward",
            b"s": "back", b"S": "back",
            b"a": "strafe_left", b"A": "strafe_left",
            b"d": "strafe_right", b"D": "strafe_right",
            b"q": "turn_left", b"Q": "turn_left",
            b"e": "turn_right", b"E": "turn_right",
            b"\x03": "quit", b"\x04": "quit", b"\x1a": "quit",
        }
        return m.get(ch)

    @staticmethod
    def _map_escape(seq):
        m = {
            b"\x1b[A": "look_up",
            b"\x1b[B": "look_down",
            b"\x1b[C": "turn_right",
            b"\x1b[D": "turn_left",
        }
        if seq in m:
            return m[seq]
        return "quit" if seq == b"\x1b" else None

    @staticmethod
    def _map_char_win(ch):
        m = {
            "w": "forward", "W": "forward", "s": "back", "S": "back",
            "a": "strafe_left", "A": "strafe_left", "d": "strafe_right",
            "D": "strafe_right", "q": "turn_left", "Q": "turn_left",
            "e": "turn_right", "E": "turn_right",
        }
        if ch == "\x03":
            return "quit"
        return m.get(ch)

    @staticmethod
    def _map_arrow_win(ch):
        return {"H": "look_up", "P": "look_down",
                "M": "turn_right", "K": "turn_left"}.get(ch)

    # -- output ----------------------------------------------------------
    def flush(self, s):
        if self.os_name == "posix":
            os.write(1, s.encode("utf-8", "replace"))
        else:
            sys.stdout.write(s)
            sys.stdout.flush()
