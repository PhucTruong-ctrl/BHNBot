import io
import json
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from .core.themes import get_theme, THEMES, get_available_themes
from .core.stats import get_user_stats
from .services.profile_service import ProfileService
from .ui.views import ThemeSelectView, ThemePreviewView
from .ui.renderer import render_profile

logger = logging.getLogger(__name__)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        await ProfileService.ensure_table()
        logger.info("ProfileCog loaded - Profile customization ready")

    def _get_vip_tier(self, member: discord.Member) -> int:
        vip_roles = {
            "VIP 1": 1, "VIP Bạc": 1, "Bạc": 1,
            "VIP 2": 2, "VIP Vàng": 2, "Vàng": 2,
            "VIP 3": 3, "VIP Kim Cương": 3, "Kim Cương": 3,
        }
        for role in member.roles:
            if role.name in vip_roles:
                return vip_roles[role.name]
        return 0

    async def _get_achievement_emojis(self, user_id: int) -> list[str]:
        try:
            achievements_file = "data/achievements.json"
            with open(achievements_file, "r", encoding="utf-8") as f:
                achievements_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        from .core.stats import get_top_achievements
        unlocked_keys = await get_top_achievements(user_id, limit=4)

        emojis = []
        for category_data in achievements_data.values():
            for key, ach_data in category_data.items():
                if key in unlocked_keys and "emoji" in ach_data:
                    emojis.append(ach_data["emoji"])
                    if len(emojis) >= 4:
                        break
            if len(emojis) >= 4:
                break

        return emojis

    @app_commands.command(name="hoso", description="Xem hồ sơ cá nhân của bạn hoặc người khác")
    @app_commands.describe(user="Người muốn xem (mặc định: bản thân)")
    async def profile_cmd(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ) -> None:
        await interaction.response.defer()

        target = user or interaction.user
        if not isinstance(target, discord.Member):
            target = interaction.guild.get_member(target.id) if interaction.guild else None
            if not target:
                await interaction.followup.send("Không tìm thấy người dùng!", ephemeral=True)
                return

        guild_id = interaction.guild.id if interaction.guild else 0

        profile = await ProfileService.get_profile(target.id)
        stats = await get_user_stats(target.id, guild_id)
        achievement_emojis = await self._get_achievement_emojis(target.id)

        try:
            image_bytes = await render_profile(
                avatar_url=target.display_avatar.url,
                username=target.display_name,
                theme_key=profile.theme,
                stats=stats,
                bio=profile.bio,
                achievement_emojis=achievement_emojis,
            )

            file = discord.File(io.BytesIO(image_bytes), filename="profile.png")
            await interaction.followup.send(file=file)

        except Exception as e:
            logger.error(f"Failed to render profile for {target.id}: {e}")
            theme = get_theme(profile.theme)
            embed = discord.Embed(
                title=f"{theme.emoji} Hồ Sơ - {target.display_name}",
                color=discord.Color.from_rgb(*theme.accent_color)
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.add_field(name="🌾 Hạt", value=f"{stats.seeds:,}", inline=True)
            embed.add_field(name="🐟 Cá", value=f"{stats.fish_caught:,}", inline=True)
            embed.add_field(name="🎤 Voice", value=f"{stats.voice_hours:.1f}h", inline=True)
            embed.add_field(name="💝 Tử Tế", value=f"{stats.kindness_score:,}", inline=True)
            embed.add_field(name="🔥 Streak", value=f"{stats.daily_streak}", inline=True)
            embed.add_field(name="🏆 Rank", value=f"#{stats.rank}", inline=True)
            embed.add_field(name="📝 Bio", value=profile.bio, inline=False)
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="theme", description="Chọn theme cho hồ sơ")
    async def theme_cmd(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Lệnh này chỉ dùng trong server!", ephemeral=True
            )
            return

        vip_tier = self._get_vip_tier(interaction.user)
        profile = await ProfileService.get_profile(interaction.user.id)
        current_theme = get_theme(profile.theme)

        embed = discord.Embed(
            title="🎨 Chọn Theme Hồ Sơ",
            description=f"Theme hiện tại: **{current_theme.emoji} {current_theme.name}**",
            color=discord.Color.from_rgb(*current_theme.accent_color)
        )

        themes_list = []
        for theme in THEMES.values():
            lock = "🔒" if theme.vip_tier > vip_tier else "✅"
            vip_note = f" (VIP {theme.vip_tier})" if theme.vip_tier > 0 else ""
            themes_list.append(f"{lock} {theme.emoji} **{theme.name}**{vip_note}")

        embed.add_field(
            name="📋 Themes Có Sẵn",
            value="\n".join(themes_list),
            inline=False
        )

        view = ThemeSelectView(interaction.user.id, vip_tier, self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def set_user_theme(self, interaction: discord.Interaction, theme_key: str) -> None:
        theme = get_theme(theme_key)

        embed = discord.Embed(
            title=f"{theme.emoji} Preview: {theme.name}",
            description=f"Bạn có muốn áp dụng theme **{theme.name}**?",
            color=discord.Color.from_rgb(*theme.accent_color)
        )
        embed.add_field(name="Font", value=theme.font.replace(".ttf", ""), inline=True)
        embed.add_field(name="VIP Tier", value=str(theme.vip_tier) if theme.vip_tier > 0 else "Free", inline=True)

        view = ThemePreviewView(interaction.user.id, theme_key, self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def confirm_theme(self, interaction: discord.Interaction, theme_key: str) -> None:
        await ProfileService.set_theme(interaction.user.id, theme_key)
        theme = get_theme(theme_key)

        await interaction.response.edit_message(
            content=f"✅ Đã áp dụng theme **{theme.emoji} {theme.name}**!",
            embed=None,
            view=None
        )
        logger.info(f"User {interaction.user.id} changed theme to {theme_key}")

    @app_commands.command(name="bio", description="Đặt bio cá nhân cho hồ sơ")
    @app_commands.describe(text="Bio của bạn (tối đa 200 ký tự)")
    async def bio_cmd(
        self,
        interaction: discord.Interaction,
        text: str
    ) -> None:
        if len(text) > 200:
            await interaction.response.send_message(
                f"❌ Bio quá dài! ({len(text)}/200 ký tự)", ephemeral=True
            )
            return

        await ProfileService.set_bio(interaction.user.id, text)
        await interaction.response.send_message(
            f"✅ Đã cập nhật bio: *\"{text}\"*", ephemeral=True
        )
        logger.info(f"User {interaction.user.id} updated bio")
