"""Global display glitch helper for Hacker Attack disaster.

Other modules can import and use apply_display_glitch() to garble fish names
while the Hacker Attack disaster is active. FishingCog will set the global
state via set_glitch_state().
"""

import time
import random
import string

DISPLAY_GLITCH_ACTIVE = False
DISPLAY_GLITCH_END_TIME = 0.0


def set_glitch_state(active: bool, end_time: float):
    global DISPLAY_GLITCH_ACTIVE, DISPLAY_GLITCH_END_TIME
    DISPLAY_GLITCH_ACTIVE = bool(active)
    DISPLAY_GLITCH_END_TIME = float(end_time or 0)


def apply_display_glitch(text: str) -> str:
    """Apply display glitch effect to text (garble characters) when active."""
    try:
        if not DISPLAY_GLITCH_ACTIVE or time.time() >= DISPLAY_GLITCH_END_TIME:
            return text
        garble_chars = "▓░█╬▄▀┃┫┬┪◄►▼▲"
        result = []
        for ch in text:
            if ch in string.ascii_letters or ch in "0123456789":
                if random.random() < 0.4:
                    result.append(random.choice(garble_chars))
                else:
                    result.append(ch)
            else:
                result.append(ch)
        return "".join(result)
    except Exception:
        # Fail-safe: never break rendering
        return text
