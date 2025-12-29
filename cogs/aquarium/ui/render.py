
from typing import List, Optional

class AquariumRender:
    """Handles visual rendering of the Aquarium."""
    
    # Mapping Decor IDs to Emojis (Move to config later for scalability)
    ICONS = {
        'san_ho': '🪸', 'rong_bien': '🌿', 'ruong_vang': '⚱️',
        'ca_map': '🦈', 'mo_neo': '⚓', 'den_neon': '💡',
        'lau_dai_cát': '🏰', 'ngoc_trai_khong_lo': '🔮',
        None: '〰️' # Empty Slot water ripple
    }

    @staticmethod
    def generate_view(slots: List[Optional[str]]) -> str:
        """
        Generate ASCII art for the aquarium.
        Args:
            slots: List of 5 item_ids (or None).
        """
        # Ensure we have 5 elements
        safe_slots = slots[:5] + [None] * (5 - len(slots))
        
        # Convert IDs to Visuals
        visuals = [AquariumRender.ICONS.get(item, '❓') for item in safe_slots]
        
        # ASCII Art Layout (Fixed 5 slots)
        # Slot 1 (Top Center)
        # Slot 0 (Mid Left), Slot 2 (Mid Center), Slot 3 (Mid Right), Slot 4 (Far Right) ?
        # Based on user boilerplate:
        # 🌊 . 🐠 . {visuals[1]} . 🐟 . 🌊
        # {visuals[0]} . {visuals[2]} . {visuals[3]} . {visuals[4]}
        # 🏖️ . . 🐚 . . 🦀 . . 🏖️

        view = (
            f"🌊 . 🐠 . {visuals[1]} . 🐟 . 🌊\n"
            f"{visuals[0]} . {visuals[2]} . {visuals[3]} . {visuals[4]}\n"
            f"🏖️ . . 🐚 . . 🦀 . . 🏖️"
        )
        
        return f"```yaml\n{view}\n```"

render_engine = AquariumRender()
