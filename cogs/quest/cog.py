import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time
import pytz

from .services.quest_service import QuestService
from .core.quest_types import QuestType, QUEST_DEFINITIONS, ALL_QUEST_BONUS
from core.database import db_manager
from core.logger import setup_logger
from cogs.seasonal.services import get_active_event, get_all_user_quests
from cogs.seasonal.core.event_manager import get_event_manager

logger = setup_logger("QuestCog", "cogs/quest.log")

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
MORNING_HOUR = 7
EVENING_HOUR = 22


class QuestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._quest_channels: dict[int, int] = {}

    async def cog_load(self) -> None:
        await QuestService.ensure_tables()
        await self._load_quest_channels()
        self.morning_announcement.start()
        self.evening_summary.start()
        logger.info("QuestCog loaded - Daily quests system active")

    async def cog_unload(self) -> None:
        self.morning_announcement.cancel()
        self.evening_summary.cancel()

    async def _load_quest_channels(self) -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS quest_config (
                guild_id BIGINT PRIMARY KEY,
                announcement_channel_id BIGINT,
                enabled BOOLEAN DEFAULT TRUE
            )
        """)
        
        rows = await db_manager.fetchall(
            "SELECT guild_id, announcement_channel_id FROM quest_config WHERE enabled = TRUE"
        )
        self._quest_channels = {row[0]: row[1] for row in rows if row[1]}

    async def set_quest_channel(self, guild_id: int, channel_id: int) -> None:
        await db_manager.execute(
            """INSERT INTO quest_config (guild_id, announcement_channel_id, enabled)
               VALUES ($1, $2, TRUE)
               ON CONFLICT (guild_id) DO UPDATE SET
                   announcement_channel_id = $2, enabled = TRUE""",
            (guild_id, channel_id)
        )
        self._quest_channels[guild_id] = channel_id

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=VN_TZ))
    async def morning_announcement(self) -> None:
        now = datetime.now(VN_TZ)
        if now.hour != MORNING_HOUR:
            return
        
        for guild_id, channel_id in self._quest_channels.items():
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                
                quests = await QuestService.generate_daily_quests(guild_id)
                streak = await QuestService.get_streak(guild_id)
                
                embed = discord.Embed(
                    title="🎯 NHIỆM VỤ NGÀY " + now.strftime("%d/%m/%Y"),
                    color=0x00FF88
                )
                
                quest_lines = []
                for i, quest in enumerate(quests, 1):
                    defn = quest.definition
                    desc = defn.description_vi.format(target=quest.target_value)
                    quest_lines.append(
                        f"{defn.icon} **{i}. {defn.name_vi}**\n"
                        f"   {desc} → {quest.reward_pool} Hạt"
                    )
                
                embed.description = "\n\n".join(quest_lines)
                
                bonus_text = f"🎁 Bonus hoàn thành cả 3: **+{ALL_QUEST_BONUS} Hạt**"
                if streak.current_streak > 0:
                    bonus_text += f"\n🔥 Server streak: **{streak.current_streak}** ngày (+{int(streak.bonus_multiplier*100)}%)"
                
                embed.add_field(name="💰 Phần Thưởng", value=bonus_text, inline=False)
                embed.set_footer(text="Kết quả sẽ được công bố lúc 22:00")
                
                active_event = await get_active_event(guild_id)
                if active_event:
                    event_id = active_event.get("event_id")
                    if event_id:
                        event_manager = get_event_manager()
                        event_config = event_manager.get_event(event_id)
                        if event_config and event_config.daily_quests:
                            embed.add_field(
                                name=f"🎊 Sự Kiện: {event_config.name}",
                                value=f"Có **{len(event_config.daily_quests[:event_config.daily_quest_count])}** nhiệm vụ sự kiện!\nDùng `/nhiemvu` để xem chi tiết.",
                                inline=False
                            )
                
                await channel.send(embed=embed)
                logger.info(f"Morning announcement sent to guild {guild_id}")
                
            except Exception as e:
                logger.error(f"Failed morning announcement for guild {guild_id}: {e}")

    @tasks.loop(time=time(hour=15, minute=0, tzinfo=VN_TZ))
    async def evening_summary(self) -> None:
        now = datetime.now(VN_TZ)
        if now.hour != EVENING_HOUR:
            return
        
        for guild_id, channel_id in self._quest_channels.items():
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                
                quests = await QuestService.get_today_quests(guild_id)
                if not quests:
                    continue
                
                rewards = await QuestService.distribute_rewards(guild_id)
                streak = await QuestService.get_streak(guild_id)
                top_contributors = await QuestService.get_top_contributors(guild_id, limit=5)
                
                embed = discord.Embed(
                    title="📊 KẾT QUẢ NHIỆM VỤ HÔM NAY",
                    color=0xFFD700
                )
                
                quest_results = []
                completed_count = 0
                for i, quest in enumerate(quests, 1):
                    defn = quest.definition
                    status = "✅" if quest.completed else "❌"
                    if quest.completed:
                        completed_count += 1
                    quest_results.append(
                        f"{status} {defn.icon} **{defn.name_vi}**: "
                        f"{quest.current_value}/{quest.target_value}"
                    )
                
                embed.add_field(
                    name=f"📋 Tiến Độ ({completed_count}/{len(quests)})",
                    value="\n".join(quest_results),
                    inline=False
                )
                
                if top_contributors:
                    top_lines = []
                    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                    for idx, (user_id, contrib) in enumerate(top_contributors):
                        try:
                            user = await self.bot.fetch_user(user_id)
                            name = user.display_name
                        except Exception:
                            name = f"User#{user_id}"
                        
                        reward = rewards.get(user_id, 0)
                        top_lines.append(f"{medals[idx]} **{name}** - {contrib} đóng góp → +{reward} Hạt")
                    
                    embed.add_field(
                        name="👥 TOP ĐÓNG GÓP",
                        value="\n".join(top_lines),
                        inline=False
                    )
                
                streak_text = f"🔥 Server streak: **{streak.current_streak}** ngày"
                if streak.longest_streak > streak.current_streak:
                    streak_text += f" (kỷ lục: {streak.longest_streak})"
                embed.add_field(name="⚡ Streak", value=streak_text, inline=False)
                
                total_distributed = sum(rewards.values())
                embed.set_footer(text=f"Tổng phát: {total_distributed} Hạt cho {len(rewards)} người")
                
                active_event = await get_active_event(guild_id)
                if active_event:
                    event_id = active_event.get("event_id")
                    if event_id:
                        event_manager = get_event_manager()
                        event_config = event_manager.get_event(event_id)
                        if event_config:
                            embed.add_field(
                                name=f"🎊 Sự Kiện: {event_config.name}",
                                value=f"Nhiệm vụ sự kiện riêng mỗi người.\nDùng `/nhiemvu` để xem tiến độ!",
                                inline=False
                            )
                
                await channel.send(embed=embed)
                logger.info(f"Evening summary sent to guild {guild_id}, distributed {total_distributed} Hạt")
                
            except Exception as e:
                logger.error(f"Failed evening summary for guild {guild_id}: {e}")

    @morning_announcement.before_loop
    async def before_morning(self) -> None:
        await self.bot.wait_until_ready()

    @evening_summary.before_loop
    async def before_evening(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="nhiemvu", description="Xem nhiệm vụ hàng ngày của server")
    async def nhiemvu(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if not interaction.guild:
            return await interaction.followup.send("Lệnh này chỉ dùng trong server!")
        
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        
        quests = await QuestService.generate_daily_quests(guild_id)
        streak = await QuestService.get_streak(guild_id)
        
        now = datetime.now(VN_TZ)
        embed = discord.Embed(
            title="🎯 NHIỆM VỤ NGÀY " + now.strftime("%d/%m/%Y"),
            color=0x00FF88
        )
        
        quest_lines = []
        completed_count = 0
        for i, quest in enumerate(quests, 1):
            defn = quest.definition
            desc = defn.description_vi.format(target=quest.target_value)
            status = "✅" if quest.completed else f"({quest.current_value}/{quest.target_value})"
            if quest.completed:
                completed_count += 1
            
            progress_bar = self._progress_bar(quest.progress_percent)
            quest_lines.append(
                f"{defn.icon} **{defn.name_vi}** {status}\n"
                f"   {progress_bar} {quest.progress_percent:.0f}%\n"
                f"   {desc} → {quest.reward_pool} Hạt"
            )
        
        embed.description = "\n\n".join(quest_lines)
        
        bonus_text = f"🎁 Hoàn thành cả 3: **+{ALL_QUEST_BONUS} Hạt**"
        if streak.current_streak > 0:
            bonus_text += f"\n🔥 Server streak: **{streak.current_streak}** ngày (+{int(streak.bonus_multiplier*100)}%)"
        
        embed.add_field(name="💰 Bonus", value=bonus_text, inline=False)
        
        event_section_added = await self._add_event_quests_section(
            embed, guild_id, user_id
        )
        
        if completed_count == len(quests):
            footer_text = "🎉 Tất cả nhiệm vụ đã hoàn thành! Chờ 22:00 để nhận thưởng."
        else:
            footer_text = "Cùng nhau hoàn thành nhiệm vụ nào!"
        
        if event_section_added:
            footer_text += " | Dùng /sukien nhiemvu để xem chi tiết nhiệm vụ sự kiện"
        
        embed.set_footer(text=footer_text)
        
        await interaction.followup.send(embed=embed)

    async def _add_event_quests_section(
        self, embed: discord.Embed, guild_id: int, user_id: int
    ) -> bool:
        try:
            active_event = await get_active_event(guild_id)
            if not active_event:
                return False
            
            event_id = active_event.get("event_id")
            if not event_id:
                return False
            
            event_manager = get_event_manager()
            event_config = event_manager.get_event(event_id)
            if not event_config:
                return False
            
            event_config_dict = {
                "daily_quests": [
                    {
                        "id": q.id,
                        "type": q.type,
                        "target": q.target,
                        "description": q.description,
                        "icon": q.icon,
                        "reward": q.reward,
                    }
                    for q in event_config.daily_quests
                ],
                "daily_quest_count": event_config.daily_quest_count,
                "fixed_quests": [
                    {
                        "id": q.id,
                        "type": q.type,
                        "target": q.target,
                        "description": q.description,
                        "icon": q.icon,
                        "reward_type": q.reward_type,
                        "reward_value": q.reward_value,
                    }
                    for q in event_config.fixed_quests
                ],
            }
            
            user_quests = await get_all_user_quests(
                guild_id, user_id, event_id, event_config_dict
            )
            
            daily_quests = user_quests.get("daily", [])
            if not daily_quests:
                return False
            
            event_lines = []
            event_completed = 0
            for quest in daily_quests:
                quest_data = quest.get("quest_data", {})
                if isinstance(quest_data, str):
                    import json
                    quest_data = json.loads(quest_data)
                
                icon = quest_data.get("icon", "📋")
                desc = quest_data.get("description", "Nhiệm vụ")
                reward = quest_data.get("reward", 0)
                progress = quest.get("progress", 0)
                target = quest.get("target", 1)
                completed = quest.get("completed", False)
                
                if completed:
                    event_completed += 1
                    status = "✅"
                else:
                    status = f"({progress}/{target})"
                
                percent = min(100, (progress / target * 100)) if target > 0 else 0
                progress_bar = self._progress_bar(percent)
                
                event_lines.append(
                    f"{icon} **{desc}** {status}\n"
                    f"   {progress_bar} {percent:.0f}% → {reward} {event_config.currency_emoji}"
                )
            
            if event_lines:
                embed.add_field(
                    name=f"🎊 Nhiệm Vụ Sự Kiện - {event_config.name} ({event_completed}/{len(daily_quests)})",
                    value="\n\n".join(event_lines[:3]),
                    inline=False
                )
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to add event quests section: {e}")
            return False

    @app_commands.command(name="nv-test-sang", description="[Admin] Trigger thông báo nhiệm vụ buổi sáng")
    @app_commands.checks.has_permissions(administrator=True)
    async def nv_test_morning(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Chỉ dùng trong server!", ephemeral=True)
        
        await interaction.response.defer()
        
        channel_id = self._quest_channels.get(interaction.guild.id)
        if not channel_id:
            return await interaction.followup.send(
                "Chưa cấu hình kênh nhiệm vụ! Dùng `/config kenh_nhiemvu:#channel`", 
                ephemeral=True
            )
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await interaction.followup.send("Không tìm thấy kênh!", ephemeral=True)
        
        quests = await QuestService.generate_daily_quests(interaction.guild.id)
        streak = await QuestService.get_streak(interaction.guild.id)
        
        now = datetime.now(VN_TZ)
        embed = discord.Embed(
            title="🎯 NHIỆM VỤ NGÀY " + now.strftime("%d/%m/%Y"),
            color=0x00FF88
        )
        
        quest_lines = []
        for i, quest in enumerate(quests, 1):
            defn = quest.definition
            desc = defn.description_vi.format(target=quest.target_value)
            quest_lines.append(
                f"{defn.icon} **{i}. {defn.name_vi}**\n"
                f"   {desc} → {quest.reward_pool} Hạt"
            )
        
        embed.description = "\n\n".join(quest_lines)
        
        bonus_text = f"🎁 Bonus hoàn thành cả 3: **+{ALL_QUEST_BONUS} Hạt**"
        if streak.current_streak > 0:
            bonus_text += f"\n🔥 Server streak: **{streak.current_streak}** ngày (+{int(streak.bonus_multiplier*100)}%)"
        
        embed.add_field(name="💰 Phần Thưởng", value=bonus_text, inline=False)
        embed.set_footer(text="[TEST] Kết quả sẽ được công bố lúc 22:00")
        
        await channel.send(embed=embed)
        await interaction.followup.send(f"✅ Đã gửi thông báo nhiệm vụ tới {channel.mention}", ephemeral=True)

    @app_commands.command(name="nv-test-toi", description="[Admin] Trigger kết quả nhiệm vụ buổi tối")
    @app_commands.checks.has_permissions(administrator=True)
    async def nv_test_evening(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Chỉ dùng trong server!", ephemeral=True)
        
        await interaction.response.defer()
        
        channel_id = self._quest_channels.get(interaction.guild.id)
        if not channel_id:
            return await interaction.followup.send(
                "Chưa cấu hình kênh nhiệm vụ! Dùng `/config kenh_nhiemvu:#channel`", 
                ephemeral=True
            )
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await interaction.followup.send("Không tìm thấy kênh!", ephemeral=True)
        
        quests = await QuestService.get_today_quests(interaction.guild.id)
        if not quests:
            return await interaction.followup.send("Chưa có nhiệm vụ hôm nay!", ephemeral=True)
        
        rewards = await QuestService.distribute_rewards(interaction.guild.id)
        streak = await QuestService.get_streak(interaction.guild.id)
        top_contributors = await QuestService.get_top_contributors(interaction.guild.id, limit=5)
        
        embed = discord.Embed(
            title="📊 KẾT QUẢ NHIỆM VỤ HÔM NAY",
            color=0xFFD700
        )
        
        quest_results = []
        completed_count = 0
        for i, quest in enumerate(quests, 1):
            defn = quest.definition
            status = "✅" if quest.completed else "❌"
            if quest.completed:
                completed_count += 1
            quest_results.append(
                f"{status} {defn.icon} **{defn.name_vi}**: "
                f"{quest.current_value}/{quest.target_value}"
            )
        
        embed.add_field(
            name=f"📋 Tiến Độ ({completed_count}/{len(quests)})",
            value="\n".join(quest_results),
            inline=False
        )
        
        if top_contributors:
            top_lines = []
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for idx, (user_id, contrib) in enumerate(top_contributors):
                try:
                    user = await self.bot.fetch_user(user_id)
                    name = user.display_name
                except Exception:
                    name = f"User#{user_id}"
                
                reward = rewards.get(user_id, 0)
                top_lines.append(f"{medals[idx]} **{name}** - {contrib} đóng góp → +{reward} Hạt")
            
            embed.add_field(
                name="👥 TOP ĐÓNG GÓP",
                value="\n".join(top_lines),
                inline=False
            )
        
        streak_text = f"🔥 Server streak: **{streak.current_streak}** ngày"
        if streak.longest_streak > streak.current_streak:
            streak_text += f" (kỷ lục: {streak.longest_streak})"
        embed.add_field(name="⚡ Streak", value=streak_text, inline=False)
        
        total_distributed = sum(rewards.values())
        embed.set_footer(text=f"[TEST] Tổng phát: {total_distributed} Hạt cho {len(rewards)} người")
        
        await channel.send(embed=embed)
        await interaction.followup.send(
            f"✅ Đã gửi kết quả tới {channel.mention}\n"
            f"💰 Phát {total_distributed} Hạt cho {len(rewards)} người",
            ephemeral=True
        )

    @staticmethod
    def _progress_bar(percent: float, length: int = 10) -> str:
        filled = int(percent / 100 * length)
        empty = length - filled
        return "█" * filled + "░" * empty


async def setup(bot: commands.Bot) -> None:
    """Load the QuestCog extension."""
    await bot.add_cog(QuestCog(bot))
