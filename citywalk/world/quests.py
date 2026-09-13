"""Mission system (DESIGN 7.3): declarative quest definitions + a small
progression state machine.

The primary mission gives the player a reason to keep walking the city:

    "Find Maya at the rooftop garden of the Harbor Hotel before 2:00 AM."

Three stages, each a tracked objective with a satisfiable completion:

  1. find_hotel     -- locate the Harbor Hotel; completes automatically when
                       the player walks within ``config.MISSION_HOTEL_RANGE``
                       of the hotel's rooftop-garden entrance (the wayfinding
                       is a compass hint: direction + block distance).
  2. reach_rooftop  -- press Enter at the entrance to ride up to the rooftop
                       garden; completes on interact.
  3. talk_maya      -- press Enter again at the rooftop garden to talk to
                       Maya; completes the mission and awards credits.

The deadline is a soft fail: if the in-game clock passes 2:00 AM, Maya "has
gone home" and the mission gently resets (clock back to 10 PM, stage back to
1) -- a reason to try again, never a game-over (DESIGN 7.3).

This module is pure state + progression: no rendering, no location gating of
its own (the caller supplies the player's position and interact presses).
``ui.hud`` reads ``objective``/``compass_hint``/``clock_text``; ``__main__``
feeds position, Enter presses, and ``tick(dt)`` for the clock. The mission
composes with the survival loop (``world.survival``) purely through the
shared ``Needs`` credits: completing the mission pays the reward there.
"""
import math

from .. import config


# --- declarative mission definition (documented schema, DESIGN 5.3) -------
FIND_MAYA = {
    "id": "find_maya",
    "title": "Find Maya",
    "intro": "A note: 'Find me at the Harbor Hotel. -- Maya'",
    "deadline": "02:00",
    "reward_credits": config.MISSION_REWARD,
    "stages": [
        {"id": "find_hotel",
         "objective": "Find the Harbor Hotel"},
        {"id": "reach_rooftop",
         "objective": "Ride to the rooftop (Enter)"},
        {"id": "talk_maya",
         "objective": "Talk to Maya (Enter)"},
    ],
    "complete_text": "You found Maya. The night is yours.",
}

# event text emitted to the HUD when a stage is satisfied
_REACHED_HOTEL = "There it is -- the Harbor Hotel, glowing on the waterfront."
_ENTER_ROOFTOP = "The elevator hums; you step onto the rooftop garden."

# 8-wind compass labels; index = round(atan2(dy, dx) / (pi/4)), +y is south
_COMPASS = ("E", "SE", "S", "SW", "W", "NW", "N", "NE")


def direction_label(dx, dy):
    """Compass direction from a displacement (grid y grows downward = south)."""
    ang = math.atan2(dy, dx)
    idx = int(round(ang / (math.pi / 4.0))) % 8
    return _COMPASS[idx]


class Quest:
    """A single mission: stages, objectives, a clock, and progression state."""

    def __init__(self, definition, target, start_hour=None, deadline_hour=None):
        self.definition = definition
        self.target = (float(target[0]), float(target[1]))
        self.stage_index = 0
        self.completed = False
        self.rewarded = False
        self.start_hour = (config.MISSION_START_HOUR if start_hour is None
                           else start_hour)
        self.deadline_hour = (config.MISSION_DEADLINE_HOUR if deadline_hour is None
                              else deadline_hour)
        self.minutes_of_day = self.start_hour * 60

    # -- queries -----------------------------------------------------------
    @property
    def stage(self):
        return self.definition["stages"][self.stage_index]

    @property
    def stage_id(self):
        return self.stage["id"]

    @property
    def objective(self):
        """The currently tracked objective text."""
        if self.completed:
            return self.definition["complete_text"]
        return self.stage["objective"]

    @property
    def intro(self):
        return self.definition["intro"]

    def is_complete(self):
        return self.completed

    def compass_hint(self, x, y):
        """(direction_label, blocks) to the target, or None once complete."""
        if self.completed:
            return None
        dx = self.target[0] - x
        dy = self.target[1] - y
        dist = math.hypot(dx, dy)
        if dist < 0.5:
            return ("here", 0)
        label = direction_label(dx, dy)
        blocks = max(1, int(round(dist / config.MISSION_BLOCK_CELLS)))
        return (label, blocks)

    def clock_text(self):
        hh = int(self.minutes_of_day) // 60
        mm = int(self.minutes_of_day) % 60
        return "%02d:%02d" % (hh % 24, mm)

    # -- simulation ---------------------------------------------------------
    def tick(self, dt):
        """Advance the in-game clock; soft-fail (reset) past the deadline.

        Returns a HUD message when a soft-fail occurred, else None.
        """
        if self.completed or not (dt > 0.0):
            return None
        self.minutes_of_day += dt * config.MISSION_MINUTES_PER_REAL_SECOND
        if self.minutes_of_day >= self.deadline_hour * 60:
            self.minutes_of_day = self.start_hour * 60
            self.stage_index = 0
            return ("It's past 2:00 AM -- Maya has gone home. "
                    "Return to the hotel and try again.")
        return None

    # -- progression (fed by the game loop) ---------------------------------
    def on_position(self, x, y):
        """Advance stage 1 when the player is within range of the hotel.

        Returns a HUD message on advance, else None.
        """
        if self.completed or self.stage_id != "find_hotel":
            return None
        dx = x - self.target[0]
        dy = y - self.target[1]
        if dx * dx + dy * dy <= config.MISSION_HOTEL_RANGE ** 2:
            self.stage_index += 1
            return _REACHED_HOTEL
        return None

    def on_interact(self, x, y):
        """Advance stage 2 / complete stage 3 by interacting at the target.

        Returns a HUD message on advance/completion, else None.
        """
        if self.completed:
            return None
        dx = x - self.target[0]
        dy = y - self.target[1]
        if dx * dx + dy * dy > config.INTERACT_RANGE ** 2:
            return None
        if self.stage_id == "reach_rooftop":
            self.stage_index += 1
            return _ENTER_ROOFTOP
        if self.stage_id == "talk_maya":
            self.completed = True
            self.rewarded = True
            return self.definition["complete_text"]
        # stage 1: interacting at the hotel before "finding" it is a no-op
        return None

    def collect_reward(self):
        """Return the credits owed (once) and mark them collected."""
        if not self.rewarded:
            return 0
        self.rewarded = False
        return self.definition["reward_credits"]
