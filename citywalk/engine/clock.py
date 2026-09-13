"""Fixed-timestep loop helpers with an FPS cap."""
import time


class Clock:
    def __init__(self, target_fps):
        self.frame_time = 1.0 / target_fps
        self.last = time.perf_counter()
        self.smoothed_fps = float(target_fps)

    def delta(self):
        """Seconds since the previous call (for movement), then reset."""
        now = time.perf_counter()
        dt = now - self.last
        self.last = now
        if dt > 0:
            # exponential moving average for a stable on-screen FPS readout
            self.smoothed_fps += (1.0 / dt - self.smoothed_fps) * 0.1
        return dt

    def cap(self):
        """Sleep the remainder of this frame's budget to hold the target FPS."""
        now = time.perf_counter()
        remaining = self.frame_time - (now - self.last)
        if remaining > 0:
            time.sleep(remaining)
            self.last += self.frame_time
        else:
            self.last = now
