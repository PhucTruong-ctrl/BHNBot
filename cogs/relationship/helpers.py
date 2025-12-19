import datetime
import random
import logging
from .constants import *

logger = logging.getLogger("relationship")

def get_affinity_title(points):
    """Get the title based on affinity points."""
    title = "Người Lạ"
    for threshold, t in sorted(AFFINITY_TITLES.items()):
        if points >= threshold:
            title = t
    return title

def get_pet_state(pet_level, last_fed_time):
    """
    Determine the pet's state/image based on time and hunger.
    Returns a string identifier for the image state: 'idle', 'sleep', 'eating', 'playing', 'sad'.
    """
    now = datetime.datetime.now()
    
    # 1. Check hunger (> 24h since last fed)
    # last_fed_time can be a string from SQLite or a datetime object
    try:
        if isinstance(last_fed_time, str):
            try:
                last_fed = datetime.datetime.fromisoformat(last_fed_time)
            except ValueError:
                # Handle different formats if necessary, e.g., with or without milliseconds
                try:
                     last_fed = datetime.datetime.strptime(last_fed_time, "%Y-%m-%d %H:%M:%S.%f")
                except:
                     last_fed = datetime.datetime.strptime(last_fed_time, "%Y-%m-%d %H:%M:%S")
        else:
            last_fed = last_fed_time
    except Exception as e:
        logger.error(f"Failed to parse last_fed_time {last_fed_time}: {e}, defaulting to idle")
        return "idle"
    
    # Make last_fed timezone naive if now is naive, or both aware. 
    # Assuming system time is naive local time or UTC. 
    # Best to stick to whatever discord.utils.utcnow() returns if using that, but here we used datetime.now()
    
    # Simple check: if (now - last_fed).total_seconds() > 24 * 3600
    if (now - last_fed).total_seconds() > 24 * 3600:
        return "sad" # Hungry/Sad
        
    # 2. Check sleep time (22h - 6h)
    current_hour = now.hour
    if current_hour >= 22 or current_hour < 6:
        return "sleep"
        
    # 3. Default: Random Idle/Play
    return random.choice(["idle", "play"])

def get_pet_image_url(level, state):
    """
    Return a URL or file path for the pet image.
    For now, returning placeholder or local asset path logic.
    """
    # In a real scenario, map this to actual files or URLs
    # Example: assets/pet_lv{level}_{state}.png
    # For now, we return a description or a placeholder that the Embed can use (or we'll just describe it in text if no image)
    return f"https://example.com/pet/lv{level}/{state}.png" # Placeholder

def calculate_next_level_xp(level):
    return level * PET_XP_PER_LEVEL
