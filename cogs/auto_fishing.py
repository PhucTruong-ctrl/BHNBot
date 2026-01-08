import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from typing import Optional
import random

from core.database import db_manager
from core.logger import setup_logger
from cogs.fishing.constants import ALL_FISH

logger = setup_logger("AutoFishingCog", "cogs/auto_fishing.log")

UPGRADE_COSTS = {
    "efficiency": [0, 100, 500, 2000, 5000],
    "duration": [0, 200, 1000, 3000, 8000],
    "quality": [0, 300, 1500, 5000, 15000],
}

UPGRADE_VALUES = {
    "efficiency": [10, 25, 50, 75, 100],
    "duration": [1, 4, 8, 16, 24],
    "quality": [0, 2, 5, 8, 12],
}

FISH_BY_RARITY = {
    "common": [],
    "rare": [],
    "epic": [],
    "legendary": [],
}

for fish_key, fish_data in ALL_FISH.items():
    rarity = fish_data.get("rarity", "common")
    if rarity in FISH_BY_RARITY:
        FISH_BY_RARITY[rarity].append(fish_key)

ESSENCE_PER_RARITY = {
    "common": 1,
    "rare": 5,
    "epic": 25,
    "legendary": 100,
}


class AutoFishingUpgradeView(discord.ui.View):
    def __init__(self, user_id: int, bot):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.bot = bot

    async def get_user_data(self):
        return await db_manager.fetchone(
            "SELECT * FROM auto_fishing WHERE user_id = ?",
            (self.user_id,)
        )

    @discord.ui.button(label="⚡ Nâng cấp Hiệu suất", style=discord.ButtonStyle.primary)
    async def upgrade_efficiency(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        await self._do_upgrade(interaction, "efficiency")

    @discord.ui.button(label="⏱️ Nâng cấp Thời gian", style=discord.ButtonStyle.primary)
    async def upgrade_duration(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        await self._do_upgrade(interaction, "duration")

    @discord.ui.button(label="✨ Nâng cấp Chất lượng", style=discord.ButtonStyle.primary)
    async def upgrade_quality(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        await self._do_upgrade(interaction, "quality")

    async def _do_upgrade(self, interaction: discord.Interaction, upgrade_type: str):
        data = await self.get_user_data()
        if not data:
            return await interaction.response.send_message("❌ Bạn chưa có hệ thống auto-fish!", ephemeral=True)

        current_level = data[f"{upgrade_type}_level"]
        if current_level >= 5:
            return await interaction.response.send_message("❌ Đã đạt cấp tối đa!", ephemeral=True)

        cost = UPGRADE_COSTS[upgrade_type][current_level]
        if data["total_essence"] < cost:
            return await interaction.response.send_message(
                f"❌ Thiếu tinh chất! Cần **{cost}** (có {data['total_essence']})",
                ephemeral=True
            )

        await db_manager.modify(
            f"UPDATE auto_fishing SET {upgrade_type}_level = {upgrade_type}_level + 1, total_essence = total_essence - ? WHERE user_id = ?",
            (cost, self.user_id)
        )

        new_value = UPGRADE_VALUES[upgrade_type][current_level]
        await interaction.response.send_message(
            f"✅ Đã nâng cấp **{upgrade_type}** lên cấp {current_level + 1}!\n"
            f"Giá trị mới: **{new_value}**",
            ephemeral=True
        )


class AutoFishing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process_auto_fishing.start()

    def cog_unload(self):
        self.process_auto_fishing.cancel()

    async def ensure_table(self):
        await db_manager.modify("""
            CREATE TABLE IF NOT EXISTS auto_fishing (
                user_id BIGINT PRIMARY KEY,
                start_time TIMESTAMP,
                duration_hours INT DEFAULT 1,
                efficiency_level INT DEFAULT 1,
                duration_level INT DEFAULT 1,
                quality_level INT DEFAULT 1,
                total_essence INT DEFAULT 0,
                pending_fish TEXT DEFAULT '{}',
                last_claim TIMESTAMP
            )
        """)

    @tasks.loop(minutes=30)
    async def process_auto_fishing(self):
        try:
            active_sessions = await db_manager.fetchall(
                "SELECT * FROM auto_fishing WHERE start_time IS NOT NULL"
            )

            for session in active_sessions:
                user_id = session["user_id"]
                start_time = session["start_time"]
                duration = session["duration_hours"]

                if not start_time:
                    continue

                end_time = start_time + timedelta(hours=duration)
                if datetime.now() >= end_time:
                    await self._complete_fishing(user_id, session)

        except Exception as e:
            logger.error(f"Auto-fishing process error: {e}")

    @process_auto_fishing.before_loop
    async def before_process(self):
        await self.bot.wait_until_ready()
        await self.ensure_table()

    async def _complete_fishing(self, user_id: int, session: dict):
        efficiency = UPGRADE_VALUES["efficiency"][session["efficiency_level"] - 1]
        quality = UPGRADE_VALUES["quality"][session["quality_level"] - 1]
        duration = session["duration_hours"]

        total_fish = efficiency * duration
        caught_fish = {}

        for _ in range(total_fish):
            roll = random.randint(1, 100)
            if roll <= quality and FISH_BY_RARITY["rare"]:
                if roll <= quality // 2 and FISH_BY_RARITY["epic"]:
                    fish = random.choice(FISH_BY_RARITY["epic"])
                else:
                    fish = random.choice(FISH_BY_RARITY["rare"])
            else:
                fish = random.choice(FISH_BY_RARITY["common"]) if FISH_BY_RARITY["common"] else "ca_chep"

            caught_fish[fish] = caught_fish.get(fish, 0) + 1

        import json
        await db_manager.modify(
            "UPDATE auto_fishing SET start_time = NULL, pending_fish = ? WHERE user_id = ?",
            (json.dumps(caught_fish), user_id)
        )

        logger.info(f"Auto-fishing completed for {user_id}: {len(caught_fish)} types, {total_fish} total")

    @app_commands.command(name="auto-fish", description="Hệ thống câu cá tự động")
    @app_commands.describe(action="Hành động")
    @app_commands.choices(action=[
        app_commands.Choice(name="🎣 Thả câu", value="start"),
        app_commands.Choice(name="📦 Thu hoạch", value="claim"),
        app_commands.Choice(name="⬆️ Nâng cấp", value="upgrade"),
        app_commands.Choice(name="📊 Trạng thái", value="status"),
        app_commands.Choice(name="🔮 Tinh luyện cá", value="sacrifice"),
    ])
    async def auto_fish(self, interaction: discord.Interaction, action: str):
        await self.ensure_table()
        user_id = interaction.user.id

        data = await db_manager.fetchone(
            "SELECT * FROM auto_fishing WHERE user_id = ?", (user_id,)
        )

        if not data:
            await db_manager.modify(
                "INSERT INTO auto_fishing (user_id) VALUES (?)",
                (user_id,)
            )
            data = await db_manager.fetchone(
                "SELECT * FROM auto_fishing WHERE user_id = ?", (user_id,)
            )

        if action == "start":
            await self._start_fishing(interaction, data)
        elif action == "claim":
            await self._claim_fish(interaction, data)
        elif action == "upgrade":
            await self._show_upgrades(interaction, data)
        elif action == "status":
            await self._show_status(interaction, data)
        elif action == "sacrifice":
            await self._sacrifice_fish(interaction)

    async def _start_fishing(self, interaction: discord.Interaction, data: dict):
        if data["start_time"]:
            end_time = data["start_time"] + timedelta(hours=data["duration_hours"])
            remaining = end_time - datetime.now()
            if remaining.total_seconds() > 0:
                return await interaction.response.send_message(
                    f"🎣 Đang câu! Còn **{remaining.seconds // 3600}h {(remaining.seconds % 3600) // 60}m**",
                    ephemeral=True
                )

        max_duration = UPGRADE_VALUES["duration"][data["duration_level"] - 1]

        embed = discord.Embed(
            title="🎣 Thả Câu Tự Động",
            description=f"Chọn thời gian (tối đa **{max_duration}** giờ)",
            color=0x3498db
        )

        efficiency = UPGRADE_VALUES["efficiency"][data["efficiency_level"] - 1]
        quality = UPGRADE_VALUES["quality"][data["quality_level"] - 1]

        embed.add_field(name="⚡ Hiệu suất", value=f"{efficiency} cá/giờ", inline=True)
        embed.add_field(name="✨ Cá hiếm", value=f"{quality}%", inline=True)

        view = AutoFishStartView(interaction.user.id, max_duration)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _claim_fish(self, interaction: discord.Interaction, data: dict):
        import json
        pending = json.loads(data.get("pending_fish", "{}"))

        if not pending:
            if data["start_time"]:
                return await interaction.response.send_message(
                    "🎣 Vẫn đang câu! Chờ hoàn thành để thu hoạch.",
                    ephemeral=True
                )
            return await interaction.response.send_message(
                "📦 Không có cá để thu hoạch! Dùng `/auto-fish start` để thả câu.",
                ephemeral=True
            )

        total_fish = sum(pending.values())
        total_essence = 0

        for fish_key, count in pending.items():
            fish_data = ALL_FISH_DATA.get(fish_key, {})
            rarity = fish_data.get("rarity", "common")
            total_essence += count * ESSENCE_PER_RARITY.get(rarity, 1)

            await self.bot.inventory.modify(interaction.user.id, fish_key, count)

        await db_manager.modify(
            "UPDATE auto_fishing SET pending_fish = '{}', last_claim = ? WHERE user_id = ?",
            (datetime.now(), interaction.user.id)
        )

        embed = discord.Embed(
            title="📦 Thu Hoạch Thành Công!",
            description=f"Đã nhận **{total_fish}** cá!",
            color=0x2ecc71
        )

        fish_summary = []
        for fish_key, count in list(pending.items())[:10]:
            fish_data = ALL_FISH_DATA.get(fish_key, {})
            name = fish_data.get("name", fish_key)
            fish_summary.append(f"• {name} x{count}")

        if len(pending) > 10:
            fish_summary.append(f"... và {len(pending) - 10} loại khác")

        embed.add_field(name="Cá đã bắt", value="\n".join(fish_summary), inline=False)
        embed.set_footer(text=f"💎 Tinh chất ước tính nếu tinh luyện: {total_essence}")

        await interaction.response.send_message(embed=embed)

    async def _show_upgrades(self, interaction: discord.Interaction, data: dict):
        embed = discord.Embed(
            title="⬆️ Nâng Cấp Auto-Fish",
            description=f"💎 Tinh chất: **{data['total_essence']}**",
            color=0x9b59b6
        )

        for upgrade_type in ["efficiency", "duration", "quality"]:
            level = data[f"{upgrade_type}_level"]
            value = UPGRADE_VALUES[upgrade_type][level - 1]
            next_cost = UPGRADE_COSTS[upgrade_type][level] if level < 5 else "MAX"

            icons = {"efficiency": "⚡", "duration": "⏱️", "quality": "✨"}
            names = {"efficiency": "Hiệu suất", "duration": "Thời gian", "quality": "Chất lượng"}
            units = {"efficiency": "cá/giờ", "duration": "giờ tối đa", "quality": "% cá hiếm"}

            embed.add_field(
                name=f"{icons[upgrade_type]} {names[upgrade_type]} (Cấp {level}/5)",
                value=f"Hiện tại: **{value}** {units[upgrade_type]}\nNâng cấp: **{next_cost}** 💎",
                inline=True
            )

        view = AutoFishingUpgradeView(interaction.user.id, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _show_status(self, interaction: discord.Interaction, data: dict):
        embed = discord.Embed(title="📊 Trạng Thái Auto-Fish", color=0x3498db)

        efficiency = UPGRADE_VALUES["efficiency"][data["efficiency_level"] - 1]
        duration = UPGRADE_VALUES["duration"][data["duration_level"] - 1]
        quality = UPGRADE_VALUES["quality"][data["quality_level"] - 1]

        embed.add_field(name="⚡ Hiệu suất", value=f"{efficiency} cá/giờ", inline=True)
        embed.add_field(name="⏱️ Thời gian tối đa", value=f"{duration} giờ", inline=True)
        embed.add_field(name="✨ Cá hiếm", value=f"{quality}%", inline=True)
        embed.add_field(name="💎 Tinh chất", value=str(data["total_essence"]), inline=True)

        if data["start_time"]:
            end_time = data["start_time"] + timedelta(hours=data["duration_hours"])
            remaining = end_time - datetime.now()
            if remaining.total_seconds() > 0:
                status = f"🎣 Đang câu ({remaining.seconds // 3600}h {(remaining.seconds % 3600) // 60}m còn lại)"
            else:
                status = "📦 Hoàn thành! Dùng `/auto-fish claim` để thu hoạch"
        else:
            import json
            pending = json.loads(data.get("pending_fish", "{}"))
            if pending:
                status = f"📦 Có {sum(pending.values())} cá chờ thu hoạch!"
            else:
                status = "💤 Chờ thả câu"

        embed.add_field(name="Trạng thái", value=status, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _sacrifice_fish(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        inventory = await self.bot.inventory.get_all(interaction.user.id)
        fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH_DATA and v > 0}

        if not fish_items:
            return await interaction.followup.send("❌ Bạn không có cá để tinh luyện!")

        total_essence = 0
        sacrificed_count = 0

        for fish_key, count in fish_items.items():
            fish_data = ALL_FISH_DATA.get(fish_key, {})
            rarity = fish_data.get("rarity", "common")
            essence = count * ESSENCE_PER_RARITY.get(rarity, 1)
            total_essence += essence
            sacrificed_count += count

            await self.bot.inventory.modify(interaction.user.id, fish_key, -count)

        await db_manager.modify(
            "UPDATE auto_fishing SET total_essence = total_essence + ? WHERE user_id = ?",
            (total_essence, interaction.user.id)
        )

        await interaction.followup.send(
            f"🔮 Đã tinh luyện **{sacrificed_count}** cá!\n"
            f"Nhận được: **{total_essence}** 💎 Tinh chất"
        )


class AutoFishStartView(discord.ui.View):
    def __init__(self, user_id: int, max_hours: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.max_hours = max_hours

        options = []
        for h in [1, 2, 4, 8, 12, 24]:
            if h <= max_hours:
                options.append(discord.SelectOption(label=f"{h} giờ", value=str(h)))

        self.add_item(AutoFishDurationSelect(user_id, options))


class AutoFishDurationSelect(discord.ui.Select):
    def __init__(self, user_id: int, options: list):
        super().__init__(placeholder="Chọn thời gian...", options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)

        hours = int(self.values[0])

        await db_manager.modify(
            "UPDATE auto_fishing SET start_time = ?, duration_hours = ? WHERE user_id = ?",
            (datetime.now(), hours, self.user_id)
        )

        await interaction.response.edit_message(
            content=f"🎣 Đã thả câu **{hours}** giờ! Quay lại sau để thu hoạch.",
            embed=None,
            view=None
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoFishing(bot))
