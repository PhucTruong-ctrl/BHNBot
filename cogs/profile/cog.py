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
from core.services.vip_service import VIPEngine

logger = logging.getLogger(__name__)


async def _get_active_title(user_id: int) -> str | None:
    try:
        from cogs.seasonal.services import get_active_title, get_title_display
        title_key = await get_active_title(user_id)
        if title_key:
            return await get_title_display(title_key)
        return None
    except Exception:
        return None


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        await ProfileService.ensure_table()
        logger.info("ProfileCog loaded - Profile customization ready")

    async def _get_vip_tier(self, user_id: int) -> int:
        vip_data = await VIPEngine.get_vip_data(user_id)
        return vip_data['tier'] if vip_data else 0

    async def _get_achievement_emojis(self, user_id: int) -> list[str]:
        from core.data_cache import data_cache
        achievements_data = data_cache.get_achievements()
        if not achievements_data:
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

            active_title = await _get_active_title(target.id)
            title_text = f"🏅 **{active_title}**\n" if active_title else ""

            file = discord.File(io.BytesIO(image_bytes), filename="profile.png")
            await interaction.followup.send(content=title_text if title_text else None, file=file)

        except Exception as e:
            logger.error(f"Failed to render profile for {target.id}: {e}")
            theme = get_theme(profile.theme)
            active_title = await _get_active_title(target.id)

            title_display = f" | 🏅 {active_title}" if active_title else ""
            embed = discord.Embed(
                title=f"{theme.emoji} Hồ Sơ - {target.display_name}{title_display}",
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

        vip_tier = await self._get_vip_tier(interaction.user.id)
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
        embed.add_field(name="Yêu cầu", value="VIP " + str(theme.vip_tier) if theme.vip_tier > 0 else "Miễn phí", inline=True)

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

    @app_commands.command(name="thanhtuu", description="Xem thành tựu của bạn")
    @app_commands.describe(
        user="Người muốn xem (mặc định: bản thân)",
        category="Loại game để lọc"
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="🎣 Câu Cá", value="fishing"),
        app_commands.Choice(name="🐺 Ma Sói", value="werewolf"),
        app_commands.Choice(name="🔤 Nối Từ", value="noitu"),
        app_commands.Choice(name="🦀 Bầu Cua", value="baucua"),
        app_commands.Choice(name="🃏 Xì Dách", value="xidach"),
        app_commands.Choice(name="🎋 Sự Kiện", value="seasonal"),
    ])
    async def thanhtuu_cmd(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
        category: Optional[str] = None
    ) -> None:
        logger.info(f"[thanhtuu] Command invoked by {interaction.user.id}, target={user}, category={category}")
        
        try:
            await interaction.response.defer()
            logger.debug("[thanhtuu] Deferred response")
        except Exception as e:
            logger.error(f"[thanhtuu] Failed to defer: {e}")
            return
        
        target = user or interaction.user
        logger.debug(f"[thanhtuu] Target user: {target.id}")
        
        try:
            from core.data_cache import data_cache
            achievements_data = data_cache.get_achievements()
            if not achievements_data:
                with open("data/achievements.json", "r", encoding="utf-8") as f:
                    achievements_data = json.load(f)
            logger.debug(f"[thanhtuu] Loaded achievements with {len(achievements_data)} categories")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"[thanhtuu] Failed to load achievements.json: {e}")
            await interaction.followup.send("❌ Không thể tải dữ liệu thành tựu!", ephemeral=True)
            return
        
        if category == "seasonal":
            achievements_data = self._load_seasonal_achievements()
            if not achievements_data:
                await interaction.followup.send("❌ Không có sự kiện nào đang hoạt động!", ephemeral=True)
                return
        elif category is None:
            seasonal_data = self._load_seasonal_achievements()
            if seasonal_data:
                achievements_data.update(seasonal_data)
        
        from database_manager import db_manager
        
        try:
            logger.debug(f"[thanhtuu] Querying user_achievements for user_id={target.id}")
            rows = await db_manager.fetchall(
                "SELECT achievement_key, unlocked_at FROM user_achievements WHERE user_id = ?",
                (target.id,)
            )
            logger.debug(f"[thanhtuu] Query returned {len(rows) if rows else 0} rows")
        except Exception as e:
            logger.error(f"[thanhtuu] Database query failed: {e}", exc_info=True)
            await interaction.followup.send("❌ Lỗi truy vấn database!", ephemeral=True)
            return
        
        try:
            unlocked_keys = {row[0]: row[1] for row in (rows or [])}
            logger.debug(f"[thanhtuu] Unlocked keys: {len(unlocked_keys)}")
        except Exception as e:
            logger.error(f"[thanhtuu] Failed to parse rows: {e}, rows={rows}", exc_info=True)
            await interaction.followup.send("❌ Lỗi xử lý dữ liệu!", ephemeral=True)
            return
        
        categories_to_show = list(achievements_data.keys()) if (category == "seasonal" or not category) else [category]
        logger.debug(f"[thanhtuu] Categories to show: {categories_to_show}")
        
        pages = []
        for cat in categories_to_show:
            if cat not in achievements_data:
                logger.debug(f"[thanhtuu] Category '{cat}' not found in achievements_data, skipping")
                continue
            
            logger.debug(f"[thanhtuu] Processing category: {cat}")
            cat_achievements = achievements_data[cat]
            cat_emoji = self._get_category_emoji(cat)
            cat_name = self._get_category_name(cat)
            
            unlocked_in_cat = sum(1 for key in cat_achievements if key in unlocked_keys)
            total_in_cat = len(cat_achievements)
            
            embed = discord.Embed(
                title=f"{cat_emoji} Thành Tựu {cat_name} - {target.display_name}",
                description=f"Đã mở khóa: **{unlocked_in_cat}/{total_in_cat}**",
                color=0xFFD700 if unlocked_in_cat == total_in_cat else 0x5865F2
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            
            lines = []
            for key, ach in cat_achievements.items():
                emoji = ach.get("emoji", "🏆")
                name = ach.get("name", key)
                desc = ach.get("description", "")
                reward = ach.get("reward_seeds", 0)
                
                if key in unlocked_keys:
                    unlock_time = unlocked_keys[key]
                    if isinstance(unlock_time, str):
                        from datetime import datetime
                        try:
                            unlock_time = datetime.fromisoformat(unlock_time.replace("Z", "+00:00"))
                            date_str = unlock_time.strftime("%d/%m/%Y")
                        except:
                            date_str = "???"
                    else:
                        date_str = unlock_time.strftime("%d/%m/%Y") if unlock_time else "???"
                    lines.append(f"✅ {emoji} **{name}**\n   _{desc}_ • {date_str}")
                else:
                    target_val = ach.get("target_value", 0)
                    lines.append(f"🔒 {emoji} **{name}**\n   _{desc}_ • Mục tiêu: {target_val}")
            
            def chunk_lines(lines: list, max_chars: int = 1000) -> list:
                chunks = []
                current_chunk = []
                current_len = 0
                
                for line in lines:
                    line_len = len(line) + 1
                    if current_len + line_len > max_chars and current_chunk:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_len = line_len
                    else:
                        current_chunk.append(line)
                        current_len += line_len
                
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                return chunks
            
            chunks = chunk_lines(lines) if lines else ["Không có thành tựu"]
            for i, chunk in enumerate(chunks):
                field_name = "Danh sách" if i == 0 else "\u200b"
                embed.add_field(name=field_name, value=chunk, inline=False)
            
            pages.append(embed)
            logger.debug(f"[thanhtuu] Built page for category '{cat}'")
        
        logger.info(f"[thanhtuu] Built {len(pages)} pages total")
        
        if not pages:
            logger.warning("[thanhtuu] No pages to show")
            await interaction.followup.send("❌ Không tìm thấy thành tựu nào!", ephemeral=True)
            return
        
        try:
            if len(pages) == 1:
                logger.debug("[thanhtuu] Sending single page")
                await interaction.followup.send(embed=pages[0])
            else:
                logger.debug("[thanhtuu] Sending paginated view")
                view = AchievementPaginationView(pages, target.id)
                pages[0].set_footer(text=f"Trang 1/{len(pages)} • Dùng nút bên dưới để chuyển trang")
                await interaction.followup.send(embed=pages[0], view=view)
            logger.info(f"[thanhtuu] Command completed successfully for user {interaction.user.id}")
        except Exception as e:
            logger.error(f"[thanhtuu] Failed to send response: {e}", exc_info=True)
            await interaction.followup.send("❌ Lỗi gửi kết quả!", ephemeral=True)

    def _get_category_emoji(self, category: str) -> str:
        mapping = {
            "fishing": "🎣",
            "werewolf": "🐺",
            "noitu": "🔤",
            "baucua": "🦀",
            "xidach": "🃏",
            "seasonal": "🎋",
            "spring": "🌸", "spring_2026": "🌸",
            "summer": "☀️", "summer_2026": "☀️",
            "autumn": "🍂", "autumn_2026": "🍂",
            "winter": "❄️", "winter_2026": "❄️",
            "halloween": "🎃", "halloween_2026": "🎃",
            "earthday": "🌍", "earthday_2026": "🌍",
            "midautumn": "🥮", "midautumn_2026": "🥮",
            "birthday": "🎂", "birthday_2026": "🎂",
        }
        return mapping.get(category, "🏆")

    def _get_category_name(self, category: str) -> str:
        mapping = {
            "fishing": "Câu Cá",
            "werewolf": "Ma Sói",
            "noitu": "Nối Từ",
            "baucua": "Bầu Cua",
            "xidach": "Xì Dách",
            "seasonal": "Sự Kiện",
            "spring": "Lễ Hội Hoa Xuân", "spring_2026": "Lễ Hội Hoa Xuân 2026",
            "summer": "Lễ Hội Biển", "summer_2026": "Lễ Hội Biển 2026",
            "autumn": "Lễ Hội Thu Hoạch", "autumn_2026": "Lễ Hội Thu Hoạch 2026",
            "winter": "Lễ Hội Mùa Đông", "winter_2026": "Lễ Hội Mùa Đông 2026",
            "halloween": "Lễ Hội Halloween", "halloween_2026": "Lễ Hội Halloween 2026",
            "earthday": "Ngày Trái Đất", "earthday_2026": "Ngày Trái Đất 2026",
            "midautumn": "Tết Trung Thu", "midautumn_2026": "Tết Trung Thu 2026",
            "birthday": "Sinh Nhật Bot", "birthday_2026": "Sinh Nhật Bot 2026",
        }
        return mapping.get(category, category.title())

    def _load_seasonal_achievements(self) -> dict:
        import glob
        from pathlib import Path
        from core.data_cache import data_cache
        
        seasonal_data = {}
        events_dir = Path("data/events")
        
        for event_file in events_dir.glob("*.json"):
            if event_file.name == "registry.json":
                continue
            try:
                cache_key = f"event_{event_file.stem}"
                event_data = data_cache.get(cache_key)
                if not event_data:
                    with open(event_file, "r", encoding="utf-8") as f:
                        event_data = json.load(f)
                
                if "achievements" in event_data:
                    event_id = event_data.get("event_id", event_file.stem)
                    seasonal_data[event_id] = event_data["achievements"]
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"[thanhtuu] Failed to load {event_file}: {e}")
                continue
        
        return seasonal_data


class AchievementPaginationView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], owner_id: int):
        super().__init__(timeout=180)
        self.pages = pages
        self.current_page = 0
        self.owner_id = owner_id
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page >= len(self.pages) - 1

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("Không phải của bạn!", ephemeral=True)
        
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        
        embed = self.pages[self.current_page]
        embed.set_footer(text=f"Trang {self.current_page + 1}/{len(self.pages)} • Dùng nút bên dưới để chuyển trang")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("Không phải của bạn!", ephemeral=True)
        
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._update_buttons()
        
        embed = self.pages[self.current_page]
        embed.set_footer(text=f"Trang {self.current_page + 1}/{len(self.pages)} • Dùng nút bên dưới để chuyển trang")
        await interaction.response.edit_message(embed=embed, view=self)
