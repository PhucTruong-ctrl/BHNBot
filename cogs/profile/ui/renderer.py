import os
import io
import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp

from ..core.themes import ThemeConfig, get_theme
from ..core.stats import ProfileStats


ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "profile")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
MAIN_FONT = "KK7-VCROSDMono.ttf"

CARD_WIDTH = 900
CARD_HEIGHT = 350
AVATAR_SIZE = 140
AVATAR_PADDING = 40
AVATAR_Y = 50

_executor = ThreadPoolExecutor(max_workers=4)


def _get_font(size: int) -> Any:
    font_path = os.path.join(FONTS_DIR, MAIN_FONT)
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _create_circular_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    """Create a circular avatar with high quality resampling."""
    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        avatar = Image.new("RGBA", (size, size), (100, 100, 100, 255))

    avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
    
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(avatar, (0, 0), mask)
    
    return output


def _draw_glass_panel(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, w: int, h: int,
    radius: int = 15,
    fill_color: tuple = (0, 0, 0, 60),
    border_color: tuple = (255, 255, 255, 30),
    border_width: int = 1
) -> None:
    """Draw a glassmorphism style rounded rectangle."""
    draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=radius,
        fill=fill_color,
        outline=None
    )
    if border_color:
        draw.rounded_rectangle(
            [(x, y), (x + w, y + h)],
            radius=radius,
            fill=None,
            outline=border_color,
            width=border_width
        )


def _draw_stat_box(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, w: int, h: int,
    label: str,
    value: str,
    font_val: Any,
    font_lbl: Any,
    theme: ThemeConfig
) -> None:
    """Draw a single statistic item inside a box."""
    cx = x + w / 2
    
    val_bbox = draw.textbbox((0, 0), value, font=font_val)
    val_w = val_bbox[2] - val_bbox[0]
    
    draw.text((cx - val_w / 2, y + 15), value, font=font_val, fill=theme.accent_color)
    
    lbl_bbox = draw.textbbox((0, 0), label.upper(), font=font_lbl)
    lbl_w = lbl_bbox[2] - lbl_bbox[0]
    
    draw.text((cx - lbl_w / 2, y + 55), label.upper(), font=font_lbl, fill=(200, 200, 200, 200))


def _render_profile_sync(
    avatar_bytes: bytes,
    username: str,
    theme: ThemeConfig,
    stats: ProfileStats,
    bio: str,
    achievement_emojis: list[str],
) -> bytes:
    bg_path = os.path.join(ASSETS_DIR, theme.bg_file)
    if os.path.exists(bg_path):
        card = Image.open(bg_path).convert("RGBA")
        bg_w, bg_h = card.size
        ratio = max(CARD_WIDTH / bg_w, CARD_HEIGHT / bg_h)
        new_size = (int(bg_w * ratio), int(bg_h * ratio))
        card = card.resize(new_size, Image.Resampling.LANCZOS)
        
        left = (new_size[0] - CARD_WIDTH) // 2
        top = (new_size[1] - CARD_HEIGHT) // 2
        card = card.crop((left, top, left + CARD_WIDTH, top + CARD_HEIGHT))
    else:
        card = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (*theme.primary_color, 255))

    overlay = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(overlay)
    
    for x in range(CARD_WIDTH):
        alpha = int(220 - (x / CARD_WIDTH) * 120)
        gradient_draw.line([(x, 0), (x, CARD_HEIGHT)], fill=(0, 0, 0, alpha))
        
    card = Image.alpha_composite(card, overlay)
    draw = ImageDraw.Draw(card)

    glow_center_x = AVATAR_PADDING + AVATAR_SIZE // 2
    glow_center_y = AVATAR_Y + AVATAR_SIZE // 2
    
    for i in range(3):
        glow_radius = (AVATAR_SIZE // 2) + 15 - (i * 5)
        glow_alpha = 40 + (i * 30)
        draw.ellipse(
            (glow_center_x - glow_radius, glow_center_y - glow_radius, 
             glow_center_x + glow_radius, glow_center_y + glow_radius),
            fill=(*theme.accent_color, glow_alpha)
        )

    avatar = _create_circular_avatar(avatar_bytes, AVATAR_SIZE)
    card.paste(avatar, (AVATAR_PADDING, AVATAR_Y), avatar)
    
    draw.ellipse(
        (AVATAR_PADDING, AVATAR_Y, AVATAR_PADDING + AVATAR_SIZE, AVATAR_Y + AVATAR_SIZE),
        outline=(*theme.accent_color, 255), width=3
    )

    info_x = AVATAR_PADDING + AVATAR_SIZE + 40
    current_y = 55

    font_name = _get_font(48)
    font_rank = _get_font(20)
    font_bio = _get_font(18)
    font_stat_val = _get_font(28)
    font_stat_lbl = _get_font(14)

    draw.text((info_x, current_y), username, font=font_name, fill=theme.text_color)
    current_y += 65

    rank_text = f"Hạng #{stats.rank} trong {stats.total_users} người"
    rank_bbox = draw.textbbox((0, 0), rank_text, font=font_rank)
    rank_w = int(rank_bbox[2] - rank_bbox[0] + 30)
    rank_h = 32
    
    _draw_glass_panel(
        draw, info_x, current_y, rank_w, rank_h, 
        radius=16, 
        fill_color=(*theme.primary_color, 150),
        border_color=theme.accent_color
    )
    
    draw.text(
        (info_x + 15, current_y + 3), 
        rank_text, 
        font=font_rank, 
        fill=(255, 255, 255, 230)
    )
    current_y += 50

    if bio:
        bio_text = (bio[:75] + '...') if len(bio) > 75 else bio
        draw.text(
            (info_x, current_y),
            f'"{bio_text}"',
            font=font_bio,
            fill=(220, 220, 220, 180)
        )

    panel_h = 90
    panel_y = CARD_HEIGHT - panel_h - 25
    panel_x = AVATAR_PADDING
    panel_w = CARD_WIDTH - (AVATAR_PADDING * 2)

    _draw_glass_panel(
        draw, panel_x, panel_y, panel_w, panel_h,
        radius=15,
        fill_color=(0, 0, 0, 80),
        border_color=(255, 255, 255, 20)
    )

    stat_items = [
        ("Hạt giống", f"{stats.seeds:,}"),
        ("Cá", f"{stats.fish_caught:,}"),
        ("Giờ nói", f"{stats.voice_hours:.1f}h"),
        ("Tử tế", f"{stats.kindness_score:,}"),
        ("Chuỗi ngày", f"{stats.daily_streak}"),
    ]
    
    item_w = int(panel_w / len(stat_items))
    
    for i, (label, value) in enumerate(stat_items):
        item_x = int(panel_x + (i * item_w))
        _draw_stat_box(
            draw, item_x, panel_y, int(item_w), panel_h,
            label, value, font_stat_val, font_stat_lbl, theme
        )
        
        if i < len(stat_items) - 1:
            sep_x = int(item_x + item_w)
            draw.line(
                [(sep_x, panel_y + 20), (sep_x, panel_y + panel_h - 20)],
                fill=(255, 255, 255, 30),
                width=1
            )

    output = io.BytesIO()
    card.save(output, format="PNG", optimize=True)
    output.seek(0)
    return output.getvalue()


async def fetch_avatar(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                return b""
        except:
            return b""


async def render_profile(
    avatar_url: str,
    username: str,
    theme_key: str,
    stats: ProfileStats,
    bio: str,
    achievement_emojis: list[str],
) -> bytes:
    """
    Render profile card with premium design.
    Run strict IO/CPU intensive tasks in executor.
    """
    avatar_bytes = await fetch_avatar(avatar_url)
    theme = get_theme(theme_key)

    loop = asyncio.get_event_loop()
    render_func = partial(
        _render_profile_sync,
        avatar_bytes,
        username,
        theme,
        stats,
        bio,
        achievement_emojis,
    )
    result = await loop.run_in_executor(_executor, render_func)
    return result
