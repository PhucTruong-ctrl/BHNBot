import discord
from typing import Optional, Callable, Awaitable
from cogs.fishing.constants import ALL_FISH
from ..core.calculator import ESSENCE_PER_RARITY


RARITY_ICONS = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "🟡"}
RARITY_NAMES = {"common": "Thường", "rare": "Hiếm", "epic": "Sử Thi", "legendary": "Huyền Thoại"}


def create_status_embed(
    data,
    storage: dict[str, int],
    is_active: bool = False
) -> discord.Embed:
    embed = discord.Embed(
        title="🎣 Auto-Fishing",
        color=0x3498db if is_active else 0x95a5a6
    )

    embed.add_field(name="⚡ Hiệu suất", value=f"{data.efficiency} cá/giờ", inline=True)
    embed.add_field(name="⏱️ Thời gian tối đa", value=f"{data.max_duration} giờ", inline=True)
    embed.add_field(name="✨ Cá hiếm bonus", value=f"+{data.quality_bonus}%", inline=True)
    embed.add_field(name="💎 Tinh chất", value=str(data.total_essence), inline=True)

    total_fish = sum(storage.values())
    embed.add_field(name="🪣 Kho cá", value=f"{total_fish} con", inline=True)

    status = "🟢 Đang hoạt động" if is_active else "🔴 Đã tắt"
    embed.add_field(name="Trạng thái", value=status, inline=True)

    return embed


def create_storage_embed(storage: dict[str, int]) -> discord.Embed:
    if not storage:
        embed = discord.Embed(
            title="🪣 Kho Cá Auto-Fish",
            description="Kho trống! Bật auto-fish để bắt đầu câu.",
            color=0x95a5a6
        )
        return embed

    embed = discord.Embed(
        title="🪣 Kho Cá Auto-Fish",
        color=0x3498db
    )

    by_rarity: dict[str, list[str]] = {"legendary": [], "epic": [], "rare": [], "common": []}
    total_essence = 0

    for fish_key, count in storage.items():
        fish_data = ALL_FISH.get(fish_key, {})
        name = fish_data.get("name", fish_key)
        rarity = fish_data.get("rarity", "common")
        essence = count * ESSENCE_PER_RARITY.get(rarity, 1)
        total_essence += essence
        by_rarity[rarity].append(f"{name} x{count}")

    for rarity in ["legendary", "epic", "rare", "common"]:
        fish_list = by_rarity[rarity]
        if fish_list:
            display = fish_list[:8]
            if len(fish_list) > 8:
                display.append(f"... +{len(fish_list) - 8} loại")
            embed.add_field(
                name=f"{RARITY_ICONS[rarity]} {RARITY_NAMES[rarity]}",
                value="\n".join(display),
                inline=True
            )

    total_fish = sum(storage.values())
    embed.set_footer(text=f"Tổng: {total_fish} cá | Tinh luyện: {total_essence} 💎")

    return embed


def create_upgrade_embed(data) -> discord.Embed:
    from ..core.calculator import get_upgrade_cost, UPGRADE_CONFIG

    embed = discord.Embed(
        title="⬆️ Nâng Cấp Auto-Fish",
        description=f"💎 Tinh chất: **{data.total_essence}**",
        color=0x9b59b6
    )

    upgrades = [
        ("efficiency", "⚡ Hiệu suất", f"{data.efficiency} cá/giờ", data.efficiency_level),
        ("duration", "⏱️ Thời gian", f"{data.max_duration} giờ", data.duration_level),
        ("quality", "✨ Chất lượng", f"+{data.quality_bonus}%", data.quality_level),
    ]

    for upgrade_type, name, current_val, level in upgrades:
        cost = get_upgrade_cost(upgrade_type, level)
        if cost:
            next_val = UPGRADE_CONFIG.__dict__[upgrade_type][level]
            cost_str = f"💎 {cost}"
            next_str = f"→ {next_val}"
        else:
            cost_str = "MAX"
            next_str = ""

        embed.add_field(
            name=f"{name} (Lv.{level})",
            value=f"{current_val} {next_str}\n{cost_str}",
            inline=True
        )

    return embed


class MainMenuView(discord.ui.View):

    def __init__(self, user_id: int, cog):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.secondary, row=0)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_refresh(interaction)

    @discord.ui.button(label="🟢 Bật/Tắt", style=discord.ButtonStyle.primary, row=0)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_toggle(interaction)

    @discord.ui.button(label="🪣 Xem kho", style=discord.ButtonStyle.secondary, row=0)
    async def storage(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_storage(interaction)

    @discord.ui.button(label="⬆️ Nâng cấp", style=discord.ButtonStyle.secondary, row=0)
    async def upgrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_upgrade_menu(interaction)

    @discord.ui.button(label="📦 Chuyển → Xô", style=discord.ButtonStyle.success, row=1)
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_transfer(interaction)

    @discord.ui.button(label="🔮 Tinh luyện", style=discord.ButtonStyle.danger, row=1)
    async def sacrifice(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_sacrifice_menu(interaction)

    @discord.ui.button(label="💰 Bán cá", style=discord.ButtonStyle.secondary, row=1)
    async def sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_sell_menu(interaction)


class UpgradeView(discord.ui.View):

    def __init__(self, user_id: int, cog):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⚡ Hiệu suất", style=discord.ButtonStyle.primary)
    async def upgrade_efficiency(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_upgrade(interaction, "efficiency")

    @discord.ui.button(label="⏱️ Thời gian", style=discord.ButtonStyle.primary)
    async def upgrade_duration(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_upgrade(interaction, "duration")

    @discord.ui.button(label="✨ Chất lượng", style=discord.ButtonStyle.primary)
    async def upgrade_quality(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_upgrade(interaction, "quality")

    @discord.ui.button(label="◀️ Quay lại", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_main_menu(interaction)


class SacrificeView(discord.ui.View):

    def __init__(self, user_id: int, cog):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔮 TẤT CẢ", style=discord.ButtonStyle.danger)
    async def sacrifice_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_sacrifice(interaction, None)

    @discord.ui.button(label="⚪ Thường", style=discord.ButtonStyle.secondary)
    async def sacrifice_common(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_sacrifice(interaction, "common")

    @discord.ui.button(label="🔵 Hiếm", style=discord.ButtonStyle.primary)
    async def sacrifice_rare(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_sacrifice(interaction, "rare")

    @discord.ui.button(label="◀️ Quay lại", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_main_menu(interaction)


class SellView(discord.ui.View):

    def __init__(self, user_id: int, cog):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="💰 Bán TẤT CẢ", style=discord.ButtonStyle.danger)
    async def sell_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_sell(interaction, None)

    @discord.ui.button(label="⚪ Bán Thường", style=discord.ButtonStyle.secondary)
    async def sell_common(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_sell(interaction, "common")

    @discord.ui.button(label="◀️ Quay lại", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_main_menu(interaction)
