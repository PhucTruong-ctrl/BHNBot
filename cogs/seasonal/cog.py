from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .core.event_manager import get_event_manager
from .services import (
    add_currency,
    claim_quest_reward,
    end_event,
    get_active_event,
    get_all_user_quests,
    get_announcement_message,
    get_community_progress,
    get_currency,
    get_last_progress,
    get_leaderboard,
    get_milestones_reached,
    get_participant_count,
    init_seasonal_tables,
    set_announcement_message,
    spend_currency,
    start_event,
    update_community_progress,
    update_last_progress,
)
from .ui import (
    ConfirmView,
    QuestView,
    ShopView,
    create_community_goal_embed,
    create_event_end_embed,
    create_event_info_embed,
    create_event_start_embed,
    create_leaderboard_embed,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SeasonalEventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.event_manager = get_event_manager(bot)

    async def cog_load(self) -> None:
        await init_seasonal_tables()
        await self._restore_active_events()
        self.check_event_dates.start()
        self.update_announcement_task.start()
        logger.info("SeasonalEventsCog loaded")

    async def cog_unload(self) -> None:
        self.check_event_dates.cancel()
        self.update_announcement_task.cancel()

    async def _restore_active_events(self) -> None:
        for guild in self.bot.guilds:
            active = await get_active_event(guild.id)
            if active:
                event_id = active["event_id"]
                if event_id in self.event_manager._registry:
                    self.event_manager._active_events[guild.id] = event_id
                    logger.info(f"Restored active event {event_id} for guild {guild.id}")

    @tasks.loop(minutes=5)
    async def update_announcement_task(self) -> None:
        for guild in self.bot.guilds:
            try:
                await self._update_guild_announcement(guild)
            except Exception as e:
                logger.error(f"Error updating announcement for guild {guild.id}: {e}")

    @update_announcement_task.before_loop
    async def before_update_announcement(self) -> None:
        await self.bot.wait_until_ready()

    async def _update_guild_announcement(self, guild: discord.Guild) -> None:
        active = await get_active_event(guild.id)
        if not active:
            return

        channel_id, message_id = await get_announcement_message(guild.id)
        if not channel_id or not message_id:
            return

        current_progress, goal = await get_community_progress(guild.id)
        last_progress = await get_last_progress(guild.id)

        if current_progress == last_progress:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(message_id)
            milestones = await get_milestones_reached(guild.id)
            embed = create_event_start_embed(event, current_progress, goal, milestones)
            await message.edit(embed=embed)
            await update_last_progress(guild.id, current_progress)
            logger.info(f"Updated announcement for guild {guild.id}: {current_progress}/{goal}")
        except discord.NotFound:
            logger.warning(f"Announcement message not found for guild {guild.id}")
        except discord.Forbidden:
            logger.warning(f"No permission to edit announcement for guild {guild.id}")

    @tasks.loop(hours=1)
    async def check_event_dates(self) -> None:
        if not self.event_manager.auto_start:
            return

        now = datetime.now()
        current_event = self.event_manager.get_current_event(now)

        for guild in self.bot.guilds:
            active = await get_active_event(guild.id)

            if current_event and not active:
                await start_event(
                    guild.id,
                    current_event.event_id,
                    current_event.community_goal_target,
                    current_event.registry.end_date,
                )
                logger.info(f"Auto-started {current_event.event_id} for guild {guild.id}")

            elif active and not current_event:
                await end_event(guild.id)
                logger.info(f"Auto-ended event for guild {guild.id}")

    @check_event_dates.before_loop
    async def before_check_event_dates(self) -> None:
        await self.bot.wait_until_ready()

    sukien_group = app_commands.Group(name="sukien", description="Các lệnh sự kiện theo mùa")

    @sukien_group.command(name="info", description="Xem thông tin sự kiện hiện tại")
    async def sukien_info(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy cấu hình sự kiện!", ephemeral=True)
            return

        user_currency = await get_currency(interaction.guild.id, interaction.user.id, active["event_id"])
        progress, goal = await get_community_progress(interaction.guild.id)

        embed = create_event_info_embed(event, user_currency, progress, goal)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @sukien_group.command(name="goal", description="Xem tiến độ Community Goal")
    async def sukien_goal(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy cấu hình sự kiện!", ephemeral=True)
            return

        progress, goal = await get_community_progress(interaction.guild.id)
        milestones = await get_milestones_reached(interaction.guild.id)

        embed = create_community_goal_embed(event, progress, goal, milestones)
        await interaction.response.send_message(embed=embed)

    @sukien_group.command(name="rank", description="Xem bảng xếp hạng sự kiện")
    async def sukien_rank(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy cấu hình sự kiện!", ephemeral=True)
            return

        leaderboard = await get_leaderboard(interaction.guild.id, active["event_id"], 10)
        embed = create_leaderboard_embed(event, leaderboard, self.bot)
        await interaction.response.send_message(embed=embed)

    @sukien_group.command(name="nhiemvu", description="Xem nhiệm vụ sự kiện")
    async def sukien_quests(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy cấu hình sự kiện!", ephemeral=True)
            return

        event_config = {
            "daily_quests": [q.__dict__ for q in event.daily_quests],
            "fixed_quests": [q.__dict__ for q in event.fixed_quests],
            "daily_quest_count": event.daily_quest_count,
        }
        quests = await get_all_user_quests(interaction.guild.id, interaction.user.id, active["event_id"], event_config)

        guild_id = interaction.guild.id
        user_id = interaction.user.id
        event_id = active["event_id"]

        async def claim_callback(inter: discord.Interaction, quest_id: str) -> bool:
            result = await claim_quest_reward(guild_id, user_id, event_id, quest_id)
            if result:
                reward = result.get("reward_value", 0)
                await inter.followup.send(f"✅ Nhận thưởng thành công! +{reward} {event.currency_emoji}", ephemeral=True)
                return True
            return False

        view = QuestView(event, interaction.user.id, quests, claim_callback)
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @sukien_group.command(name="cuahang", description="Cửa hàng sự kiện")
    async def sukien_shop(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy cấu hình sự kiện!", ephemeral=True)
            return

        user_currency = await get_currency(interaction.guild.id, interaction.user.id, active["event_id"])
        shop_items = [{"name": s.name, "price": s.price, "description": s.description, "emoji": "📦", "type": s.type, "key": s.key} for s in event.shop]

        shop_guild_id = interaction.guild.id
        shop_user_id = interaction.user.id
        shop_event_id = active["event_id"]

        async def purchase_callback(inter: discord.Interaction, item: dict) -> bool:
            price = item.get("price", 0)
            success = await spend_currency(shop_guild_id, shop_user_id, shop_event_id, price)
            if success:
                await inter.followup.send(f"✅ Đã mua **{item.get('name')}**!", ephemeral=True)
                return True
            await inter.followup.send("❌ Không đủ tiền!", ephemeral=True)
            return False

        view = ShopView(event, interaction.user.id, user_currency, shop_items, purchase_callback)
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @sukien_group.command(name="muctieu", description="Xem mục tiêu cộng đồng")
    async def sukien_muctieu(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy cấu hình sự kiện!", ephemeral=True)
            return

        progress, goal = await get_community_progress(interaction.guild.id)
        milestones = await get_milestones_reached(interaction.guild.id)

        embed = create_community_goal_embed(event, progress, goal, milestones)
        await interaction.response.send_message(embed=embed)

    @sukien_group.command(name="xephang", description="Bảng xếp hạng sự kiện")
    async def sukien_xephang(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy cấu hình sự kiện!", ephemeral=True)
            return

        leaderboard = await get_leaderboard(interaction.guild.id, active["event_id"], 10)
        embed = create_leaderboard_embed(event, leaderboard, self.bot)
        await interaction.response.send_message(embed=embed)

    sukien_test_group = app_commands.Group(
        name="sukien-test",
        description="Test commands cho sự kiện (Admin)",
        default_permissions=discord.Permissions(administrator=True),
    )

    @sukien_test_group.command(name="start", description="Bắt đầu sự kiện test")
    @app_commands.describe(event_id="ID sự kiện (vd: spring_2026)")
    async def test_start(self, interaction: discord.Interaction, event_id: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        event = self.event_manager.get_event(event_id)
        if not event:
            available = ", ".join(self.event_manager._registry.keys())
            await interaction.response.send_message(f"❌ Không tìm thấy `{event_id}`!\nCó sẵn: {available}", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if active:
            await interaction.response.send_message(f"❌ Đang có sự kiện `{active['event_id']}`! Dùng `/sukien-test end` trước.", ephemeral=True)
            return

        embed = create_event_start_embed(event, 0, event.community_goal_target, [])
        
        await interaction.response.send_message("✅ Đang khởi động sự kiện...", ephemeral=True)
        
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.edit_original_response(content="❌ Chỉ có thể khởi động trong kênh text!")
            return
        
        announcement_msg = await channel.send(embed=embed)
        
        await start_event(
            interaction.guild.id,
            event_id,
            event.community_goal_target,
            event.registry.end_date,
            channel.id,
            announcement_msg.id,
        )
        
        self.event_manager._active_events[interaction.guild.id] = event_id
        
        await interaction.edit_original_response(content=f"✅ Đã khởi động sự kiện **{event.name}**!")

    @sukien_test_group.command(name="end", description="Kết thúc sự kiện test")
    async def test_end(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện nào đang chạy!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        progress, goal = await get_community_progress(interaction.guild.id)
        participant_count = await get_participant_count(interaction.guild.id, active["event_id"])

        await end_event(interaction.guild.id)

        if event:
            embed = create_event_end_embed(event, progress, goal, participant_count)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("✅ Đã kết thúc sự kiện!")

    @sukien_test_group.command(name="currency", description="Thao tác tiền tệ sự kiện")
    @app_commands.describe(action="Hành động", amount="Số lượng")
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="spend", value="spend"),
        app_commands.Choice(name="check", value="check"),
    ])
    async def test_currency(self, interaction: discord.Interaction, action: str, amount: int = 0) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện nào đang chạy!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        emoji = event.currency_emoji if event else "💰"

        if action == "add":
            new_bal = await add_currency(interaction.guild.id, interaction.user.id, active["event_id"], amount)
            await interaction.response.send_message(f"✅ +{amount} {emoji} | Số dư: {new_bal} {emoji}")
        elif action == "spend":
            success = await spend_currency(interaction.guild.id, interaction.user.id, active["event_id"], amount)
            if success:
                bal = await get_currency(interaction.guild.id, interaction.user.id, active["event_id"])
                await interaction.response.send_message(f"✅ -{amount} {emoji} | Số dư: {bal} {emoji}")
            else:
                await interaction.response.send_message(f"❌ Không đủ tiền!")
        else:
            bal = await get_currency(interaction.guild.id, interaction.user.id, active["event_id"])
            await interaction.response.send_message(f"💰 Số dư: {bal} {emoji}")

    @sukien_test_group.command(name="milestone", description="Cập nhật tiến độ cộng đồng")
    @app_commands.describe(progress="Số lượng thêm vào")
    async def test_milestone(self, interaction: discord.Interaction, progress: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện nào đang chạy!", ephemeral=True)
            return

        new_progress = await update_community_progress(interaction.guild.id, progress)
        goal = active["community_goal"]
        percent = (new_progress / goal * 100) if goal > 0 else 0

        await interaction.response.send_message(f"📊 Community Goal: {new_progress:,} / {goal:,} ({percent:.1f}%)")

    @sukien_test_group.command(name="minigame", description="Spawn minigame test")
    @app_commands.describe(minigame_type="Loại minigame")
    @app_commands.choices(minigame_type=[
        app_commands.Choice(name="Lì Xì Auto", value="lixi_auto"),
        app_commands.Choice(name="Lì Xì Manual", value="lixi_manual"),
    ])
    async def test_minigame(self, interaction: discord.Interaction, minigame_type: str) -> None:
        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện nào đang chạy!", ephemeral=True)
            return

        from .minigames.base import get_minigame
        minigame = get_minigame(minigame_type, self.bot, self.event_manager)
        if not minigame:
            await interaction.response.send_message(f"❌ Không tìm thấy minigame `{minigame_type}`!", ephemeral=True)
            return

        if isinstance(interaction.channel, discord.TextChannel):
            await minigame.spawn(interaction.channel, interaction.guild.id)
            await interaction.response.send_message(f"✅ Đã spawn minigame `{minigame_type}`!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Không thể spawn trong kênh này!", ephemeral=True)

    sukien_admin_group = app_commands.Group(
        name="sukien-admin",
        description="Admin commands cho sự kiện",
        default_permissions=discord.Permissions(administrator=True),
    )

    @sukien_admin_group.command(name="start", description="Bắt đầu sự kiện thủ công")
    @app_commands.describe(event_id="ID của sự kiện (vd: spring_2026)")
    async def sukien_admin_start(self, interaction: discord.Interaction, event_id: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        event = self.event_manager.get_event(event_id)
        if not event:
            available = ", ".join(self.event_manager._registry.keys())
            await interaction.response.send_message(f"❌ Không tìm thấy event `{event_id}`!\nCó sẵn: {available}", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if active:
            await interaction.response.send_message(f"❌ Đã có sự kiện `{active['event_id']}` đang chạy! Dùng `/sukien-admin end` trước.", ephemeral=True)
            return

        await start_event(
            interaction.guild.id,
            event_id,
            event.community_goal_target,
            event.registry.end_date,
        )

        embed = create_event_start_embed(event)
        await interaction.response.send_message(embed=embed)

    @sukien_admin_group.command(name="end", description="Kết thúc sự kiện sớm")
    async def sukien_admin_end(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện nào đang chạy!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        progress, goal = await get_community_progress(interaction.guild.id)
        participant_count = await get_participant_count(interaction.guild.id, active["event_id"])

        await end_event(interaction.guild.id)

        if event:
            embed = create_event_end_embed(event, progress, goal, participant_count)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("✅ Đã kết thúc sự kiện!")

    @sukien_admin_group.command(name="addcurrency", description="Debug: Cộng currency cho user")
    @app_commands.describe(user="User nhận currency", amount="Số lượng")
    async def sukien_admin_addcurrency(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện nào đang chạy!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        new_balance = await add_currency(interaction.guild.id, user.id, active["event_id"], amount)

        emoji = event.currency_emoji if event else "💰"
        await interaction.response.send_message(f"✅ Đã cộng {amount} {emoji} cho {user.mention}. Balance mới: {new_balance} {emoji}")

    @sukien_admin_group.command(name="addgoal", description="Debug: Cộng tiến độ Community Goal")
    @app_commands.describe(amount="Số lượng thêm vào goal")
    async def sukien_admin_addgoal(self, interaction: discord.Interaction, amount: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện nào đang chạy!", ephemeral=True)
            return

        new_progress = await update_community_progress(interaction.guild.id, amount)
        goal = active["community_goal"]
        percent = (new_progress / goal * 100) if goal > 0 else 0

        await interaction.response.send_message(f"✅ Community Goal: {new_progress:,} / {goal:,} ({percent:.1f}%)")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SeasonalEventsCog(bot))
