"""
Xi Dach Card Renderer - Generates card images using Pillow

Renders complete game state as a single image showing dealer and all players.
Uses asyncio.run_in_executor for non-blocking image generation.
"""
import asyncio
import io
from typing import List, Optional, Tuple, Dict
from PIL import Image, ImageDraw, ImageFont

# Card dimensions
CARD_WIDTH = 60
CARD_HEIGHT = 84
CARD_SPACING = 8
CARD_RADIUS = 6

# Layout
SECTION_PADDING = 15
HAND_ROW_HEIGHT = CARD_HEIGHT + 40  # Cards + label

# Colors
BG_COLOR = (54, 57, 63)  # Discord dark theme
CARD_BG = (255, 255, 255)
CARD_BORDER = (50, 50, 50)
RED_SUIT = (220, 53, 69)
BLACK_SUIT = (33, 37, 41)
HIDDEN_BG = (70, 100, 140)
HIDDEN_PATTERN = (90, 120, 160)
TEXT_COLOR = (255, 255, 255)
LABEL_COLOR = (185, 187, 190)

# Suits
SUIT_INFO = {
    "♠️": ("♠", BLACK_SUIT),
    "♥️": ("♥", RED_SUIT),
    "♦️": ("♦", RED_SUIT),
    "♣️": ("♣", BLACK_SUIT),
}



def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get font with fallback."""
    # Prioritize Bold/Clear fonts
    for name in ["segoeuib.ttf", "verdanab.ttf", "arialbd.ttf", "seguiemj.ttf", "arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_card(
    draw: ImageDraw.Draw,
    x: int, y: int,
    rank: str, suit: str,
    font_large: ImageFont.FreeTypeFont,
    font_small: ImageFont.FreeTypeFont
) -> None:
    """Draw a single playing card."""
    # Background
    draw.rounded_rectangle(
        (x, y, x + CARD_WIDTH, y + CARD_HEIGHT),
        radius=CARD_RADIUS,
        fill=CARD_BG,
        outline=CARD_BORDER
    )
    
    # Get suit color
    suit_symbol, color = SUIT_INFO.get(suit, ("?", BLACK_SUIT))
    
    # Rank top-left
    draw.text((x + 4, y + 2), rank, font=font_small, fill=color)
    # Small suit below rank
    draw.text((x + 4, y + 14), suit_symbol, font=font_small, fill=color)
    
    # Large suit in center
    try:
        bbox = draw.textbbox((0, 0), suit_symbol, font=font_large)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except:
        tw, th = 24, 24
    cx = x + (CARD_WIDTH - tw) // 2
    cy = y + (CARD_HEIGHT - th) // 2
    draw.text((cx, cy), suit_symbol, font=font_large, fill=color)
    
    # Rank bottom-right (rotated look)
    draw.text((x + CARD_WIDTH - 16, y + CARD_HEIGHT - 28), rank, font=font_small, fill=color)
    draw.text((x + CARD_WIDTH - 16, y + CARD_HEIGHT - 16), suit_symbol, font=font_small, fill=color)


def _draw_hidden_card(draw: ImageDraw.Draw, x: int, y: int) -> None:
    """Draw a face-down card."""
    draw.rounded_rectangle(
        (x, y, x + CARD_WIDTH, y + CARD_HEIGHT),
        radius=CARD_RADIUS,
        fill=HIDDEN_BG,
        outline=CARD_BORDER
    )
    # Pattern
    for i in range(4, CARD_WIDTH - 4, 6):
        for j in range(4, CARD_HEIGHT - 4, 6):
            if (i + j) % 12 == 0:
                draw.ellipse((x+i, y+j, x+i+3, y+j+3), fill=HIDDEN_PATTERN)
    
    # Question mark
    font = _get_font(28)
    draw.text((x + CARD_WIDTH//2 - 8, y + CARD_HEIGHT//2 - 14), "?", font=font, fill=(255,255,255))


def render_game_state_sync(
    dealer_cards: List[Tuple[str, str]],
    players: List[Dict],
    hide_dealer: bool = True
) -> bytes:
    """Render complete game state to PNG.
    
    Args:
        dealer_cards: List of (rank, suit) for dealer
        players: List of dicts with 'name', 'cards', 'score', 'bet'
        hide_dealer: Hide dealer's first card
        
    Returns:
        PNG bytes
    """
    # Calculate dimensions
    max_cards = max(
        len(dealer_cards),
        max((len(p.get('cards', [])) for p in players), default=2)
    )
    img_width = max(SECTION_PADDING * 2 + max_cards * (CARD_WIDTH + CARD_SPACING), 350)
    img_height = SECTION_PADDING + HAND_ROW_HEIGHT * (1 + len(players)) + SECTION_PADDING
    
    # Create image
    img = Image.new("RGB", (img_width, img_height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Try to load a nice bold font
    font_large = _get_font(32)
    font_small = _get_font(14)
    font_label = _get_font(20)
    
    y_offset = SECTION_PADDING
    
    # === DEALER SECTION ===
    # draw.text((SECTION_PADDING, y_offset), "Nhà Cái", font=font_label, fill=TEXT_COLOR)
    # y_offset += 30
    
    x = SECTION_PADDING
    for i, card in enumerate(dealer_cards):
        # Handle both Card objects and legacy tuples
        if hasattr(card, 'rank') and hasattr(card, 'suit'):
            rank = card.rank.symbol
            suit = card.suit.value
        else:
            rank, suit = card # Fallback tuple ("A", "♠️")

        if i == 0 and hide_dealer:
            _draw_hidden_card(draw, x, y_offset)
        else:
            _draw_card(draw, x, y_offset, rank, suit, font_large, font_small)
        x += CARD_WIDTH + CARD_SPACING
    
    y_offset += CARD_HEIGHT + 20
    
    # === PLAYER SECTIONS ===
    for player in players:
        name = player.get('name', 'Player')
        cards = player.get('cards', [])
        
        # Label
        # label = name
        # draw.text((SECTION_PADDING, y_offset), label, font=font_label, fill=TEXT_COLOR)
        
        # y_offset += 30
        
        # Cards
        x = SECTION_PADDING
        for card_obj in cards:
            if hasattr(card_obj, 'rank') and hasattr(card_obj, 'suit'):
                rank = card_obj.rank.symbol
                suit = card_obj.suit.value
            else:
                rank, suit = card_obj # Fallback tuple

            _draw_card(draw, x, y_offset, rank, suit, font_large, font_small)
            x += CARD_WIDTH + CARD_SPACING
        
        y_offset += CARD_HEIGHT + 20
    
    # Save
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer.getvalue()


async def render_game_state(
    dealer_cards: List[Tuple[str, str]],
    players: List[Dict],
    hide_dealer: bool = True
) -> bytes:
    """Async wrapper for render_game_state_sync."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, render_game_state_sync, dealer_cards, players, hide_dealer
    )


from core.logger import setup_logger

logger = setup_logger("CardRenderer", "cogs/card_renderer.log")

def render_player_hand_sync(
    cards: List[Tuple[str, str]],
    player_name: str = "Người chơi"
) -> bytes:
    """Render a single player's hand with their name label.
    
    Args:
        cards: List of (rank, suit) tuples
        player_name: Name to display as label
        
    Returns:
        PNG bytes
    """
    try:
        logger.info(f"[RENDER_START] player={player_name} cards={len(cards)}")
        
        if not cards:
            img = Image.new("RGBA", (100, 50), (0, 0, 0, 0))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        
        # Calculate dimensions
        total_width = SECTION_PADDING * 2 + len(cards) * (CARD_WIDTH + CARD_SPACING)
        total_height = SECTION_PADDING + 20 + CARD_HEIGHT + SECTION_PADDING
        
        # Create image with Discord dark theme background
        img = Image.new("RGB", (total_width, total_height), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        font_large = _get_font(28)
        font_small = _get_font(12)
        font_label = _get_font(14)
        
        y_offset = SECTION_PADDING
        
        # Player name label
        label = player_name
        draw.text((SECTION_PADDING, y_offset), label, font=font_label, fill=TEXT_COLOR)
        y_offset += 20
        
        # Draw cards
        x = SECTION_PADDING
        for card_obj in cards:
            if hasattr(card_obj, 'rank') and hasattr(card_obj, 'suit'):
                rank = card_obj.rank.symbol
                suit = card_obj.suit.value
            else:
                rank, suit = card_obj # Fallback tuple
            
            _draw_card(draw, x, y_offset, rank, suit, font_large, font_small)
            x += CARD_WIDTH + CARD_SPACING
        
        # Save
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        
        result = buffer.getvalue()
        logger.info(f"[RENDER_SUCCESS] player={player_name} size={len(result)} bytes")
        return result
        
    except Exception as e:
        logger.error(f"[RENDER_ERROR] Failed to render hand for {player_name}: {e}", exc_info=True)
        # Return empty image on error to prevent crash
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "RENDER ERROR", fill=(255, 255, 255))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


async def render_player_hand(
    cards: List[Tuple[str, str]],
    player_name: str = "Người chơi"
) -> bytes:
    """Async render player hand with their name."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, render_player_hand_sync, cards, player_name)


# Backwards compatibility - these now just render cards without label
def render_hand_sync(cards: List[Tuple[str, str]], hide_first: bool = False) -> bytes:
    """Render single hand (backward compatibility)."""
    return render_player_hand_sync(cards, "Bài của bạn")


async def render_hand(cards: List[Tuple[str, str]], hide_first: bool = False) -> bytes:
    """Async render single hand (backward compatibility)."""
    return await render_player_hand(cards, "Bài của bạn")
