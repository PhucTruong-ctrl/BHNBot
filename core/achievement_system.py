"""
Centralized Achievement System
Quản lý tất cả thành tựu của bot một cách tập trung và hướng sự kiện.
"""

import json
import discord
from pathlib import Path
from database_manager import db_manager, add_seeds
from core.logging import get_logger

logger = get_logger("achievement")

ACHIEVEMENT_DATA = {}
try:
    with open("./data/achievements.json", "r", encoding="utf-8") as f:
        ACHIEVEMENT_DATA = json.load(f)
except FileNotFoundError:
    logger.warning("achievements_config_missing", file="achievements.json")
except Exception as e:
    logger.error("achievements_config_load_failed", error=str(e))

# Load seasonal achievement config from all event files
SEASONAL_ACHIEVEMENT_DATA = {}  # {event_id: {achievement_key: achievement_data}}
def load_seasonal_achievements():
    """Load achievements from all event JSON files."""
    global SEASONAL_ACHIEVEMENT_DATA
    SEASONAL_ACHIEVEMENT_DATA = {}
    events_dir = Path("./data/events")
    
    if not events_dir.exists():
        logger.warning("seasonal_achievements_dir_missing", path="data/events")
        return
    
    for event_file in events_dir.glob("*.json"):
        if event_file.name == "registry.json":
            continue
        try:
            with open(event_file, "r", encoding="utf-8") as f:
                event_data = json.load(f)
            
            if "achievements" in event_data:
                event_id = event_data.get("event_id", event_file.stem)
                SEASONAL_ACHIEVEMENT_DATA[event_id] = event_data["achievements"]
                logger.info("seasonal_achievements_loaded", count=len(event_data['achievements']), file=event_file.name)
        except Exception as e:
            logger.error("seasonal_achievements_load_failed", file=event_file.name, error=str(e))

# Load seasonal achievements at startup
load_seasonal_achievements()

SERVER_CONFIG = {}
try:
    with open("./configs/server_config.json", "r", encoding="utf-8") as f:
        SERVER_CONFIG = json.load(f)
except FileNotFoundError:
    logger.warning("server_config_missing", file="server_config.json")
except Exception as e:
    logger.error("server_config_load_failed", error=str(e))

class AchievementManager:
    """
    Centralized achievement management system.
    Handles checking, unlocking, and notifying achievements across all games.
    """

    def __init__(self, bot):
        self.bot = bot

    async def check_unlock(self, user_id: int, game_category: str, stat_key: str, current_value: int, channel: discord.TextChannel = None):
        """
        Check if any achievements should be unlocked based on stat update.

        Args:
            user_id: Discord user ID
            game_category: 'fishing', 'werewolf', 'noitu', etc.
            stat_key: The stat that was updated (e.g., 'total_fish_caught', 'wolf_wins')
            current_value: Current value of the stat
            channel: Discord channel to send notification (important for UX)
        """
        if not ACHIEVEMENT_DATA:
            return  # Achievement system disabled

        # Get achievements for this game category
        game_achievements = ACHIEVEMENT_DATA.get(game_category, {})

        for achievement_key, achievement_data in game_achievements.items():
            # Only check achievements that match this stat
            if achievement_data.get("condition_stat") != stat_key:
                continue

            # Check if condition is met
            target_value = achievement_data.get("target_value", 0)
            if current_value >= target_value:
                # Check if already unlocked (prevent spam)
                if await self.is_unlocked(user_id, achievement_key):
                    continue

                # UNLOCK ACHIEVEMENT!
                await self.unlock_achievement(user_id, achievement_key, achievement_data, channel)

    async def check_seasonal_unlock(
        self, 
        user_id: int, 
        event_id: str, 
        condition_type: str, 
        condition_key: str = None, 
        current_value: int = 1, 
        channel: discord.TextChannel = None
    ):
        """
        Check if any seasonal achievements should be unlocked.
        
        Args:
            user_id: Discord user ID
            event_id: Event identifier (e.g., 'spring_2026')
            condition_type: Type of condition ('catch_specific_fish', 'collect_all', 'community_goal', etc.)
            condition_key: Specific item key for 'catch_specific_fish' type
            current_value: Current progress value
            channel: Discord channel to send notification
        """
        if not SEASONAL_ACHIEVEMENT_DATA:
            return
        
        event_achievements = SEASONAL_ACHIEVEMENT_DATA.get(event_id, {})
        if not event_achievements:
            return
        
        for achievement_key, achievement_data in event_achievements.items():
            if achievement_data.get("condition_type") != condition_type:
                continue
            
            # For specific item achievements, check condition_key matches
            if condition_type == "catch_specific_fish":
                if achievement_data.get("condition_key") != condition_key:
                    continue
            
            target_value = achievement_data.get("target_value", 1)
            if current_value >= target_value:
                if await self.is_unlocked(user_id, achievement_key):
                    continue
                
                await self.unlock_achievement(user_id, achievement_key, achievement_data, channel)

    async def is_unlocked(self, user_id: int, achievement_key: str) -> bool:
        """Check if user has already unlocked this achievement."""
        try:
            row = await db_manager.fetchone(
                "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_key = ?",
                (user_id, achievement_key)
            )
            unlocked = bool(row)
            if unlocked:
                logger.debug("achievement_already_unlocked", user_id=user_id, achievement_key=achievement_key)
            return unlocked
        except Exception as e:
            logger.error("achievement_unlock_check_failed", achievement_key=achievement_key, error=str(e))
            return True  # Assume unlocked to prevent spam if DB error

    async def unlock_achievement(self, user_id: int, achievement_key: str, achievement_data: dict, channel: discord.TextChannel = None):
        """Unlock an achievement and send notification."""
        try:
            # Double-check if already unlocked (prevent race conditions)
            if await self.is_unlocked(user_id, achievement_key):
                logger.debug("achievement_skip_already_unlocked", achievement_key=achievement_key, user_id=user_id)
                return

            # 1. Save to database
            try:
                await db_manager.modify(
                    "INSERT INTO user_achievements (user_id, achievement_key) VALUES (?, ?) ON CONFLICT (user_id, achievement_key) DO NOTHING",
                    (user_id, achievement_key)
                )
                logger.info("achievement_inserted", achievement_key=achievement_key, user_id=user_id)
            except Exception as e:
                logger.error("achievement_insert_failed", achievement_key=achievement_key, user_id=user_id, error=str(e))
                return  # Don't proceed if can't save to DB

            # 2. Give reward
            reward_seeds = achievement_data.get("reward_seeds", 0)
            if reward_seeds > 0:
                await add_seeds(user_id, reward_seeds, 'achievement_reward', 'system')

            # 3. Give role reward if configured
            role_assigned = False
            reward_role_key = achievement_data.get("reward_role_key")
            if reward_role_key and SERVER_CONFIG:
                role_assigned = await self._assign_role_reward(user_id, reward_role_key, channel)

            # 4. Send notification in the game channel
            await self._send_unlock_notification(user_id, achievement_key, achievement_data, channel, role_assigned)

            logger.info("achievement_unlocked", achievement_key=achievement_key, user_id=user_id, reward_seeds=reward_seeds, role_assigned=role_assigned)

        except Exception as e:
            logger.error("achievement_unlock_failed", achievement_key=achievement_key, user_id=user_id, error=str(e))

    async def _assign_role_reward(self, user_id: int, role_key: str, channel: discord.TextChannel = None) -> bool:
        """Assign role reward to user if role exists in server config."""
        try:
            if not channel or not channel.guild:
                return False

            # Get role ID from server config
            default_server = SERVER_CONFIG.get("default_server", {})
            role_id = default_server.get(role_key)

            if not role_id:
                logger.warning("role_key_not_found", role_key=role_key)
                return False

            # Get the role object
            role = channel.guild.get_role(role_id)
            if not role:
                logger.warning("role_not_found", role_id=role_id, guild_id=channel.guild.id)
                return False

            # Get the member
            member = channel.guild.get_member(user_id)
            if not member:
                logger.warning("member_not_found", user_id=user_id, guild_id=channel.guild.id)
                return False

            # Check if member already has the role
            if role in member.roles:
                logger.debug("member_already_has_role", user_id=user_id, role_name=role.name)
                return True  # Consider it successful since they have the role

            # Assign the role
            await member.add_roles(role)
            logger.info("role_assigned", role_name=role.name, user_id=user_id)
            return True

        except Exception as e:
            logger.error("role_assign_failed", role_key=role_key, user_id=user_id, error=str(e))
            return False

    async def _send_unlock_notification(self, user_id: int, achievement_key: str, achievement_data: dict, channel: discord.TextChannel = None, role_assigned: bool = False):
        """Send achievement unlock notification to Discord channel."""
        if not channel:
            return  # No channel specified, skip notification

        try:
            # Get user display name
            member = channel.guild.get_member(user_id) if channel.guild else None
            display_name = member.display_name if member else f"<@{user_id}>"

            embed = discord.Embed(
                title=f"🏆 THÀNH TỰU MỚI: {achievement_data['name']}",
                description=f"Chúc mừng **{display_name}** đã đạt mốc:\n**{achievement_data['description']}**",
                color=discord.Color.gold()
            )

            # Add trophy image
            embed.set_thumbnail(url="https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3djV0aWw2ZGgwa2p4aGgxZnk2dXg1amp0NDF4N3FoM3A3ejV0b3A3YSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/IX96Ceg5hiMNBn7Ls7/giphy.gif")

            # Add reward info
            reward_seeds = achievement_data.get("reward_seeds", 0)
            reward_fields = []

            if reward_seeds > 0:
                reward_fields.append(f"💰 +{reward_seeds} Hạt 🌰")

            if role_assigned:
                reward_fields.append("👑 Vai trò mới!")

            if reward_fields:
                embed.add_field(name="🎁 Phần thưởng", value="\n".join(reward_fields), inline=True)

            if channel.guild:
                total_members = channel.guild.member_count or 1
                count_row = await db_manager.fetchone(
                    "SELECT COUNT(DISTINCT user_id) FROM user_achievements WHERE achievement_key = ?",
                    (achievement_key,)
                )
                earned_count = count_row[0] if count_row else 1
                rarity_pct = (earned_count / total_members) * 100
                
                embed.add_field(
                    name="🌍 Độ hiếm", 
                    value=f"**{rarity_pct:.1f}%** người chơi đã đạt được", 
                    inline=True
                )

            # Add emoji footer
            emoji = achievement_data.get("emoji", "🎮")
            embed.set_footer(text=f"Game Achievement {emoji}")

            # Send the message
            await channel.send(content=f"👏 Chúc mừng <@{user_id}>!", embed=embed)

        except Exception as e:
            logger.error("notification_failed", achievement_key=achievement_key, error=str(e))

    async def get_user_achievements(self, user_id: int, game_category: str = None) -> list:
        """Get list of unlocked achievements for a user."""
        try:
            if game_category:
                # Get achievements for specific game
                query = """
                    SELECT ua.achievement_key, ua.unlocked_at, ad.name, ad.description, ad.emoji
                    FROM user_achievements ua
                    JOIN achievements_data ad ON ua.achievement_key = ad.key
                    WHERE ua.user_id = ? AND ad.game_category = ?
                    ORDER BY ua.unlocked_at DESC
                """
                rows = await db_manager.execute(query, (user_id, game_category))
            else:
                # Get all achievements
                query = """
                    SELECT ua.achievement_key, ua.unlocked_at, ad.name, ad.description, ad.emoji, ad.game_category
                    FROM user_achievements ua
                    JOIN achievements_data ad ON ua.achievement_key = ad.key
                    WHERE ua.user_id = ?
                    ORDER BY ua.unlocked_at DESC
                """
                rows = await db_manager.execute(query, (user_id,))

            return rows or []
        except Exception as e:
            logger.error("get_achievements_failed", user_id=user_id, error=str(e))
            return []

    async def get_achievement_progress(self, user_id: int, game_category: str, stat_key: str) -> dict:
        """Get progress towards achievements for a specific stat."""
        if not ACHIEVEMENT_DATA:
            return {}

        game_achievements = ACHIEVEMENT_DATA.get(game_category, {})
        progress = {}

        for achievement_key, achievement_data in game_achievements.items():
            if achievement_data.get("condition_stat") == stat_key:
                target = achievement_data.get("target_value", 0)
                unlocked = await self.is_unlocked(user_id, achievement_key)
                progress[achievement_key] = {
                    "name": achievement_data.get("name"),
                    "description": achievement_data.get("description"),
                    "target": target,
                    "unlocked": unlocked,
                    "reward_seeds": achievement_data.get("reward_seeds", 0)
                }

        return progress