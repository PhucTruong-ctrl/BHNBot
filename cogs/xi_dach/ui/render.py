"""
Xi Dach Card Renderer - Optimized with Asset Manager & Pillow
"""
import asyncio
import io
import os
from typing import List, Tuple, Dict, Union, Optional
from PIL import Image

from core.logging import get_logger

logger = get_logger("CardRenderer")

# ==================== CONFIGURATION ====================

# Asset Paths
ASSETS_DIR = "assets"
CARDS_DIR = os.path.join(ASSETS_DIR, "cards")
BG_PATH = os.path.join(ASSETS_DIR, "table_bg.jpg")  # Prefer JPG as per context

# Card Dimensions (Resize target)
CARD_WIDTH = 80
CARD_HEIGHT = 112  # 5:7 aspect ratio roughly (Compact Mobile)
CARD_SPACING = 10  # Spacing between cards

# Layout for Game State (Table View)
SECTION_PADDING = 10
ROW_HEIGHT = CARD_HEIGHT + 25

# Suit Mapping for Filenames (Symbol -> Filename Suffix)
SUIT_MAP = {
    "♠️": "Spades",
    "♠": "Spades",
    "♥️": "Hearts",
    "♥": "Hearts",
    "♦️": "Diamonds",
    "♦": "Diamonds",
    "♣️": "Clubs",
    "♣": "Clubs",
}

# Rank Mapping (Symbol -> Filename Suffix)
RANK_MAP = {
    "10": "10",
    "A": "A",
    "J": "J",
    "Q": "Q",
    "K": "K"
}
# Add 2-9 mapping
for i in range(2, 10):
    RANK_MAP[str(i)] = str(i)


class AssetManager:
    """Singleton Asset Manager for Caching Images in RAM."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AssetManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.cards: Dict[str, Image.Image] = {}
        self.back: Optional[Image.Image] = None
        self.bg: Optional[Image.Image] = None
        self._initialized = True
        self.loaded = False

    def load_assets(self):
        """Loads all assets from disk and resizes them once."""
        if self.loaded:
            return

        logger.info("Loading Xi Dach assets into RAM...")
        
        try:
            # 1. Load Background
            bg_path_final = BG_PATH
            if not os.path.exists(bg_path_final):
                bg_path_final = bg_path_final.replace(".jpg", ".png")
            
            if os.path.exists(bg_path_final):
                self.bg = Image.open(bg_path_final).convert("RGB")
                logger.info(f"Loaded background: {bg_path_final}")
            else:
                logger.warning(f"Background not found at {bg_path_final}, using plain color.")
                self.bg = Image.new("RGB", (800, 600), (35, 39, 42))

            # 2. Load Card Back
            back_path = os.path.join(CARDS_DIR, "cardBack.png")
            if os.path.exists(back_path):
                img = Image.open(back_path).convert("RGBA")
                self.back = img.resize((CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)
            else:
                logger.error(f"Card back not found: {back_path}")
                self.back = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (150, 0, 0))

            # 3. Load 52 Cards
            count = 0
            for suit_sym, suit_name in [("♠️", "Spades"), ("♥️", "Hearts"), ("♦️", "Diamonds"), ("♣️", "Clubs")]:
                # Ranks: 2-10, J, Q, K, A
                ranks = [str(i) for i in range(2, 11)] + ["J", "Q", "K", "A"]
                for rank in ranks:
                    filename = f"card{suit_name}{rank}.png"
                    path = os.path.join(CARDS_DIR, filename)
                    
                    key = f"{rank}{suit_sym}" # Key used by renderer lookup
                    
                    if os.path.exists(path):
                        img = Image.open(path).convert("RGBA")
                        # Resize NOW to save RAM and CPU later
                        img_resized = img.resize((CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)
                        self.cards[key] = img_resized
                        count += 1
                        
                        # Also map single char variants just in case
                        self.cards[f"{rank}{suit_sym[0]}"] = img_resized
                    else:
                        logger.warning(f"Missing card asset: {filename}")

            self.loaded = True
            logger.info(f"Asset loading complete. Loaded {count} cards.")

        except Exception as e:
            logger.error(f"Failed to load assets: {e}", exc_info=True)

    def get_card(self, rank: str, suit: str) -> Image.Image:
        """Get cached card image."""
        key = f"{rank}{suit}"
        if key in self.cards:
            return self.cards[key]
        return self.back if self.back else Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (255, 0, 255))

    def get_back(self) -> Image.Image:
        return self.back

    def get_bg(self, width: int, height: int) -> Image.Image:
        """Get background crop or resized version."""
        if not self.bg:
             return Image.new("RGB", (width, height), (54, 57, 63))
        bg_w, bg_h = self.bg.size
        if width > bg_w or height > bg_h:
             return self.bg.resize((max(width, bg_w), max(height, bg_h)))
        left = (bg_w - width) // 2
        top = (bg_h - height) // 2
        return self.bg.crop((left, top, left + width, top + height))

# Global Instance
assets = AssetManager()


def _get_card_key(card_obj) -> Tuple[str, str]:
    """Helper to extract rank/suit from Discord objects or tuples."""
    if hasattr(card_obj, 'rank') and hasattr(card_obj, 'suit'):
        rank = card_obj.rank.symbol
        suit = card_obj.suit.value
    else:
        rank, suit = card_obj # Fallback tuple ("A", "♠️")
    return rank, suit


def render_player_hand_sync(
    cards: List[Union[Tuple[str, str], object]],
    player_name: str = "Player"
) -> bytes:
    """Render a single player's hand using cached assets."""
    try:
        # Lazy load check
        if not assets.loaded:
            assets.load_assets()

        num_cards = len(cards)
        if num_cards == 0:
            return io.BytesIO().getvalue()

        # Calculate Canvas Size
        padding_x = 20
        padding_y = 20
        
        total_width = padding_x * 2 + (num_cards * CARD_WIDTH) + ((num_cards - 1) * CARD_SPACING)
        total_height = padding_y * 2 + CARD_HEIGHT
        
        # Prepare Background
        img = assets.get_bg(total_width, total_height).copy()
        
        # Paste Cards
        current_x = padding_x
        y = padding_y
        
        for card_obj in cards:
            rank, suit = _get_card_key(card_obj)
            card_img = assets.get_card(rank, suit)
            img.paste(card_img, (current_x, y), card_img)
            current_x += CARD_WIDTH + CARD_SPACING
            
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=False)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"[RENDER_ERROR] {e}", exc_info=True)
        return io.BytesIO().getvalue()


async def render_player_hand(
    cards: List[Union[Tuple[str, str], object]],
    player_name: str = "Player"
) -> bytes:
    """Async wrapper used by multi.py"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, render_player_hand_sync, cards, player_name)


# Backwards compatibility
async def render_hand(cards: List[Tuple[str, str]], hide_first: bool = False) -> bytes:
    """Async render single hand."""
    return await render_player_hand(cards, "Bài của bạn")


# ==================== TABLE RENDERER (Restored for Compatibility) ====================

def render_game_state_sync(
    dealer_cards: List[Union[Tuple[str, str], object]],
    players: List[Dict],
    hide_dealer: bool = True
) -> bytes:
    """
    Render complete game state (Dealer + Players) using AssetManager.
    Restored to fix ImportError in cog.py.
    """
    try:
        if not assets.loaded:
            assets.load_assets()

        # 1. Calc Dimensions
        # Dealer row + 1 Row per player (simple vertical layout)
        num_players = len(players)
        
        # Assume max width based on max cards (e.g. 5)
        # 5 cards width = 20 + 5*120 + 4*15 + 20 = ~680
        # Let's verify max width required
        max_cards = 5
        row_width = 40 + (max_cards * CARD_WIDTH) + ((max_cards-1) * CARD_SPACING)
        row_width = max(row_width, 600) # Min width
        
        total_height = SECTION_PADDING + ROW_HEIGHT # Dealer row
        total_height += num_players * ROW_HEIGHT
        total_height += SECTION_PADDING
        
        # 2. Create BG
        img = assets.get_bg(row_width, total_height).copy()
        
        # 3. Draw Dealer
        dealer_y = SECTION_PADDING
        current_x = SECTION_PADDING
        
        for i, card_obj in enumerate(dealer_cards):
            if i == 0 and hide_dealer:
                card_img = assets.get_back()
            else:
                rank, suit = _get_card_key(card_obj)
                card_img = assets.get_card(rank, suit)
            
            img.paste(card_img, (current_x, dealer_y), card_img)
            current_x += CARD_WIDTH + CARD_SPACING
            
        # 4. Draw Players
        current_y = dealer_y + ROW_HEIGHT
        
        for player in players:
            p_cards = player.get('cards', [])
            current_x = SECTION_PADDING
            
            for card_obj in p_cards:
                rank, suit = _get_card_key(card_obj)
                card_img = assets.get_card(rank, suit)
                
                img.paste(card_img, (current_x, current_y), card_img)
                current_x += CARD_WIDTH + CARD_SPACING
            
            current_y += ROW_HEIGHT
            
        # 5. Save
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=False)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"[RENDER_TABLE_ERROR] {e}", exc_info=True)
        return io.BytesIO().getvalue()


async def render_game_state(
    dealer_cards: List[Union[Tuple[str, str], object]],
    players: List[Dict],
    hide_dealer: bool = True
) -> bytes:
    """Async wrapper for render_game_state_sync."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, render_game_state_sync, dealer_cards, players, hide_dealer
    )
