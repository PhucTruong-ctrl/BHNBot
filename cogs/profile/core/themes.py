from dataclasses import dataclass
from typing import Optional


@dataclass
class ThemeConfig:
    key: str
    name: str
    emoji: str
    font: str
    primary_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    text_color: tuple[int, int, int]
    bg_file: str
    vip_tier: int
    frame_file: Optional[str] = None


THEMES: dict[str, ThemeConfig] = {
    "forest": ThemeConfig(
        key="forest",
        name="Forest Sanctuary",
        emoji="🌲",
        font="Quicksand-Medium.ttf",
        primary_color=(45, 90, 39),
        accent_color=(139, 195, 74),
        text_color=(255, 255, 255),
        bg_file="bg_forest.png",
        vip_tier=0,
    ),
    "ocean": ThemeConfig(
        key="ocean",
        name="Ocean Depths",
        emoji="🌊",
        font="Comfortaa-Medium.ttf",
        primary_color=(26, 35, 126),
        accent_color=(77, 208, 225),
        text_color=(255, 255, 255),
        bg_file="bg_ocean.png",
        vip_tier=0,
    ),
    "starry": ThemeConfig(
        key="starry",
        name="Starry Night",
        emoji="🌙",
        font="Nunito-Medium.ttf",
        primary_color=(26, 26, 46),
        accent_color=(224, 176, 255),
        text_color=(255, 255, 255),
        bg_file="bg_starry.png",
        vip_tier=0,
    ),
    "cabin": ThemeConfig(
        key="cabin",
        name="Cozy Cabin",
        emoji="🏠",
        font="Caveat-Medium.ttf",
        primary_color=(93, 64, 55),
        accent_color=(255, 171, 145),
        text_color=(255, 255, 255),
        bg_file="bg_cabin.png",
        vip_tier=1,
    ),
    "sunrise": ThemeConfig(
        key="sunrise",
        name="Sunrise Meadow",
        emoji="🌅",
        font="Outfit-Medium.ttf",
        primary_color=(255, 111, 0),
        accent_color=(255, 213, 79),
        text_color=(255, 255, 255),
        bg_file="bg_sunrise.png",
        vip_tier=2,
    ),
}

DEFAULT_THEME = "forest"


def get_theme(key: str) -> ThemeConfig:
    return THEMES.get(key, THEMES[DEFAULT_THEME])


def get_available_themes(vip_tier: int = 0) -> list[ThemeConfig]:
    return [t for t in THEMES.values() if t.vip_tier <= vip_tier]


def get_theme_choices() -> list[tuple[str, str]]:
    result = []
    for theme in THEMES.values():
        vip_label = f" (VIP {theme.vip_tier})" if theme.vip_tier > 0 else ""
        label = f"{theme.emoji} {theme.name}{vip_label}"
        result.append((label, theme.key))
    return result
