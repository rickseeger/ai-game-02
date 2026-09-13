"""Camera: continuous position, facing angle, and the camera plane."""
import math

from .. import config


class Camera:
    def __init__(self, x, y, angle, floor_z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.floor_z = float(floor_z)  # elevation of the floor the player stands on
        self.pitch = 0.0               # vertical look offset, in screen rows
        self.set_angle(angle)

    def set_angle(self, angle):
        self.angle = angle % (2.0 * math.pi)
        fov = math.radians(config.FOV_DEG)
        tan = math.tan(fov / 2.0)
        self.dir_x = math.cos(self.angle)
        self.dir_y = math.sin(self.angle)
        # camera plane: perpendicular to dir, length tan(FOV/2)
        self.plane_x = -self.dir_y * tan
        self.plane_y = self.dir_x * tan

    def turn(self, da):
        self.set_angle(self.angle + da)

    def move_forward(self, dist):
        self.x += self.dir_x * dist
        self.y += self.dir_y * dist

    def strafe(self, dist):
        # right vector = (-dir_y, dir_x) == the camera plane direction (screen right)
        self.x += -self.dir_y * dist
        self.y += self.dir_x * dist

    def look(self, d_rows):
        self.pitch += d_rows
        self.pitch = max(-config.MAX_LOOK, min(config.MAX_LOOK, self.pitch))

    def eye_z(self):
        return self.floor_z + config.EYE_HEIGHT
