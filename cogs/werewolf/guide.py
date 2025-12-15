"""Werewolf game role guide with embeds."""

from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

from .roles import ROLE_REGISTRY
from .roles.base import Alignment, Expansion


class RoleGuideView(discord.ui.View):
    """Paginated view for role guides."""

    def __init__(self, pages: list[discord.Embed], author_id: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self) -> None:
        """Update button states based on current page."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the command author to use the buttons."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Chỉ người phát lệnh mới có thể sử dụng!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.gray, custom_id="prev_page")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Previous page button."""
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.gray, custom_id="next_page")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Next page button."""
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_timeout(self) -> None:
        """Called when the view times out."""
        self.prev_button.disabled = True
        self.next_button.disabled = True


def get_alignment_emoji(alignment: Alignment) -> str:
    """Get emoji for alignment."""
    emojis = {
        Alignment.VILLAGE: "🏘️",
        Alignment.WEREWOLF: "🐺",
        Alignment.NEUTRAL: "⚖️",
    }
    return emojis.get(alignment, "❓")

def create_guide_pages() -> list[discord.Embed]:
    """Create paginated guide embeds for all roles."""
    # Sort roles by alignment and name
    roles_by_alignment = {
        Alignment.VILLAGE: [],
        Alignment.WEREWOLF: [],
        Alignment.NEUTRAL: [],
    }

    for role_cls in ROLE_REGISTRY.values():
        roles_by_alignment[role_cls.metadata.alignment].append(role_cls)

    # Sort each alignment group by name
    for alignment in roles_by_alignment:
        roles_by_alignment[alignment].sort(key=lambda r: r.metadata.name)

    # Combine all roles: Village -> Werewolf -> Neutral
    all_roles = (
        roles_by_alignment[Alignment.VILLAGE]
        + roles_by_alignment[Alignment.WEREWOLF]
        + roles_by_alignment[Alignment.NEUTRAL]
    )

    # Create pages with 5 roles per page (for better image display)
    pages = []
    roles_per_page = 5

    for page_num, i in enumerate(range(0, len(all_roles), roles_per_page)):
        page_roles = all_roles[i : i + roles_per_page]
        embed = discord.Embed(
            title=f"📖 Hướng Dẫn Các Role Ma Sói - Trang {page_num + 1}",
            description="Hướng dẫn chi tiết về tất cả các role trong trò chơi.",
            color=0x2C3E50,
        )

        # Set thumbnail to first role's card image
        if page_roles:
            first_role_image = page_roles[0].metadata.card_image_url
            if first_role_image and "placeholder" not in first_role_image.lower():
                embed.set_thumbnail(url=first_role_image)

        # Add roles to embed
        for role_cls in page_roles:
            metadata = role_cls.metadata
            alignment_emoji = get_alignment_emoji(metadata.alignment)

            # Create role description field with image link
            role_name = f"{alignment_emoji} {metadata.name}"
            role_description = metadata.description

            embed.add_field(name=role_name, value=role_description, inline=False)

        # Add footer with page info
        total_pages = (len(all_roles) + roles_per_page - 1) // roles_per_page
        embed.set_footer(
            text=f"Trang {page_num + 1}/{total_pages} • "
            f"🏘️ = Dân Làng | 🐺 = Ma Sói | ⚖️ = Trung Lập",
            icon_url="https://upload.wikimedia.org/wikipedia/vi/b/bf/Logo_The_Werewolves_of_Millers_Hollow.png",
        )

        pages.append(embed)

    return pages


class WerewolfGuideCog(commands.Cog):
    """Werewolf game guide cog."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.guide_pages = create_guide_pages()

    def get_guide_embed(self) -> discord.Embed:
        """Get the first page of the guide."""
        if not self.guide_pages:
            return discord.Embed(title="❌ Lỗi", description="Không tìm thấy dữ liệu guide!")
        return self.guide_pages[0]

    def get_guide_view(self, author_id: int) -> RoleGuideView:
        """Get the view for guide navigation."""
        return RoleGuideView(self.guide_pages, author_id)


async def setup(bot: commands.Bot) -> None:
    """Setup the guide cog."""
    await bot.add_cog(WerewolfGuideCog(bot))
