from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .core.event_manager import get_event_manager
from .minigames import get_minigame
from .services import (
    add_currency,
    claim_quest_reward,
    end_event,
    get_active_event,
    get_active_title,
    get_all_user_quests,
    get_announcement_message,
    get_community_progress,
    get_currency,
    get_last_progress,
    get_leaderboard,
    get_milestones_reached,
    get_participant_count,
    get_purchase_history,
    get_shop_items,
    get_user_titles,
    init_seasonal_tables,
    set_active_title,
    set_announcement_message,
    spend_currency,
    start_event,
    update_community_progress,
    update_last_progress,
)
from .services.database import (
    execute_query,
    get_notification_role,
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
        self.restore_events_task.start()
        self.check_event_dates.start()
        self.update_announcement_task.start()
        self.auto_spawn_minigames.start()
        logger.info("SeasonalEventsCog loaded")

    async def cog_unload(self) -> None:
        self.restore_events_task.cancel()
        self.check_event_dates.cancel()
        self.update_announcement_task.cancel()
        self.auto_spawn_minigames.cancel()

    @tasks.loop(count=1)
    async def restore_events_task(self) -> None:
        await self._restore_active_events()

    @restore_events_task.before_loop
    async def before_restore_events(self) -> None:
        await self.bot.wait_until_ready()

    async def _restore_active_events(self) -> None:
        logger.info(f"Starting event restoration for {len(self.bot.guilds)} guilds...")
        restored_count = 0
        for guild in self.bot.guilds:
            try:
                active = await get_active_event(guild.id)
                if active:
                    event_id = active["event_id"]
                    logger.debug(f"Found active event in DB: guild={guild.id}, event={event_id}")
                    if event_id in self.event_manager._registry:
                        self.event_manager._active_events[guild.id] = event_id
                        restored_count += 1
                        logger.info(f"Restored active event {event_id} for guild {guild.id} ({guild.name})")
                    else:
                        logger.warning(f"Event {event_id} not in registry for guild {guild.id} - skipping restore")
                else:
                    logger.debug(f"No active event found in DB for guild {guild.id}")
            except Exception as e:
                logger.error(f"Error restoring event for guild {guild.id}: {e}", exc_info=True)
        logger.info(f"Event restoration complete: {restored_count}/{len(self.bot.guilds)} guilds have active events")

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
                # Skip test events - they should only be ended manually
                if active.get("is_test_event"):
                    continue
                await end_event(guild.id)
                logger.info(f"Auto-ended event for guild {guild.id}")

    @check_event_dates.before_loop
    async def before_check_event_dates(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=30)
    async def auto_spawn_minigames(self) -> None:
        """Automatically spawn random minigames during active events."""
        for guild in self.bot.guilds:
            try:
                active = await get_active_event(guild.id)
                if not active:
                    continue

                event = self.event_manager.get_event(active["event_id"])
                if not event or not event.minigames:
                    continue

                if random.random() > 0.5:
                    continue

                minigame_type = random.choice(event.minigames)

                spawn_channel = None
                for channel in guild.text_channels:
                    if any(x in channel.name.lower() for x in ["chat", "general", "bot", "minigame"]):
                        if channel.permissions_for(guild.me).send_messages:
                            spawn_channel = channel
                            break

                if not spawn_channel:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            spawn_channel = channel
                            break

                if spawn_channel:
                    minigame = get_minigame(minigame_type, self.bot, self.event_manager)
                    if minigame:
                        await minigame.spawn(spawn_channel, guild.id)
                        logger.info(f"Auto-spawned {minigame_type} in {guild.name}#{spawn_channel.name}")

            except Exception as e:
                logger.error(f"Error auto-spawning minigame for guild {guild.id}: {e}")

    @auto_spawn_minigames.before_loop
    async def before_auto_spawn(self) -> None:
        await self.bot.wait_until_ready()
        # Wait 5 minutes after startup before first spawn
        await asyncio.sleep(300)

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

    @sukien_group.command(name="bosuutap", description="Xem bộ sưu tập cá sự kiện")
    async def sukien_collection(self, interaction: discord.Interaction) -> None:
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

        rows = await execute_query(
            """
            SELECT fish_key, COUNT(*) as count
            FROM event_fish_collection
            WHERE guild_id = $1 AND user_id = $2 AND event_id = $3
            GROUP BY fish_key
            """,
            (interaction.guild.id, interaction.user.id, active["event_id"]),
        )

        caught_fish = {row["fish_key"]: row["count"] for row in rows}
        all_fish = event.fish

        tier_stars = {"common": 1, "rare": 2, "epic": 3, "legendary": 4}

        embed = discord.Embed(
            title=f"🎣 Bộ Sưu Tập Cá - {event.name}",
            color=event.registry.color_int,
        )

        if not all_fish:
            embed.description = "Sự kiện này không có cá đặc biệt."
        else:
            fish_lines = []
            for fish in all_fish:
                count = caught_fish.get(fish.key, 0)
                status = "✅" if count > 0 else "❓"
                name = fish.name if count > 0 else "???"
                emoji = fish.emoji if count > 0 else "❓"
                stars = tier_stars.get(fish.tier, 1) if count > 0 else 0
                rarity = f"({'⭐' * stars})" if count > 0 else ""
                fish_lines.append(f"{status} {emoji} **{name}** {rarity} x{count}")

            embed.description = "\n".join(fish_lines)
            collected = len([f for f in all_fish if caught_fish.get(f.key, 0) > 0])
            embed.set_footer(text=f"Tiến độ: {collected}/{len(all_fish)} loại cá")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @sukien_group.command(name="lichsu", description="Xem lịch sử mua hàng")
    async def sukien_history(self, interaction: discord.Interaction) -> None:
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

        history = await get_purchase_history(
            interaction.guild.id, interaction.user.id, active["event_id"], limit=15
        )

        embed = discord.Embed(
            title=f"📜 Lịch Sử Mua Hàng - {event.name}",
            color=event.registry.color_int,
        )

        if not history:
            embed.description = "Bạn chưa mua gì trong sự kiện này."
        else:
            lines = []
            shop_items = {s.key: s for s in event.shop}
            for purchase in history:
                item = shop_items.get(purchase["item_key"])
                item_name = item.name if item else purchase["item_key"]
                ts = int(purchase["purchased_at"].timestamp())
                lines.append(
                    f"📦 **{item_name}** x{purchase['quantity']} "
                    f"(-{purchase['price_paid']} {event.currency_emoji}) <t:{ts}:R>"
                )
            embed.description = "\n".join(lines)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    danhhieu_group = app_commands.Group(name="danhhieu", description="Quản lý danh hiệu")

    @danhhieu_group.command(name="xem", description="Xem danh hiệu đã mở khóa")
    async def danhhieu_view(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        titles = await get_user_titles(interaction.guild.id, interaction.user.id)
        active_title = await get_active_title(interaction.user.id)

        embed = discord.Embed(
            title="🏅 Danh Hiệu Của Bạn",
            color=discord.Color.gold(),
        )

        if not titles:
            embed.description = "Bạn chưa mở khóa danh hiệu nào!\nTham gia sự kiện để nhận danh hiệu."
        else:
            title_lines = []
            for title in titles:
                is_active = "👑" if title["title_key"] == active_title else ""
                title_lines.append(f"{is_active} **{title['title_key']}** - từ {title['event_id']}")
            embed.description = "\n".join(title_lines)
            embed.set_footer(text="Dùng /danhhieu set <tên> để đặt danh hiệu")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @danhhieu_group.command(name="set", description="Đặt danh hiệu hiển thị")
    @app_commands.describe(title="Tên danh hiệu muốn dùng (để trống để bỏ)")
    async def danhhieu_set(self, interaction: discord.Interaction, title: str | None = None) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Lệnh này chỉ dùng trong server!", ephemeral=True)
            return

        if title is None:
            from .services import clear_active_title
            await clear_active_title(interaction.user.id)
            await interaction.response.send_message("✅ Đã bỏ danh hiệu.", ephemeral=True)
            return

        titles = await get_user_titles(interaction.guild.id, interaction.user.id)
        title_keys = [t["title_key"] for t in titles]

        if title not in title_keys:
            await interaction.response.send_message(
                f"❌ Bạn chưa mở khóa danh hiệu **{title}**!",
                ephemeral=True,
            )
            return

        await set_active_title(interaction.user.id, title)
        await interaction.response.send_message(f"✅ Đã đặt danh hiệu: **{title}**", ephemeral=True)

    sukien_test_group = app_commands.Group(
        name="sukien-test",
        description="Test commands cho sự kiện (Admin)",
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
            is_test_event=True,
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
    @app_commands.describe(minigame_type="ID minigame (vd: lixi_auto, boat_race, ghost_hunt...)")
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

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ Không thể spawn trong kênh này!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await minigame.spawn(interaction.channel, interaction.guild.id)
            await interaction.followup.send(f"✅ Đã spawn minigame `{minigame_type}`!", ephemeral=True)
        except Exception as e:
            logger.error(f"[MINIGAME] Error spawning {minigame_type}: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Lỗi spawn minigame: {e}", ephemeral=True)

    sukien_admin_group = app_commands.Group(
        name="sukien-admin",
        description="Admin commands cho sự kiện",
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
        self.event_manager._active_events[interaction.guild.id] = event_id
        logger.info(f"Admin started event {event_id} for guild {interaction.guild.id}")

        embed = create_event_start_embed(event)
        
        notification_role_id = await get_notification_role(interaction.guild.id)
        content = None
        if notification_role_id:
            role = interaction.guild.get_role(notification_role_id)
            if role:
                content = role.mention
        
        await interaction.response.send_message(content=content, embed=embed)

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
    cog = SeasonalEventsCog(bot)
    await bot.add_cog(cog)
