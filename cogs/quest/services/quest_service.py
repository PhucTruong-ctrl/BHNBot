import random
from datetime import date, datetime, timedelta
from typing import Optional
from dataclasses import dataclass
import pytz

from core.database import db_manager
from core.logging import get_logger
from ..core.quest_types import (
    QuestType, QuestDefinition, QUEST_DEFINITIONS, 
    DAILY_QUEST_COUNT, STREAK_BONUSES, ALL_QUEST_BONUS,
    EVENT_TO_SERVER_QUEST_MAP
)

logger = get_logger("QuestService")

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


@dataclass
class ServerQuest:
    id: int
    guild_id: int
    quest_date: date
    quest_type: QuestType
    target_value: int
    current_value: int
    reward_pool: int
    completed: bool

    @property
    def progress_percent(self) -> float:
        if self.target_value <= 0:
            return 100.0
        return min(100.0, (self.current_value / self.target_value) * 100)

    @property
    def definition(self) -> QuestDefinition:
        return QUEST_DEFINITIONS[self.quest_type]


@dataclass
class UserContribution:
    user_id: int
    guild_id: int
    quest_date: date
    quest_type: QuestType
    contribution: int
    reward_claimed: int


@dataclass
class ServerQuestStreak:
    guild_id: int
    current_streak: int
    longest_streak: int
    last_complete_date: Optional[date]

    @property
    def bonus_multiplier(self) -> float:
        for threshold, bonus in sorted(STREAK_BONUSES.items(), reverse=True):
            if self.current_streak >= threshold:
                return bonus
        return 0.0


class QuestService:

    @staticmethod
    async def ensure_tables() -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS server_daily_quests (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                quest_date DATE NOT NULL,
                quest_type VARCHAR(50) NOT NULL,
                target_value INT NOT NULL,
                current_value INT DEFAULT 0,
                reward_pool INT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                UNIQUE(guild_id, quest_date, quest_type)
            )
        """)
        
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS quest_contributions (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                quest_date DATE NOT NULL,
                quest_type VARCHAR(50) NOT NULL,
                contribution INT DEFAULT 0,
                reward_claimed INT DEFAULT 0,
                UNIQUE(guild_id, user_id, quest_date, quest_type)
            )
        """)
        
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS server_quest_streak (
                guild_id BIGINT PRIMARY KEY,
                current_streak INT DEFAULT 0,
                longest_streak INT DEFAULT 0,
                last_complete_date DATE
            )
        """)
        
        await db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_quest_contributions_date 
            ON quest_contributions(guild_id, quest_date)
        """)

    @staticmethod
    def _get_today_vn() -> date:
        return datetime.now(VN_TZ).date()

    @staticmethod
    async def generate_daily_quests(guild_id: int) -> list[ServerQuest]:
        await QuestService.ensure_tables()
        today = QuestService._get_today_vn()
        
        existing = await db_manager.fetchall(
            """SELECT id, guild_id, quest_date, quest_type, target_value, 
                      current_value, reward_pool, completed
               FROM server_daily_quests
               WHERE guild_id = $1 AND quest_date = $2""",
            (guild_id, today)
        )
        
        if existing:
            return [
                ServerQuest(
                    id=row[0], guild_id=row[1], quest_date=row[2],
                    quest_type=QuestType(row[3]), target_value=row[4],
                    current_value=row[5], reward_pool=row[6], completed=row[7]
                )
                for row in existing
            ]
        
        available_types = list(QUEST_DEFINITIONS.keys())
        
        # Filter out quest types that overlap with active event quests
        # This prevents duplicate quests (e.g., both server "Câu cá" and event "Câu 20 cá")
        # We prioritize non-overlapping types, but if not enough, include overlapping ones
        overlapping_types: set[QuestType] = set()
        try:
            from cogs.seasonal.services.event_service import get_active_event
            from cogs.seasonal.core.event_manager import get_event_manager
            
            active_event = await get_active_event(guild_id)
            if active_event:
                event_manager = get_event_manager()
                event_config = event_manager.get_event(active_event["event_id"])
                if event_config and event_config.daily_quests:
                    event_quest_types = {q.type for q in event_config.daily_quests}
                    for event_type, server_type in EVENT_TO_SERVER_QUEST_MAP.items():
                        if event_type in event_quest_types and server_type in available_types:
                            overlapping_types.add(server_type)
                            logger.info(f"Marked {server_type.value} as overlapping with event quest {event_type}")
        except ImportError:
            logger.warning("Could not import seasonal event services - skipping overlap filter")
        except Exception as e:
            logger.warning(f"Error checking active event for overlap filter: {e}")
        
        # Prioritize non-overlapping types, fill remaining with overlapping if needed
        non_overlapping = [qt for qt in available_types if qt not in overlapping_types]
        
        if len(non_overlapping) >= DAILY_QUEST_COUNT:
            selected_types = random.sample(non_overlapping, DAILY_QUEST_COUNT)
        else:
            selected_types = non_overlapping.copy()
            remaining_needed = DAILY_QUEST_COUNT - len(selected_types)
            overlapping_list = [qt for qt in available_types if qt in overlapping_types]
            selected_types.extend(random.sample(overlapping_list, min(remaining_needed, len(overlapping_list))))
            logger.info(f"Using {len(non_overlapping)} non-overlapping + {len(selected_types) - len(non_overlapping)} overlapping quest types")
        
        quests = []
        for qt in selected_types:
            definition = QUEST_DEFINITIONS[qt]
            await db_manager.execute(
                """INSERT INTO server_daily_quests 
                   (guild_id, quest_date, quest_type, target_value, reward_pool)
                   VALUES ($1, $2, $3, $4, $5)""",
                (guild_id, today, qt.value, definition.target_value, definition.reward_pool)
            )
        
        return await QuestService.get_today_quests(guild_id)

    @staticmethod
    async def get_today_quests(guild_id: int) -> list[ServerQuest]:
        today = QuestService._get_today_vn()
        
        rows = await db_manager.fetchall(
            """SELECT id, guild_id, quest_date, quest_type, target_value, 
                      current_value, reward_pool, completed
               FROM server_daily_quests
               WHERE guild_id = $1 AND quest_date = $2
               ORDER BY id""",
            (guild_id, today)
        )
        
        return [
            ServerQuest(
                id=row[0], guild_id=row[1], quest_date=row[2],
                quest_type=QuestType(row[3]), target_value=row[4],
                current_value=row[5], reward_pool=row[6], completed=row[7]
            )
            for row in rows
        ]

    @staticmethod
    async def add_contribution(
        guild_id: int, 
        user_id: int, 
        quest_type: QuestType, 
        amount: int = 1
    ) -> bool:
        await QuestService.ensure_tables()
        today = QuestService._get_today_vn()
        
        quest = await db_manager.fetchone(
            """SELECT id, completed FROM server_daily_quests
               WHERE guild_id = $1 AND quest_date = $2 AND quest_type = $3""",
            (guild_id, today, quest_type.value)
        )
        
        if not quest:
            return False
        
        if quest[1]:
            return False
        
        await db_manager.execute(
            """UPDATE server_daily_quests 
               SET current_value = current_value + $1
               WHERE guild_id = $2 AND quest_date = $3 AND quest_type = $4""",
            (amount, guild_id, today, quest_type.value)
        )
        
        await db_manager.execute(
            """INSERT INTO quest_contributions 
               (guild_id, user_id, quest_date, quest_type, contribution)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (guild_id, user_id, quest_date, quest_type) 
               DO UPDATE SET contribution = quest_contributions.contribution + $5""",
            (guild_id, user_id, today, quest_type.value, amount)
        )
        
        updated = await db_manager.fetchone(
            """SELECT current_value, target_value FROM server_daily_quests
               WHERE guild_id = $1 AND quest_date = $2 AND quest_type = $3""",
            (guild_id, today, quest_type.value)
        )
        
        if updated and updated[0] >= updated[1]:
            await db_manager.execute(
                """UPDATE server_daily_quests SET completed = TRUE
                   WHERE guild_id = $1 AND quest_date = $2 AND quest_type = $3""",
                (guild_id, today, quest_type.value)
            )
            logger.info(f"Quest {quest_type.value} completed for guild {guild_id}")
        
        return True

    @staticmethod
    async def get_top_contributors(
        guild_id: int, 
        quest_date: Optional[date] = None,
        limit: int = 10
    ) -> list[tuple[int, int]]:
        if quest_date is None:
            quest_date = QuestService._get_today_vn()
        
        rows = await db_manager.fetchall(
            """SELECT user_id, SUM(contribution) as total
               FROM quest_contributions
               WHERE guild_id = $1 AND quest_date = $2
               GROUP BY user_id
               ORDER BY total DESC
               LIMIT $3""",
            (guild_id, quest_date, limit)
        )
        
        return [(row[0], row[1]) for row in rows]

    @staticmethod
    async def get_streak(guild_id: int) -> ServerQuestStreak:
        row = await db_manager.fetchone(
            """SELECT guild_id, current_streak, longest_streak, last_complete_date
               FROM server_quest_streak WHERE guild_id = $1""",
            (guild_id,)
        )
        
        if row:
            return ServerQuestStreak(
                guild_id=row[0],
                current_streak=row[1] or 0,
                longest_streak=row[2] or 0,
                last_complete_date=row[3]
            )
        
        return ServerQuestStreak(
            guild_id=guild_id,
            current_streak=0,
            longest_streak=0,
            last_complete_date=None
        )

    @staticmethod
    async def update_streak(guild_id: int, quests_completed: int, total_quests: int) -> ServerQuestStreak:
        today = QuestService._get_today_vn()
        streak = await QuestService.get_streak(guild_id)
        
        if quests_completed >= 2:
            if streak.last_complete_date is None:
                new_streak = 1
            elif streak.last_complete_date == today - timedelta(days=1):
                new_streak = streak.current_streak + 1
            elif streak.last_complete_date == today:
                new_streak = streak.current_streak
            else:
                new_streak = 1
            
            new_longest = max(streak.longest_streak, new_streak)
            
            await db_manager.execute(
                """INSERT INTO server_quest_streak (guild_id, current_streak, longest_streak, last_complete_date)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (guild_id) DO UPDATE SET
                       current_streak = $2,
                       longest_streak = $3,
                       last_complete_date = $4""",
                (guild_id, new_streak, new_longest, today)
            )
            
            streak.current_streak = new_streak
            streak.longest_streak = new_longest
            streak.last_complete_date = today
        elif quests_completed <= 1 and streak.last_complete_date != today:
            await db_manager.execute(
                """UPDATE server_quest_streak SET current_streak = 0
                   WHERE guild_id = $1""",
                (guild_id,)
            )
            streak.current_streak = 0
        
        return streak

    @staticmethod
    async def calculate_rewards(guild_id: int) -> dict[int, int]:
        today = QuestService._get_today_vn()
        quests = await QuestService.get_today_quests(guild_id)
        
        if not quests:
            return {}
        
        completed_quests = [q for q in quests if q.completed]
        total_pool = sum(q.reward_pool for q in completed_quests)
        
        if len(completed_quests) == len(quests):
            total_pool += ALL_QUEST_BONUS
        
        streak = await QuestService.get_streak(guild_id)
        if streak.bonus_multiplier > 0:
            total_pool = int(total_pool * (1 + streak.bonus_multiplier))
        
        contributors = await QuestService.get_top_contributors(guild_id, today, limit=100)
        
        if not contributors:
            return {}
        
        total_contributions = sum(c[1] for c in contributors)
        if total_contributions <= 0:
            return {}
        
        rewards: dict[int, int] = {}
        for user_id, contribution in contributors:
            share = contribution / total_contributions
            reward = int(total_pool * share)
            if reward > 0:
                rewards[user_id] = reward
        
        return rewards

    @staticmethod
    async def distribute_rewards(guild_id: int) -> dict[int, int]:
        rewards = await QuestService.calculate_rewards(guild_id)
        
        if rewards:
            reward_data = [(amount, user_id, guild_id) for user_id, amount in rewards.items()]
            await db_manager.executemany(
                """UPDATE economy SET balance = balance + $1
                   WHERE user_id = $2 AND guild_id = $3""",
                reward_data
            )
        
        quests = await QuestService.get_today_quests(guild_id)
        completed_count = sum(1 for q in quests if q.completed)
        await QuestService.update_streak(guild_id, completed_count, len(quests))
        
        logger.info(f"Distributed rewards to {len(rewards)} users in guild {guild_id}")
        return rewards
