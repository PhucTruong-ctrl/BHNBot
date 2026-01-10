from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any


class QuestType(Enum):
    FISH_TOTAL = "fish_total"
    VOICE_TOTAL = "voice_total"
    GIFT_TOTAL = "gift_total"
    REACT_TOTAL = "react_total"
    TREE_WATER = "tree_water"
    THANK_TOTAL = "thank_total"


@dataclass
class QuestDefinition:
    quest_type: QuestType
    name_vi: str
    description_vi: str
    target_value: int
    reward_pool: int
    icon: str


QUEST_DEFINITIONS: dict[QuestType, QuestDefinition] = {
    QuestType.FISH_TOTAL: QuestDefinition(
        quest_type=QuestType.FISH_TOTAL,
        name_vi="Câu cá",
        description_vi="Cả server câu {target} con cá",
        target_value=50,
        reward_pool=100,
        icon="🎣"
    ),
    QuestType.VOICE_TOTAL: QuestDefinition(
        quest_type=QuestType.VOICE_TOTAL,
        name_vi="Voice chat",
        description_vi="Cả server voice tổng {target} phút",
        target_value=120,
        reward_pool=100,
        icon="🎤"
    ),
    QuestType.GIFT_TOTAL: QuestDefinition(
        quest_type=QuestType.GIFT_TOTAL,
        name_vi="Tặng quà",
        description_vi="Cả server tặng {target} món quà",
        target_value=5,
        reward_pool=75,
        icon="🎁"
    ),
    QuestType.REACT_TOTAL: QuestDefinition(
        quest_type=QuestType.REACT_TOTAL,
        name_vi="Thả tim",
        description_vi="Cả server thả {target} reactions ❤️",
        target_value=30,
        reward_pool=50,
        icon="❤️"
    ),
    QuestType.TREE_WATER: QuestDefinition(
        quest_type=QuestType.TREE_WATER,
        name_vi="Tưới cây",
        description_vi="Cả server tưới cây {target} lần",
        target_value=10,
        reward_pool=50,
        icon="🌳"
    ),
    QuestType.THANK_TOTAL: QuestDefinition(
        quest_type=QuestType.THANK_TOTAL,
        name_vi="Cảm ơn",
        description_vi="Cả server cảm ơn {target} lần",
        target_value=10,
        reward_pool=50,
        icon="🙏"
    ),
}

DAILY_QUEST_COUNT = 3

STREAK_BONUSES = {
    3: 0.10,
    7: 0.25,
    14: 0.50,
    30: 1.00,
}

ALL_QUEST_BONUS = 50
