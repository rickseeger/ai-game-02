"""Central tunables for citywalk.

Every render/game constant lives here. config.py IS the config in v1
(DESIGN.md section 5.3). Units: 1.0 == one grid cell == one meter.
"""

# --- Renderer -----------------------------------------------------------
FOV_DEG = 66.0            # horizontal field of view, degrees
EYE_HEIGHT = 0.5          # camera height above the player's floor, in cells
MAX_DDA_STEPS = 512       # ray step bound (open sky / never hits a wall)
FLOOR_STEP = 2            # floor/sky rendered at half horizontal resolution

# --- Atmosphere / lighting ----------------------------------------------
FOG_COLOR = (8, 10, 24)
FOG_DIST = 24.0
LIGHT_FALLOFF = 2.0       # exponent on (1 - d/radius) glow falloff

# --- Movement -----------------------------------------------------------
MOVE_SPEED = 4.0          # cells per second
TURN_SPEED = 2.2          # radians per second
LOOK_SPEED = 16.0         # rows per second (vertical look)
MAX_LOOK = 20             # max vertical look offset, in screen rows

# --- Loop ---------------------------------------------------------------
TARGET_FPS = 30
FRAME_BUDGET = 1.0 / TARGET_FPS

# --- Fallbacks ----------------------------------------------------------
DEFAULT_SIZE = (120, 40)  # headless / non-TTY fallback size
MIN_SIZE = (80, 24)

# --- Survival loop (DESIGN 7.2) ------------------------------------------
NEED_START = 100.0            # hunger/thirst start full (100 = full)
NEED_DECAY_PER_SEC = 1.0 / 60.0   # 1 point per 60 s -> full bar ~100 min
NEED_LOW = 20.0               # gentle HUD hint at or below this
MEAL_HUNGER = 35.0            # hunger restored by "eat a meal"
DRINK_THIRST = 30.0           # thirst restored by "buy a drink"
MEAL_COST = 8                 # credits for a meal
DRINK_COST = 5                # credits for a drink
START_CREDITS = 40
START_HEALTH = 100.0
HEALTH_DRAIN_PER_SEC = 0.1    # 1 point / 10 s while a meter sits at 0
HEALTH_FLOOR = 25.0           # no death by starvation in v1
FREE_SAMPLES = 4              # free vendor samples keep the economy trivial
INTERACT_RANGE = 1.6          # cells from a vendor serving cell to interact
MESSAGE_TTL = 2.5             # seconds a transient HUD message stays visible
