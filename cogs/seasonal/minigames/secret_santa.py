from __future__ import annotations

from core.logging import get_logger
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

logger = get_logger("seasonal_minigames_secret_santa")


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
            "phases": ["registration", "pairing", "gifting", "reveal"],
            "phase_duration_days": 2,
        }

    def _get_config(self, event: Any) -> dict[str, Any]:
        """Get minigame config from event with fallbacks."""
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("secret_santa", {})
        return {}

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

        config = self._get_config(event)
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

        event = self.event_manager.get_event(active["event_id"])
        config = self._get_config(event)
        reward = config.get("participation_reward", 50)
        await add_currency(guild_id, user_id, active["event_id"], reward)
        await add_contribution(guild_id, user_id, active["event_id"], reward)

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

    async def run_pairing(self, channel: TextChannel, guild_id: int) -> bool:
        """Execute circular pairing algorithm for all participants."""
        active = await get_active_event(guild_id)
        if not active:
            return False

        event = self.event_manager.get_event(active["event_id"])
        config = self._get_config(event)
        min_participants = config.get("min_participants", 4)

        participants = await execute_query(
            "SELECT user_id FROM secret_santa_participants WHERE guild_id = ? AND event_id = ?",
            (guild_id, active["event_id"]),
        )
        if not participants or len(participants) < min_participants:
            await channel.send(
                f"❌ Không đủ người tham gia! Cần tối thiểu **{min_participants}** người."
            )
            return False

        user_ids = [p["user_id"] for p in participants]
        random.shuffle(user_ids)

        for i, giver_id in enumerate(user_ids):
            receiver_id = user_ids[(i + 1) % len(user_ids)]
            await execute_write(
                """
                UPDATE secret_santa_participants
                SET receiver_id = ?
                WHERE guild_id = ? AND event_id = ? AND user_id = ?
                """,
                (receiver_id, guild_id, active["event_id"], giver_id),
            )

        await execute_write(
            "UPDATE secret_santa_sessions SET phase = ? WHERE guild_id = ? AND event_id = ?",
            (SecretSantaPhase.GIFTING.value, guild_id, active["event_id"]),
        )

        embed = discord.Embed(
            title="🎅 GHÉP CẶP HOÀN TẤT!",
            description=(
                f"**{len(user_ids)}** người đã được ghép cặp ngẫu nhiên!\n\n"
                "Sử dụng `/sukien secretsanta tangqua` để gửi lời chúc cho người bạn được ghép.\n\n"
                "**Lưu ý:** Quà của bạn sẽ được tiết lộ vào cuối sự kiện!"
            ),
            color=event.color if event else 0xC41E3A,
        )
        embed.set_footer(text="Hãy gửi những lời chúc tốt đẹp nhất!")
        await channel.send(embed=embed)

        for giver_id in user_ids:
            await self._notify_pairing(giver_id, guild_id, active["event_id"])

        return True

    async def _notify_pairing(self, giver_id: int, guild_id: int, event_id: str) -> None:
        """Send DM to giver about their receiver."""
        pairing = await execute_query(
            "SELECT receiver_id FROM secret_santa_participants WHERE guild_id = ? AND event_id = ? AND user_id = ?",
            (guild_id, event_id, giver_id),
        )
        if not pairing:
            return

        receiver_id = pairing[0]["receiver_id"]
        try:
            giver = self.bot.get_user(giver_id) or await self.bot.fetch_user(giver_id)
            receiver = self.bot.get_user(receiver_id) or await self.bot.fetch_user(receiver_id)

            embed = discord.Embed(
                title="🎅 Bạn Đã Được Ghép Cặp!",
                description=(
                    f"Người bạn cần tặng quà là: **{receiver.display_name}**\n\n"
                    "Sử dụng `/sukien secretsanta tangqua` để gửi lời chúc!\n"
                    "Họ sẽ không biết ai đã gửi cho đến lễ tiết lộ."
                ),
                color=0xC41E3A,
            )
            embed.set_thumbnail(url=receiver.display_avatar.url)
            await giver.send(embed=embed)
        except (discord.Forbidden, discord.NotFound):
            logger.warning(f"Cannot DM user {giver_id} about Secret Santa pairing")

    async def reveal_ceremony(self, channel: TextChannel, guild_id: int) -> None:
        """Reveal all Secret Santa pairings and gifts."""
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        config = self._get_config(event)

        await execute_write(
            "UPDATE secret_santa_sessions SET phase = ? WHERE guild_id = ? AND event_id = ?",
            (SecretSantaPhase.REVEAL.value, guild_id, active["event_id"]),
        )

        participants = await execute_query(
            """
            SELECT user_id, receiver_id, gift_message, gifted_at
            FROM secret_santa_participants
            WHERE guild_id = ? AND event_id = ?
            """,
            (guild_id, active["event_id"]),
        )

        if not participants:
            await channel.send("❌ Không có dữ liệu Secret Santa!")
            return

        embed = discord.Embed(
            title="🎄 LỄ TIẾT LỘ SECRET SANTA!",
            description="Tất cả những người tặng quà sẽ được tiết lộ!",
            color=event.color if event else 0xC41E3A,
        )

        reveals = []
        gifted_count = 0
        for p in participants:
            giver = self.bot.get_user(p["user_id"])
            receiver = self.bot.get_user(p["receiver_id"])
            giver_name = giver.display_name if giver else f"User {p['user_id']}"
            receiver_name = receiver.display_name if receiver else f"User {p['receiver_id']}"

            gift_msg = p.get("gift_message") or "*(Chưa gửi lời chúc)*"
            if p.get("gifted_at"):
                gifted_count += 1
                reveals.append(f"🎁 **{giver_name}** → **{receiver_name}**\n> {gift_msg}")
            else:
                reveals.append(f"😢 **{giver_name}** → **{receiver_name}**\n> *(Quên tặng quà)*")

        reveal_text = "\n\n".join(reveals)
        if len(reveal_text) > 4000:
            reveal_text = reveal_text[:4000] + "\n\n*...và nhiều hơn nữa!*"

        embed.add_field(name="🎅 Các Cặp", value=reveal_text or "Không có", inline=False)
        embed.add_field(name="📊 Thống Kê", value=f"Đã gửi quà: **{gifted_count}/{len(participants)}**", inline=True)

        bonus_reward = config.get("completion_bonus", 100)
        emoji = event.currency_emoji if event else "❄️"

        for p in participants:
            if p.get("gifted_at"):
                await add_currency(guild_id, p["user_id"], active["event_id"], bonus_reward)
                await add_contribution(guild_id, p["user_id"], active["event_id"], bonus_reward)

        embed.add_field(
            name="🎁 Phần Thưởng",
            value=f"Những ai đã gửi quà nhận thêm **+{bonus_reward}** {emoji}!",
            inline=True,
        )
        embed.set_footer(text="Cảm ơn mọi người đã tham gia Secret Santa!")

        await channel.send(embed=embed)
        await update_community_progress(guild_id, active["event_id"], gifted_count)

    async def check_my_santa(self, interaction: Interaction) -> None:
        """Check who will give you a gift (without revealing)."""
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện!", ephemeral=True)
            return

        session = await self._get_session(guild_id, active["event_id"])
        if not session or session["phase"] == SecretSantaPhase.REGISTRATION.value:
            await interaction.response.send_message("❌ Chưa ghép cặp!", ephemeral=True)
            return

        santa = await execute_query(
            """
            SELECT user_id, gift_message, gifted_at
            FROM secret_santa_participants
            WHERE guild_id = ? AND event_id = ? AND receiver_id = ?
            """,
            (guild_id, active["event_id"], user_id),
        )

        if not santa:
            await interaction.response.send_message("❌ Bạn chưa tham gia!", ephemeral=True)
            return

        if santa[0].get("gifted_at"):
            await interaction.response.send_message(
                "🎁 Người bí ẩn đã gửi quà cho bạn! Chờ lễ tiết lộ nhé!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⏳ Người bí ẩn chưa gửi quà. Hãy kiên nhẫn!",
                ephemeral=True,
            )

    async def check_my_giftee(self, interaction: Interaction) -> None:
        """Check who you need to give a gift to."""
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện!", ephemeral=True)
            return

        pairing = await execute_query(
            "SELECT receiver_id, gifted_at FROM secret_santa_participants WHERE guild_id = ? AND event_id = ? AND user_id = ?",
            (guild_id, active["event_id"], user_id),
        )

        if not pairing or not pairing[0].get("receiver_id"):
            await interaction.response.send_message("❌ Bạn chưa được ghép cặp!", ephemeral=True)
            return

        receiver_id = pairing[0]["receiver_id"]
        receiver = self.bot.get_user(receiver_id)
        receiver_name = receiver.display_name if receiver else f"User {receiver_id}"

        if pairing[0].get("gifted_at"):
            await interaction.response.send_message(
                f"✅ Bạn đã gửi quà cho **{receiver_name}** rồi!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"🎅 Bạn cần tặng quà cho: **{receiver_name}**\n"
                "Sử dụng `/sukien secretsanta tangqua` để gửi lời chúc!",
                ephemeral=True,
            )


class SecretSantaRegistrationView(discord.ui.View):
    minigame: "SecretSantaMinigame"

    def __init__(self, minigame: "SecretSantaMinigame", guild_id: int, event_id: str) -> None:
        super().__init__(timeout=None)
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id

    @discord.ui.button(label="🎅 Đăng Ký Tham Gia", style=discord.ButtonStyle.success)
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.minigame.register_participant(interaction)
