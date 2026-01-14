"""
Seasonal Events - Core Type Definitions

JSON-driven event configuration dataclasses.
All event data is loaded from data/events/*.json files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Path to event data files
EVENTS_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "events"


@dataclass
class CurrencyConfig:
    """Event currency configuration."""

    emoji: str
    name: str
    name_en: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CurrencyConfig:
        return cls(
            emoji=data["emoji"],
            name=data["name"],
            name_en=data.get("name_en", ""),
        )


@dataclass
class CommunityGoalConfig:
    """Community goal configuration."""

    type: str  # currency_collected, treasure_found, letters_sent, etc.
    target: int
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommunityGoalConfig:
        return cls(
            type=data["type"],
            target=data["target"],
            description=data.get("description", ""),
        )


@dataclass
class MilestoneConfig:
    """Milestone reward configuration."""

    percent: int
    reward_type: str  # seeds, title, buff, role, multi
    amount: int | None = None
    title_key: str | None = None
    title_name: str | None = None
    buff_type: str | None = None
    duration_hours: int | None = None
    role_name: str | None = None
    role_color: str | None = None
    extra_rewards: list[dict[str, Any]] = field(default_factory=list)
    announcement: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MilestoneConfig:
        return cls(
            percent=data["percent"],
            reward_type=data["reward_type"],
            amount=data.get("amount"),
            title_key=data.get("title_key"),
            title_name=data.get("title_name"),
            buff_type=data.get("buff_type"),
            duration_hours=data.get("duration_hours"),
            role_name=data.get("role_name"),
            role_color=data.get("role_color"),
            extra_rewards=data.get("extra_rewards", []),
            announcement=data.get("announcement", ""),
        )


@dataclass
class EventFishConfig:
    """Event fish configuration."""

    key: str
    name: str
    emoji: str
    tier: str  # common, rare, epic
    drop_rate: float
    currency_reward: int
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventFishConfig:
        return cls(
            key=data["key"],
            name=data["name"],
            emoji=data["emoji"],
            tier=data["tier"],
            drop_rate=data["drop_rate"],
            currency_reward=data["currency_reward"],
            description=data.get("description", ""),
        )


@dataclass
class QuestConfig:
    """Quest configuration (daily or fixed)."""

    id: str
    type: str  # fish_count, lixi_sent, message_count, etc.
    target: int
    description: str
    icon: str = ""
    # For daily quests
    reward: int = 0
    # For fixed quests
    reward_type: str | None = None  # currency, title, badge
    reward_value: str | int | None = None
    title_key: str | None = None
    fish_key: str | None = None  # For catch_specific_fish type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestConfig:
        return cls(
            id=data["id"],
            type=data["type"],
            target=data["target"],
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            reward=data.get("reward", 0),
            reward_type=data.get("reward_type"),
            reward_value=data.get("reward_value"),
            title_key=data.get("title_key"),
            fish_key=data.get("fish_key"),
        )


@dataclass
class ShopItemConfig:
    """Shop item configuration."""

    key: str
    name: str
    price: int
    type: str  # background, frame, consumable, badge, gift, cosmetic, etc.
    limit_per_user: int = 1  # -1 for unlimited
    description: str = ""
    effect: dict[str, Any] | None = None
    tier: int | None = None  # For secret santa gifts

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShopItemConfig:
        return cls(
            key=data["key"],
            name=data["name"],
            price=data["price"],
            type=data["type"],
            limit_per_user=data.get("limit_per_user", 1),
            description=data.get("description", ""),
            effect=data.get("effect"),
            tier=data.get("tier"),
        )


@dataclass
class EventRegistryEntry:
    event_id: str
    name: str
    name_en: str
    type: str
    start_date: datetime
    end_date: datetime
    currency: CurrencyConfig
    color: str
    config_file: str
    minigames: list[str]
    community_goal: CommunityGoalConfig
    special_buffs: dict[str, Any] = field(default_factory=dict)
    banner_image: str = ""
    thumbnail: str = ""
    description: str = ""
    guide: str = ""

    @classmethod
    def from_dict(cls, event_id: str, data: dict[str, Any]) -> EventRegistryEntry:
        return cls(
            event_id=event_id,
            name=data["name"],
            name_en=data.get("name_en", ""),
            type=data["type"],
            start_date=datetime.strptime(data["start_date"], "%Y-%m-%d"),
            end_date=datetime.strptime(data["end_date"], "%Y-%m-%d"),
            currency=CurrencyConfig.from_dict(data["currency"]),
            color=data["color"],
            config_file=data["config_file"],
            minigames=data.get("minigames", []),
            community_goal=CommunityGoalConfig.from_dict(data["community_goal"]),
            special_buffs=data.get("special_buffs", {}),
            banner_image=data.get("banner_image", ""),
            thumbnail=data.get("thumbnail", ""),
            description=data.get("description", ""),
            guide=data.get("guide", ""),
        )

    def is_active(self, now: datetime | None = None) -> bool:
        """Check if event is currently active based on date."""
        if now is None:
            now = datetime.now()
        return self.start_date <= now <= self.end_date

    @property
    def color_int(self) -> int:
        """Return color as integer for Discord embeds."""
        return int(self.color.lstrip("#"), 16)


@dataclass
class EventConfig:
    """Full event configuration loaded from JSON file."""

    # From registry
    registry: EventRegistryEntry

    # From event-specific JSON
    milestones: list[MilestoneConfig] = field(default_factory=list)
    fish: list[EventFishConfig] = field(default_factory=list)
    daily_quests: list[QuestConfig] = field(default_factory=list)
    daily_quest_count: int = 3
    fixed_quests: list[QuestConfig] = field(default_factory=list)
    shop: list[ShopItemConfig] = field(default_factory=list)
    minigame_config: dict[str, Any] = field(default_factory=dict)
    special_days: dict[str, Any] = field(default_factory=dict)
    currency_sources: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, registry_entry: EventRegistryEntry) -> EventConfig:
        """Load full event config from registry entry."""
        config_path = EVENTS_DATA_PATH / registry_entry.config_file

        if not config_path.exists():
            # Return config with just registry data if file doesn't exist
            return cls(registry=registry_entry)

        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            registry=registry_entry,
            milestones=[MilestoneConfig.from_dict(m) for m in data.get("milestones", [])],
            fish=[EventFishConfig.from_dict(f) for f in data.get("fish", [])],
            daily_quests=[QuestConfig.from_dict(q) for q in data.get("daily_quests", [])],
            daily_quest_count=data.get("daily_quest_count", 3),
            fixed_quests=[QuestConfig.from_dict(q) for q in data.get("fixed_quests", [])],
            shop=[ShopItemConfig.from_dict(s) for s in data.get("shop", [])],
            minigame_config=data.get("minigame_config", {}),
            special_days=data.get("special_days", {}),
            currency_sources=data.get("currency_sources", {}),
        )

    # Convenience properties
    @property
    def event_id(self) -> str:
        return self.registry.event_id

    @property
    def name(self) -> str:
        return self.registry.name

    @property
    def currency_emoji(self) -> str:
        return self.registry.currency.emoji

    @property
    def currency_name(self) -> str:
        return self.registry.currency.name

    @property
    def color(self) -> int:
        return self.registry.color_int

    @property
    def community_goal_target(self) -> int:
        return self.registry.community_goal.target

    @property
    def banner_image(self) -> str:
        return self.registry.banner_image

    @property
    def thumbnail(self) -> str:
        return self.registry.thumbnail

    @property
    def description(self) -> str:
        return self.registry.description

    @property
    def guide(self) -> str:
        return self.registry.guide

    @property
    def community_goal_description(self) -> str:
        return self.registry.community_goal.description

    @property
    def minigames(self) -> list[str]:
        return self.registry.minigames

    def get_fish_by_key(self, key: str) -> EventFishConfig | None:
        """Get fish config by key."""
        for fish in self.fish:
            if fish.key == key:
                return fish
        return None

    def get_shop_item(self, key: str) -> ShopItemConfig | None:
        """Get shop item by key."""
        for item in self.shop:
            if item.key == key:
                return item
        return None

    def get_milestone(self, percent: int) -> MilestoneConfig | None:
        """Get milestone config by percent."""
        for milestone in self.milestones:
            if milestone.percent == percent:
                return milestone
        return None


def load_registry() -> dict[str, EventRegistryEntry]:
    """Load all events from registry.json."""
    registry_path = EVENTS_DATA_PATH / "registry.json"

    if not registry_path.exists():
        return {}

    with open(registry_path, encoding="utf-8") as f:
        data = json.load(f)

    events = {}
    for event_id, event_data in data.get("events", {}).items():
        events[event_id] = EventRegistryEntry.from_dict(event_id, event_data)

    return events


def get_registry_settings() -> dict[str, Any]:
    """Get global settings from registry.json."""
    registry_path = EVENTS_DATA_PATH / "registry.json"

    if not registry_path.exists():
        return {}

    with open(registry_path, encoding="utf-8") as f:
        data = json.load(f)

    return data.get("settings", {})
