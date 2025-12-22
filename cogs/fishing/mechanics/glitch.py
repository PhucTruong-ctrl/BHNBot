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


def is_glitch_active() -> bool:
    """Check if glitch is currently active."""
    return DISPLAY_GLITCH_ACTIVE and time.time() < DISPLAY_GLITCH_END_TIME


def apply_display_glitch(text: str) -> str:
    """Apply display glitch effect to text (garble characters) when active.
    Glitches letters and numbers aggressively (40% chance each)."""
    try:
        if not is_glitch_active():
            return text
        
        garble_chars = "▓░█╬▄▀┃┫┬┪◄►▼▲"
        result = []
        for ch in text:
            # Garble ASCII letters, numbers, and Vietnamese characters
            if ch.isalnum() or ord(ch) > 127:  # ASCII letters/digits or non-ASCII (Vietnamese)
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


def apply_glitch_aggressive(text: str) -> str:
    """Apply AGGRESSIVE glitch effect - garbles more aggressively (50% chance).
    Used for all fishing output text during hacker attack."""
    try:
        if not is_glitch_active():
            return text
        
        garble_chars = "▓░█╬▄▀┃┫┬┪◄►▼▲?@#$%^&*"
        result = []
        for ch in text:
            # Glitch most characters (50% chance for letters/numbers, 30% for others)
            if ch.isalnum() or ord(ch) > 127:
                if random.random() < 0.5:
                    result.append(random.choice(garble_chars))
                else:
                    result.append(ch)
            elif ch not in "\n\t ":  # Glitch some punctuation too
                if random.random() < 0.3:
                    result.append(random.choice(garble_chars))
                else:
                    result.append(ch)
            else:
                result.append(ch)
        return "".join(result)
    except Exception:
        # Fail-safe: never break rendering
        return text


def apply_glitch_lite(text: str) -> str:
    """Apply LITE glitch effect - garbles less aggressively (20% chance).
    Used for minor visual effects during events."""
    try:
        if not is_glitch_active():
            return text
        
        garble_chars = "▓░█▄▀"
        result = []
        for ch in text:
            if ch.isalnum() or ord(ch) > 127:
                if random.random() < 0.2:
                    result.append(random.choice(garble_chars))
                else:
                    result.append(ch)
            else:
                result.append(ch)
        return "".join(result)
    except Exception:
        return text


def apply_glitch_moderate(text: str) -> str:
    """Apply MODERATE glitch effect - garbles with 30% chance.
    Used for moderate visual effects during events."""
    try:
        if not is_glitch_active():
            return text
        
        garble_chars = "▓░█╬▄▀┃◄►"
        result = []
        for ch in text:
            if ch.isalnum() or ord(ch) > 127:
                if random.random() < 0.3:
                    result.append(random.choice(garble_chars))
                else:
                    result.append(ch)
            else:
                result.append(ch)
        return "".join(result)
    except Exception:
        return text
