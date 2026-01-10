import logging
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .services.voice_service import VoiceService, VoiceStats
from .services.kindness_service import KindnessService, KindnessStats
from .services.streak_service import StreakService, StreakData, STREAK_MULTIPLIERS
from .services.voice_reward_service import VoiceRewardService
from cogs.relationship.services.buddy_service import BuddyService
from cogs.quest.services.quest_service import QuestService
from cogs.quest.core.quest_types import QuestType

logger = logging.getLogger(__name__)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SocialCog(bot))


class SocialCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._reaction_cooldowns: dict[tuple[int, int], datetime] = {}

    async def cog_load(self) -> None:
        await VoiceService.ensure_table()
        await KindnessService.ensure_table()
        await StreakService.ensure_table()
        await VoiceRewardService.ensure_table()
        self.flush_voice_sessions.start()
        logger.info("SocialCog loaded - Voice & Kindness tracking active")

    async def cog_unload(self) -> None:
        self.flush_voice_sessions.cancel()

    @tasks.loop(minutes=5)
    async def flush_voice_sessions(self) -> None:
        for guild in self.bot.guilds:
            count = await VoiceService.flush_active_sessions(guild.id)
            if count > 0:
                logger.debug(f"Flushed {count} voice sessions for guild {guild.id}")
                await self._process_voice_rewards(guild)

    @flush_voice_sessions.before_loop
    async def before_flush(self) -> None:
        await self.bot.wait_until_ready()

    async def _process_voice_rewards(self, guild: discord.Guild) -> None:
        online_user_ids: set[int] = set()
        for vc in guild.voice_channels:
            for member in vc.members:
                if not member.bot:
                    online_user_ids.add(member.id)
        
        from core.database import db_manager
        rows = await db_manager.fetchall(
            """SELECT user_id, total_seconds FROM voice_stats 
               WHERE guild_id = $1 AND last_session_start IS NULL AND total_seconds > 0""",
            (guild.id,)
        )
        
        for row in rows:
            user_id, total_seconds = row[0], row[1]
            if total_seconds < 600:
                continue
            
            buddies = await BuddyService.get_buddies(user_id, guild.id)
            has_buddy_online = False
            for bond in buddies:
                buddy_id = BuddyService.get_buddy_id(bond, user_id)
                if buddy_id in online_user_ids:
                    has_buddy_online = True
                    break
            
            base, bonus = await VoiceRewardService.calculate_and_grant_reward(
                user_id, guild.id, 300, has_buddy_online
            )
            
            if base > 0 or bonus > 0:
                logger.debug(f"Voice reward granted: {user_id} -> {base}+{bonus} Hạt")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        if member.bot:
            return

        guild_id = member.guild.id
        user_id = member.id

        joined = before.channel is None and after.channel is not None
        left = before.channel is not None and after.channel is None

        if joined:
            await VoiceService.start_session(user_id, guild_id)
            logger.debug(f"Voice session started: {member} in {after.channel}")

        elif left:
            duration = await VoiceService.end_session(user_id, guild_id)
            logger.debug(f"Voice session ended: {member}, duration={duration}s")

    @commands.Cog.listener()
    async def on_reaction_add(
        self,
        reaction: discord.Reaction,
        user: discord.User
    ) -> None:
        if user.bot:
            return
        if reaction.message.author.bot:
            return
        if user.id == reaction.message.author.id:
            return

        guild = reaction.message.guild
        if not guild:
            return

        cooldown_key = (user.id, reaction.message.author.id)
        now = datetime.utcnow()

        if cooldown_key in self._reaction_cooldowns:
            elapsed = (now - self._reaction_cooldowns[cooldown_key]).total_seconds()
            if elapsed < 60:
                return

        self._reaction_cooldowns[cooldown_key] = now

        await KindnessService.increment_reaction_given(user.id, guild.id)
        await KindnessService.increment_reaction_received(reaction.message.author.id, guild.id)
        await StreakService.record_kind_action(user.id, guild.id)
        await QuestService.add_contribution(guild.id, user.id, QuestType.REACT_TOTAL, 1)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.mentions:
            return

        if not KindnessService.contains_thanks(message.content):
            return

        guild_id = message.guild.id
        sender_id = message.author.id

        await KindnessService.increment_thanks_given(sender_id, guild_id)
        await StreakService.record_kind_action(sender_id, guild_id)
        await QuestService.add_contribution(guild_id, sender_id, QuestType.THANK_TOTAL, 1)

        for mentioned_user in message.mentions:
            if mentioned_user.bot:
                continue
            if mentioned_user.id == sender_id:
                continue
            await KindnessService.increment_thanks_received(mentioned_user.id, guild_id)

    @app_commands.command(name="tute", description="Xem điểm tử tế của bạn hoặc người khác")
    @app_commands.describe(user="Người muốn xem (mặc định: bản thân)")
    async def kindness_cmd(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ) -> None:
        target = user or interaction.user
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        stats = await KindnessService.get_stats(target.id, interaction.guild.id)
        voice_stats = await VoiceService.get_stats(target.id, interaction.guild.id)
        streak = await StreakService.get_streak(target.id, interaction.guild.id)

        embed = discord.Embed(
            title=f"💝 Điểm Tử Tế - {target.display_name}",
            color=0xFF69B4
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        multiplier_text = f" (x{streak.multiplier:.2f})" if streak.multiplier > 1.0 else ""
        embed.add_field(
            name="📊 Tổng Điểm",
            value=f"**{stats.score:,}** điểm{multiplier_text}",
            inline=False
        )

        streak_text = f"🔥 **{streak.current_streak}** ngày"
        if streak.next_milestone:
            streak_text += f" (còn {streak.days_to_next_milestone} ngày đến x{STREAK_MULTIPLIERS.get(streak.next_milestone, 1.0):.2f})"
        if streak.streak_protected:
            streak_text += " 🛡️"
        embed.add_field(
            name="⚡ Streak Tử Tế",
            value=streak_text,
            inline=False
        )

        details = (
            f"😊 Reactions đã cho: **{stats.reactions_given}**\n"
            f"🥰 Reactions đã nhận: **{stats.reactions_received}**\n"
            f"🙏 Lần cảm ơn: **{stats.thanks_given}**\n"
            f"💕 Được cảm ơn: **{stats.thanks_received}**\n"
            f"🎁 Quà đã tặng: **{stats.gifts_given}**\n"
            f"📦 Quà đã nhận: **{stats.gifts_received}**"
        )
        embed.add_field(name="📋 Chi Tiết", value=details, inline=False)

        embed.add_field(
            name="🎤 Thời Gian Voice",
            value=f"**{voice_stats.total_hours}** giờ ({voice_stats.sessions_count} phiên)",
            inline=False
        )

        earned_today, remaining, voice_streak = await VoiceRewardService.get_daily_stats(
            target.id, interaction.guild.id
        )
        voice_reward_text = f"💰 Hôm nay: **{earned_today}** Hạt (còn {remaining} Hạt)"
        if voice_streak > 0:
            voice_reward_text += f"\n🔥 Voice streak: **{voice_streak}** ngày"
        embed.add_field(
            name="🎁 Voice Rewards",
            value=voice_reward_text,
            inline=False
        )

        embed.set_footer(text="Cho đi là nhận lại 💖")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tutetop", description="Bảng xếp hạng người tử tế nhất server")
    async def kindness_leaderboard(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        await interaction.response.defer()

        leaderboard = await KindnessService.get_leaderboard(interaction.guild.id, limit=10)

        if not leaderboard:
            await interaction.followup.send("Chưa có ai trong bảng xếp hạng!")
            return

        embed = discord.Embed(
            title="💝 Bảng Xếp Hạng Tử Tế",
            description="Top 10 người tử tế nhất server",
            color=0xFF69B4
        )

        medals = ["🥇", "🥈", "🥉"]
        lines = []

        for i, (user_id, score) in enumerate(leaderboard):
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            lines.append(f"{medal} {name} - **{score:,}** điểm")

        embed.description = "\n".join(lines)
        embed.set_footer(text="Hãy tử tế với mọi người nhé! 🌸")

        await interaction.followup.send(embed=embed)
