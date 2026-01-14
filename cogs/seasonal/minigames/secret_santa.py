from __future__ import annotations

import random
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress
from ..services.database import execute_query, execute_write

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager


class SecretSantaPhase(Enum):
    REGISTRATION = "registration"
    PAIRING = "pairing"
    GIFTING = "gifting"
    REVEAL = "reveal"


@register_minigame("secret_santa")
class SecretSantaMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)

    @property
    def name(self) -> str:
        return "Secret Santa"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "scheduled",
            "registration_hours": 48,
            "gifting_hours": 72,
            "min_participants": 4,
            "reward_giver": 50,
            "reward_receiver": 50,
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def start_registration(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self.spawn_config
        registration_hours = config.get("registration_hours", 48)
        deadline = datetime.now() + timedelta(hours=registration_hours)

        await execute_write(
            """
            INSERT INTO secret_santa_sessions (guild_id, event_id, phase, registration_deadline, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (guild_id, event_id) DO UPDATE SET
                phase = ?,
                registration_deadline = ?,
                created_at = ?
            """,
            (
                guild_id, active["event_id"], SecretSantaPhase.REGISTRATION.value,
                deadline.isoformat(), datetime.now().isoformat(),
                SecretSantaPhase.REGISTRATION.value, deadline.isoformat(), datetime.now().isoformat()
            ),
        )

        embed = discord.Embed(
            title="🎅 SECRET SANTA BẮT ĐẦU!",
            description=(
                "Đăng ký tham gia Secret Santa!\n\n"
                "**Cách chơi:**\n"
                "1️⃣ Đăng ký tham gia\n"
                "2️⃣ Được ghép cặp ngẫu nhiên\n"
                "3️⃣ Tặng quà cho người được ghép\n"
                "4️⃣ Nhận quà từ người bí ẩn!\n"
            ),
            color=event.color if event else 0xC41E3A,
        )
        embed.add_field(name="⏰ Hạn đăng ký", value=f"<t:{int(deadline.timestamp())}:R>", inline=True)
        embed.add_field(name="👥 Tối thiểu", value=f"{config.get('min_participants', 4)} người", inline=True)

        view = SecretSantaRegistrationView(self, guild_id, active["event_id"])
        await channel.send(embed=embed, view=view)

    async def register_participant(self, interaction: Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện đang diễn ra!", ephemeral=True)
            return

        session = await self._get_session(guild_id, active["event_id"])
        if not session:
            await interaction.response.send_message("❌ Không có phiên Secret Santa!", ephemeral=True)
            return

        if session["phase"] != SecretSantaPhase.REGISTRATION.value:
            await interaction.response.send_message("❌ Đã hết thời gian đăng ký!", ephemeral=True)
            return

        existing = await execute_query(
            "SELECT 1 FROM secret_santa_participants WHERE guild_id = ? AND event_id = ? AND user_id = ?",
            (guild_id, active["event_id"], user_id),
        )
        if existing:
            await interaction.response.send_message("❌ Bạn đã đăng ký rồi!", ephemeral=True)
            return

        await execute_write(
            """
            INSERT INTO secret_santa_participants (guild_id, event_id, user_id, registered_at)
            VALUES (?, ?, ?, ?)
            """,
            (guild_id, active["event_id"], user_id, datetime.now().isoformat()),
        )

        count = await self._get_participant_count(guild_id, active["event_id"])
        await interaction.response.send_message(
            f"🎅 Đăng ký thành công! Hiện có **{count}** người tham gia.",
            ephemeral=True,
        )

    async def send_gift(self, interaction: Interaction, message: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện đang diễn ra!", ephemeral=True)
            return

        session = await self._get_session(guild_id, active["event_id"])
        if not session or session["phase"] != SecretSantaPhase.GIFTING.value:
            await interaction.response.send_message("❌ Chưa đến giai đoạn tặng quà!", ephemeral=True)
            return

        pairing = await execute_query(
            "SELECT receiver_id FROM secret_santa_participants WHERE guild_id = ? AND event_id = ? AND user_id = ?",
            (guild_id, active["event_id"], user_id),
        )
        if not pairing or not pairing[0].get("receiver_id"):
            await interaction.response.send_message("❌ Bạn chưa được ghép cặp!", ephemeral=True)
            return

        receiver_id = pairing[0]["receiver_id"]

        await execute_write(
            """
            UPDATE secret_santa_participants
            SET gift_message = ?, gifted_at = ?
            WHERE guild_id = ? AND event_id = ? AND user_id = ?
            """,
            (message, datetime.now().isoformat(), guild_id, active["event_id"], user_id),
        )

        config = self.spawn_config
        reward = config.get("reward_giver", 50)
        await add_currency(guild_id, user_id, active["event_id"], reward)
        await add_contribution(guild_id, user_id, active["event_id"], reward)

        event = self.event_manager.get_event(active["event_id"])
        emoji = event.currency_emoji if event else "❄️"

        await interaction.response.send_message(
            f"🎁 Đã gửi quà thành công! +**{reward}** {emoji}",
            ephemeral=True,
        )

    async def _get_session(self, guild_id: int, event_id: str) -> dict | None:
        rows = await execute_query(
            "SELECT * FROM secret_santa_sessions WHERE guild_id = ? AND event_id = ?",
            (guild_id, event_id),
        )
        return rows[0] if rows else None

    async def _get_participant_count(self, guild_id: int, event_id: str) -> int:
        rows = await execute_query(
            "SELECT COUNT(*) as count FROM secret_santa_participants WHERE guild_id = ? AND event_id = ?",
            (guild_id, event_id),
        )
        return rows[0]["count"] if rows else 0


class SecretSantaRegistrationView(discord.ui.View):
    def __init__(self, minigame: SecretSantaMinigame, guild_id: int, event_id: str) -> None:
        super().__init__(timeout=None)
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id

    @discord.ui.button(label="🎅 Đăng Ký Tham Gia", style=discord.ButtonStyle.success)
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.minigame.register_participant(interaction)
