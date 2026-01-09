import os
import io
import asyncio
from functools import partial
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp

from ..core.themes import ThemeConfig, get_theme
from ..core.stats import ProfileStats


ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "profile")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

CARD_WIDTH = 900
CARD_HEIGHT = 350
AVATAR_SIZE = 180
AVATAR_X = 40
AVATAR_Y = 85

_executor = ThreadPoolExecutor(max_workers=4)


def _get_font(theme: ThemeConfig, size: int) -> ImageFont.FreeTypeFont:
    font_path = os.path.join(FONTS_DIR, theme.font)
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _create_circular_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(avatar, (0, 0), mask)

    return output


def _draw_progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int, y: int,
    width: int, height: int,
    progress: float,
    bg_color: tuple[int, int, int],
    fill_color: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle(
        [(x, y), (x + width, y + height)],
        radius=height // 2,
        fill=(*bg_color, 100)
    )

    fill_width = int(width * min(1.0, max(0.0, progress)))
    if fill_width > 0:
        draw.rounded_rectangle(
            [(x, y), (x + fill_width, y + height)],
            radius=height // 2,
            fill=(*fill_color, 255)
        )


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
        card = card.resize((CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)
    else:
        card = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (*theme.primary_color, 255))

    overlay = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 80))
    card = Image.alpha_composite(card, overlay)

    draw = ImageDraw.Draw(card)

    avatar = _create_circular_avatar(avatar_bytes, AVATAR_SIZE)

    border_size = AVATAR_SIZE + 8
    border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.ellipse((0, 0, border_size, border_size), fill=(*theme.accent_color, 255))
    card.paste(border, (AVATAR_X - 4, AVATAR_Y - 4), border)
    card.paste(avatar, (AVATAR_X, AVATAR_Y), avatar)

    font_large = _get_font(theme, 36)
    font_medium = _get_font(theme, 24)
    font_small = _get_font(theme, 18)

    info_x = AVATAR_X + AVATAR_SIZE + 40

    draw.text(
        (info_x, 60),
        username,
        font=font_large,
        fill=theme.text_color
    )

    rank_text = f"Hạng #{stats.rank} / {stats.total_users}"
    draw.text(
        (info_x, 105),
        rank_text,
        font=font_medium,
        fill=theme.accent_color
    )

    if bio:
        draw.text(
            (info_x, 140),
            f'"{bio}"',
            font=font_small,
            fill=(*theme.text_color[:3], 200)
        )

    if achievement_emojis:
        badges_text = " ".join(achievement_emojis[:4])
        draw.text(
            (info_x + 350, 65),
            badges_text,
            font=font_medium,
            fill=theme.text_color
        )

    stats_y = 200
    stat_items = [
        ("🌾", f"{stats.seeds:,}", "Hạt"),
        ("🐟", f"{stats.fish_caught:,}", "Cá"),
        ("🎤", f"{stats.voice_hours:.1f}h", "Voice"),
        ("💝", f"{stats.kindness_score:,}", "Tử Tế"),
        ("🔥", f"{stats.daily_streak}", "Streak"),
    ]

    stat_width = 150
    for i, (emoji, value, label) in enumerate(stat_items):
        x = info_x + (i * stat_width)

        draw.rounded_rectangle(
            [(x, stats_y), (x + 130, stats_y + 70)],
            radius=10,
            fill=(0, 0, 0, 100)
        )

        draw.text(
            (x + 10, stats_y + 8),
            emoji,
            font=font_medium,
            fill=theme.text_color
        )
        draw.text(
            (x + 45, stats_y + 10),
            value,
            font=font_medium,
            fill=theme.accent_color
        )
        draw.text(
            (x + 10, stats_y + 45),
            label,
            font=font_small,
            fill=(*theme.text_color[:3], 180)
        )

    draw.text(
        (CARD_WIDTH - 120, CARD_HEIGHT - 35),
        f"Theme: {theme.emoji}",
        font=font_small,
        fill=(*theme.text_color[:3], 150)
    )

    output = io.BytesIO()
    card.save(output, format="PNG", optimize=True)
    output.seek(0)
    return output.getvalue()


async def fetch_avatar(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
            raise ValueError(f"Failed to fetch avatar: {resp.status}")


async def render_profile(
    avatar_url: str,
    username: str,
    theme_key: str,
    stats: ProfileStats,
    bio: str,
    achievement_emojis: list[str],
) -> bytes:
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
