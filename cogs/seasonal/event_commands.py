"""Event-specific commands for seasonal events."""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .core.event_manager import EventManager, get_event_manager
from .minigames import get_minigame
from .services import add_currency, get_active_event, get_currency

if TYPE_CHECKING:
    from bot import BHNBot


class EventCommandsCog(commands.Cog):
    def __init__(self, bot: BHNBot) -> None:
        self.bot = bot
        self.event_manager: EventManager = get_event_manager()

    async def _check_event_active(
        self, interaction: discord.Interaction, required_event: str | None = None
    ) -> dict | None:
        if not interaction.guild:
            await interaction.response.send_message(
                "Lệnh này chỉ dùng trong server!", ephemeral=True
            )
            return None

        active = await get_active_event(interaction.guild.id)
        if not active:
            await interaction.response.send_message(
                "❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True
            )
            return None

        if required_event and active["event_id"] != required_event:
            await interaction.response.send_message(
                f"❌ Lệnh này chỉ dùng được trong sự kiện {required_event}!", ephemeral=True
            )
            return None

        return active

    @app_commands.command(name="lixi", description="🧧 Tạo hoặc nhận lì xì (Sự kiện Tết)")
    @app_commands.describe(amount="Số tiền lì xì (để trống để nhận lì xì ngẫu nhiên)")
    async def lixi_command(
        self, interaction: discord.Interaction, amount: int | None = None
    ) -> None:
        active = await self._check_event_active(interaction, "spring_2026")
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        guild_id = interaction.guild.id  # type: ignore
        user_id = interaction.user.id

        if amount is not None:
            user_currency = await get_currency(guild_id, user_id, active["event_id"])
            if user_currency < amount:
                await interaction.response.send_message(
                    f"❌ Bạn không đủ {event.currency_emoji} để tạo lì xì!", ephemeral=True
                )
                return

            await add_currency(guild_id, user_id, active["event_id"], -amount)
            embed = discord.Embed(
                title="🧧 Lì Xì Đã Tạo!",
                description=(
                    f"{interaction.user.mention} đã tạo một lì xì **{amount}** {event.currency_emoji}!\n\n"
                    f"Người đầu tiên dùng `/lixi` sẽ nhận được!"
                ),
                color=0xFF6B6B,
            )
            self.bot._pending_lixi = {  # type: ignore
                "guild_id": guild_id,
                "amount": amount,
                "creator_id": user_id,
            }
            await interaction.response.send_message(embed=embed)
        else:
            pending = getattr(self.bot, "_pending_lixi", None)
            if pending and pending["guild_id"] == guild_id:
                if pending["creator_id"] == user_id:
                    await interaction.response.send_message(
                        "❌ Bạn không thể nhận lì xì của chính mình!", ephemeral=True
                    )
                    return

                await add_currency(guild_id, user_id, active["event_id"], pending["amount"])
                embed = discord.Embed(
                    title="🧧 Chúc Mừng!",
                    description=(
                        f"{interaction.user.mention} đã nhận được lì xì "
                        f"**{pending['amount']}** {event.currency_emoji}!"
                    ),
                    color=0xFF6B6B,
                )
                self.bot._pending_lixi = None  # type: ignore
                await interaction.response.send_message(embed=embed)
            else:
                bonus = random.randint(5, 25)
                await add_currency(guild_id, user_id, active["event_id"], bonus)
                embed = discord.Embed(
                    title="🧧 Lì Xì May Mắn!",
                    description=(
                        f"{interaction.user.mention} nhận được **{bonus}** {event.currency_emoji} "
                        f"từ lì xì may mắn!"
                    ),
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tricktreat", description="🎃 Trick or Treat! (Sự kiện Halloween)")
    @app_commands.describe(target="Người bạn muốn Trick or Treat")
    async def trick_or_treat(
        self, interaction: discord.Interaction, target: discord.Member
    ) -> None:
        active = await self._check_event_active(interaction, "halloween_2026")
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        guild_id = interaction.guild.id  # type: ignore
        user_id = interaction.user.id

        if target.id == user_id:
            await interaction.response.send_message(
                "❌ Bạn không thể trick or treat chính mình!", ephemeral=True
            )
            return

        if target.bot:
            await interaction.response.send_message(
                "❌ Bot không thể bị trick or treat!", ephemeral=True
            )
            return

        is_treat = random.random() < 0.6

        if is_treat:
            amount = random.randint(10, 30)
            await add_currency(guild_id, user_id, active["event_id"], amount)
            embed = discord.Embed(
                title="🍬 TREAT!",
                description=(
                    f"{target.mention} đã cho {interaction.user.mention} "
                    f"**{amount}** {event.currency_emoji}!\n\n"
                    "🎃 Happy Halloween!"
                ),
                color=0xFF8C00,
            )
        else:
            steal_amount = random.randint(5, 15)
            target_currency = await get_currency(guild_id, target.id, active["event_id"])
            actual_steal = min(steal_amount, target_currency)

            if actual_steal > 0:
                await add_currency(guild_id, target.id, active["event_id"], -actual_steal)
                await add_currency(guild_id, user_id, active["event_id"], actual_steal)
                embed = discord.Embed(
                    title="👻 TRICK!",
                    description=(
                        f"{interaction.user.mention} đã đánh cắp "
                        f"**{actual_steal}** {event.currency_emoji} từ {target.mention}!\n\n"
                        "🎃 Spooky!"
                    ),
                    color=0x8B0000,
                )
            else:
                embed = discord.Embed(
                    title="👻 TRICK... thất bại!",
                    description=(
                        f"{target.mention} không có gì để đánh cắp!\n\n"
                        "🎃 Better luck next time!"
                    ),
                    color=0x696969,
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="denlong", description="🏮 Thả đèn lồng (Sự kiện Trung Thu)")
    @app_commands.describe(message="Lời chúc của bạn")
    async def release_lantern(
        self, interaction: discord.Interaction, message: str
    ) -> None:
        active = await self._check_event_active(interaction, "midautumn_2026")
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        guild_id = interaction.guild.id  # type: ignore
        user_id = interaction.user.id

        if len(message) > 100:
            await interaction.response.send_message(
                "❌ Lời chúc không được quá 100 ký tự!", ephemeral=True
            )
            return

        from .services.database import execute_write

        await execute_write(
            """
            INSERT INTO lantern_parade (guild_id, user_id, event_id, message, released_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            (guild_id, user_id, active["event_id"], message),
        )

        bonus = random.randint(10, 25)
        await add_currency(guild_id, user_id, active["event_id"], bonus)

        embed = discord.Embed(
            title="🏮 Đèn Lồng Bay Lên!",
            description=(
                f"*\"{message}\"*\n\n"
                f"Đèn lồng của {interaction.user.mention} đã bay lên trời!\n"
                f"+**{bonus}** {event.currency_emoji}"
            ),
            color=0xFFD700,
        )
        embed.set_footer(text="🌕 Trung Thu vui vẻ!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sinhnhat", description="🎂 Gửi lời chúc sinh nhật (Sự kiện Anniversary)")
    @app_commands.describe(wish="Lời chúc của bạn cho BHNBot")
    async def birthday_wish(self, interaction: discord.Interaction, wish: str) -> None:
        active = await self._check_event_active(interaction, "birthday_2026")
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        guild_id = interaction.guild.id  # type: ignore
        user_id = interaction.user.id

        if len(wish) > 200:
            await interaction.response.send_message(
                "❌ Lời chúc không được quá 200 ký tự!", ephemeral=True
            )
            return

        from .services.database import execute_query, execute_write

        existing = await execute_query(
            """
            SELECT id FROM birthday_wishes
            WHERE guild_id = $1 AND user_id = $2 AND event_id = $3
            """,
            (guild_id, user_id, active["event_id"]),
        )

        if existing:
            await interaction.response.send_message(
                "❌ Bạn đã gửi lời chúc rồi!", ephemeral=True
            )
            return

        await execute_write(
            """
            INSERT INTO birthday_wishes (guild_id, user_id, event_id, wish, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            (guild_id, user_id, active["event_id"], wish),
        )

        bonus = 50
        await add_currency(guild_id, user_id, active["event_id"], bonus)

        embed = discord.Embed(
            title="🎂 Cảm Ơn Lời Chúc!",
            description=(
                f"*\"{wish}\"*\n\n"
                f"BHNBot cảm ơn lời chúc từ {interaction.user.mention}!\n"
                f"+**{bonus}** {event.currency_emoji}"
            ),
            color=0xFF69B4,
        )
        embed.set_footer(text="🎉 Happy Birthday BHNBot!")

        await interaction.response.send_message(embed=embed)


async def setup(bot: BHNBot) -> None:
    await bot.add_cog(EventCommandsCog(bot))
