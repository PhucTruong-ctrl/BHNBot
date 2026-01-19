import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional

from core.logging import setup_logger
from .services.fishing_service import AutoFishingService, AutoFishData
from .ui.views import (
    create_status_embed,
    create_storage_embed,
    create_upgrade_embed,
    MainMenuView,
    UpgradeView,
    SacrificeView,
    SellView,
)

logger = setup_logger("AutoFishingCog", "cogs/auto_fishing.log")


class AutoFishingCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.harvest_loop.start()

    async def cog_unload(self):
        self.harvest_loop.cancel()

    async def cog_load(self):
        await AutoFishingService.ensure_tables()

    @tasks.loop(minutes=30)
    async def harvest_loop(self):
        try:
            from core.database import db_manager
            rows = await db_manager.fetchall(
                "SELECT user_id FROM auto_fishing WHERE is_active = TRUE"
            )
            for row in rows:
                user_id = row[0]
                data = await AutoFishingService.get_user_data(user_id)
                if data and data.is_active:
                    await AutoFishingService.harvest_fish(user_id, data)
                    logger.info(f"Auto-harvested for user {user_id}")
        except Exception as e:
            logger.error(f"Harvest loop error: {e}")

    @harvest_loop.before_loop
    async def before_harvest(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="autocauca", description="Hệ thống câu cá tự động")
    async def auto_fish(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        data = await AutoFishingService.get_user_data(user_id)

        if not data:
            data = await AutoFishingService.create_user(user_id)

        if data.is_active and data.last_harvest:
            await AutoFishingService.harvest_fish(user_id, data)
            data = await AutoFishingService.get_user_data(user_id)

        storage = await AutoFishingService.get_storage(user_id)
        embed = create_status_embed(data, storage, data.is_active)
        view = MainMenuView(user_id, self)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def handle_main_menu(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        data = await AutoFishingService.get_user_data(user_id)
        if not data:
            data = await AutoFishingService.create_user(user_id)

        if data.is_active and data.last_harvest:
            await AutoFishingService.harvest_fish(user_id, data)
            data = await AutoFishingService.get_user_data(user_id)

        storage = await AutoFishingService.get_storage(user_id)
        embed = create_status_embed(data, storage, data.is_active)
        view = MainMenuView(user_id, self)

        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_refresh(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        data = await AutoFishingService.get_user_data(user_id)
        if not data:
            data = await AutoFishingService.create_user(user_id)

        harvested = {}
        if data.is_active and data.last_harvest:
            harvested = await AutoFishingService.harvest_fish(user_id, data)
            data = await AutoFishingService.get_user_data(user_id)

        storage = await AutoFishingService.get_storage(user_id)
        embed = create_status_embed(data, storage, data.is_active)

        if harvested:
            total = sum(harvested.values())
            embed.set_footer(text=f"🎣 Vừa thu hoạch {total} cá!")

        view = MainMenuView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_toggle(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        data = await AutoFishingService.get_user_data(user_id)
        if not data:
            data = await AutoFishingService.create_user(user_id)

        new_state = not data.is_active

        if data.is_active and data.last_harvest:
            await AutoFishingService.harvest_fish(user_id, data)

        await AutoFishingService.toggle_active(user_id, new_state)

        data = await AutoFishingService.get_user_data(user_id)
        storage = await AutoFishingService.get_storage(user_id)
        embed = create_status_embed(data, storage, data.is_active)

        status = "🟢 Bật" if data.is_active else "🔴 Tắt"
        embed.set_footer(text=f"Auto-fish đã {status}")
        logger.info(f"User {user_id} toggled auto-fish to {data.is_active}")

        view = MainMenuView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_storage(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        data = await AutoFishingService.get_user_data(user_id)
        if data and data.is_active and data.last_harvest:
            await AutoFishingService.harvest_fish(user_id, data)

        storage = await AutoFishingService.get_storage(user_id)
        embed = create_storage_embed(storage)
        view = MainMenuView(user_id, self)

        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_upgrade_menu(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        data = await AutoFishingService.get_user_data(user_id)
        if not data:
            data = await AutoFishingService.create_user(user_id)

        embed = create_upgrade_embed(data)
        view = UpgradeView(user_id, self)

        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_upgrade(self, interaction: discord.Interaction, upgrade_type: str):
        user_id = interaction.user.id
        success, message = await AutoFishingService.upgrade(user_id, upgrade_type)

        data = await AutoFishingService.get_user_data(user_id)
        embed = create_upgrade_embed(data)

        if success:
            embed.set_footer(text=f"✅ {message}")
            logger.info(f"User {user_id} upgraded {upgrade_type}: {message}")
        else:
            embed.set_footer(text=f"❌ {message}")

        view = UpgradeView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_transfer(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        data = await AutoFishingService.get_user_data(user_id)
        if data and data.is_active and data.last_harvest:
            await AutoFishingService.harvest_fish(user_id, data)

        types_count, total_count = await AutoFishingService.transfer_to_inventory(
            user_id, self.bot
        )

        storage = await AutoFishingService.get_storage(user_id)
        data = await AutoFishingService.get_user_data(user_id)
        embed = create_status_embed(data, storage, data.is_active if data else False)

        if total_count > 0:
            embed.set_footer(text=f"📦 Đã chuyển {total_count} cá vào xô!")
            logger.info(f"User {user_id} transferred {total_count} fish ({types_count} types) to inventory")
        else:
            embed.set_footer(text="❌ Không có cá để chuyển!")

        view = MainMenuView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_sacrifice_menu(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        data = await AutoFishingService.get_user_data(user_id)
        if data and data.is_active and data.last_harvest:
            await AutoFishingService.harvest_fish(user_id, data)

        storage = await AutoFishingService.get_storage(user_id)
        embed = create_storage_embed(storage)
        embed.title = "🔮 Tinh Luyện Cá"
        embed.description = "Chọn loại cá muốn tinh luyện thành 💎 Tinh chất"

        view = SacrificeView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_sacrifice(self, interaction: discord.Interaction, rarity: Optional[str]):
        user_id = interaction.user.id
        total_fish, total_essence = await AutoFishingService.sacrifice_fish(user_id, rarity)

        data = await AutoFishingService.get_user_data(user_id)
        storage = await AutoFishingService.get_storage(user_id)
        embed = create_status_embed(data, storage, data.is_active if data else False)

        if total_fish > 0:
            embed.set_footer(text=f"🔮 Đã tinh luyện {total_fish} cá → +{total_essence} 💎")
            logger.info(f"User {user_id} sacrificed {total_fish} fish for {total_essence} essence (filter: {rarity})")
        else:
            embed.set_footer(text="❌ Không có cá để tinh luyện!")

        view = MainMenuView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_sell_menu(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        data = await AutoFishingService.get_user_data(user_id)
        if data and data.is_active and data.last_harvest:
            await AutoFishingService.harvest_fish(user_id, data)

        storage = await AutoFishingService.get_storage(user_id)
        embed = create_storage_embed(storage)
        embed.title = "💰 Bán Cá"
        embed.description = "Chọn loại cá muốn bán"

        view = SellView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def handle_sell(self, interaction: discord.Interaction, rarity: Optional[str]):
        user_id = interaction.user.id
        total_fish, total_value = await AutoFishingService.sell_fish(user_id, self.bot, rarity)

        data = await AutoFishingService.get_user_data(user_id)
        storage = await AutoFishingService.get_storage(user_id)
        embed = create_status_embed(data, storage, data.is_active if data else False)

        if total_fish > 0:
            embed.set_footer(text=f"💰 Đã bán {total_fish} cá → +{total_value:,} 🪙")
            logger.info(f"User {user_id} sold {total_fish} fish for {total_value} coins (filter: {rarity})")
        else:
            embed.set_footer(text="❌ Không có cá để bán!")

        view = MainMenuView(user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoFishingCog(bot))
