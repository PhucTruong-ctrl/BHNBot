from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("Lixi")


@register_minigame("lixi_auto")
class LixiAutoMinigame(BaseMinigame):
    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_messages: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Lì Xì Trời Cho"

    def _get_config(self, event: Any) -> dict[str, Any]:
        """Get minigame config from event with fallbacks."""
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("lixi_auto", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self._get_config(event)
        max_claims = config.get("max_claims", 5)
        timeout = config.get("timeout_seconds", 60)

        expire_time = datetime.now() + timedelta(seconds=timeout)

        embed = discord.Embed(
            title="🧧 LÌ XÌ TRỜI CHO!",
            description="Ông Địa đang phát lì xì! Nhanh tay nhận nào!",
            color=event.color,
        )
        embed.add_field(name="🎁 Còn lại", value=f"{max_claims}/{max_claims} phần", inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        view = LixiAutoView(self, guild_id, active["event_id"], max_claims, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_messages[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "claims": [],
            "max_claims": max_claims,
            "expire_time": expire_time,
            "message": message,
        }

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def claim_lixi(self, interaction: Interaction, message_id: int) -> None:
        data = self._active_messages.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Lì xì này đã hết hiệu lực!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Lì xì đã hết hạn!", ephemeral=True)
            return

        if interaction.user.id in data["claims"]:
            await interaction.response.send_message("❌ Bạn đã nhận lì xì này rồi!", ephemeral=True)
            return

        if len(data["claims"]) >= data["max_claims"]:
            await interaction.response.send_message("❌ Lì xì đã hết!", ephemeral=True)
            return

        event = self.event_manager.get_event(data["event_id"])
        reward_range = self._get_config(event).get("reward_range", [20, 100])
        reward = random.randint(reward_range[0], reward_range[1])

        data["claims"].append(interaction.user.id)

        await add_currency(data["guild_id"], interaction.user.id, data["event_id"], reward)
        await add_contribution(data["guild_id"], interaction.user.id, data["event_id"], reward)
        await update_community_progress(data["guild_id"], reward)

        emoji = event.currency_emoji if event else "🌸"

        await interaction.response.send_message(f"🧧 Bạn nhận được **+{reward} {emoji}**!", ephemeral=True)

        remaining = data["max_claims"] - len(data["claims"])
        if remaining <= 0:
            await self._end_lixi(data)
        else:
            await self._update_embed(data, remaining)

    async def _update_embed(self, data: dict, remaining: int) -> None:
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])

        embed = discord.Embed(
            title="🧧 LÌ XÌ TRỜI CHO!",
            description="Ông Địa đang phát lì xì! Nhanh tay nhận nào!",
            color=event.color if event else 0xFFB7C5,
        )
        embed.add_field(name="🎁 Còn lại", value=f"{remaining}/{data['max_claims']} phần", inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(data['expire_time'].timestamp())}:R>", inline=True)

        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            pass

    async def _end_lixi(self, data: dict) -> None:
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🌸"

        claims_text = []
        for user_id in data["claims"]:
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            claims_text.append(f"🎁 {name}")

        embed = discord.Embed(
            title="🧧 LÌ XÌ ĐÃ HẾT!",
            description="Người may mắn:\n" + "\n".join(claims_text) if claims_text else "Không ai nhận!",
            color=event.color if event else 0xFFB7C5,
        )

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_messages.pop(message.id, None)


class LixiAutoView(discord.ui.View):
    minigame: LixiAutoMinigame

    def __init__(
        self,
        minigame: LixiAutoMinigame,
        guild_id: int,
        event_id: str,
        max_claims: int,
        expire_time: datetime,
    ) -> None:
        super().__init__(timeout=60)
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.max_claims = max_claims
        self.expire_time = expire_time

    @discord.ui.button(label="🧧 Nhận Lì Xì", style=discord.ButtonStyle.danger)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.message:
            await self.minigame.claim_lixi(interaction, interaction.message.id)


@register_minigame("lixi_manual")
class LixiManualMinigame(BaseMinigame):
    """Manual lì xì minigame - users give lì xì to each other."""

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_envelopes: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Lì Xì Tặng Bạn"

    def _get_config(self, event: Any) -> dict[str, Any]:
        """Get minigame config from event with fallbacks."""
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("lixi_manual", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def create_envelope(
        self,
        interaction: Interaction,
        total_amount: int,
        num_envelopes: int,
        message: str | None = None,
    ) -> bool:
        """Create a new lì xì envelope for others to claim.

        Args:
            interaction: Discord interaction from the creator.
            total_amount: Total currency to distribute.
            num_envelopes: Number of people who can claim.
            message: Optional message from the creator.

        Returns:
            bool: True if envelope was created successfully.
        """
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return False

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện nào đang diễn ra!", ephemeral=True)
            return False

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy thông tin sự kiện!", ephemeral=True)
            return False

        config = self._get_config(event)
        min_amount = config.get("min_amount", 10)
        max_amount = config.get("max_amount", 1000)
        max_claims = config.get("max_claims", 10)
        timeout = config.get("timeout_seconds", 300)

        if total_amount < min_amount:
            await interaction.response.send_message(
                f"❌ Số tiền tối thiểu là **{min_amount} {event.currency_emoji}**!", ephemeral=True
            )
            return False

        if total_amount > max_amount:
            await interaction.response.send_message(
                f"❌ Số tiền tối đa là **{max_amount} {event.currency_emoji}**!", ephemeral=True
            )
            return False

        if num_envelopes < 1 or num_envelopes > max_claims:
            await interaction.response.send_message(
                f"❌ Số phần lì xì phải từ 1 đến {max_claims}!", ephemeral=True
            )
            return False

        if total_amount < num_envelopes:
            await interaction.response.send_message(
                "❌ Số tiền phải lớn hơn hoặc bằng số phần lì xì!", ephemeral=True
            )
            return False

        from ..services import get_currency

        balance = await get_currency(guild_id, user_id, active["event_id"])
        if balance < total_amount:
            await interaction.response.send_message(
                f"❌ Bạn không đủ tiền! Cần **{total_amount} {event.currency_emoji}** nhưng chỉ có **{balance} {event.currency_emoji}**.",
                ephemeral=True,
            )
            return False

        await add_currency(guild_id, user_id, active["event_id"], -total_amount)

        expire_time = datetime.now() + timedelta(seconds=timeout)

        amounts = self._distribute_amounts(total_amount, num_envelopes)

        embed = discord.Embed(
            title="🧧 LÌ XÌ TỪ " + interaction.user.display_name.upper() + "!",
            description=message or "Chúc mừng năm mới! 🎊",
            color=event.color,
        )
        embed.add_field(name="💰 Tổng giá trị", value=f"{total_amount} {event.currency_emoji}", inline=True)
        embed.add_field(name="🎁 Còn lại", value=f"{num_envelopes}/{num_envelopes} phần", inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)
        embed.set_footer(text=f"Người tặng: {interaction.user.display_name}")

        await interaction.response.send_message("🧧 Đang tạo lì xì...", ephemeral=True)

        view = LixiManualView(self, guild_id, active["event_id"], expire_time)
        channel = interaction.channel
        if channel is None or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return False

        msg = await channel.send(embed=embed, view=view)

        self._active_envelopes[msg.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "creator_id": user_id,
            "total_amount": total_amount,
            "amounts": amounts,
            "claims": {},
            "expire_time": expire_time,
            "message": msg,
            "custom_message": message,
        }

        await interaction.edit_original_response(content=f"✅ Đã tạo lì xì với **{total_amount} {event.currency_emoji}** cho {num_envelopes} người!")
        return True

    def _distribute_amounts(self, total: int, num_parts: int) -> list[int]:
        """Distribute total amount into random parts.

        Uses a fair random algorithm that ensures:
        - Each part gets at least 1
        - Total sums to exactly the input total
        """
        if num_parts == 1:
            return [total]

        amounts = [1] * num_parts
        remaining = total - num_parts

        for _ in range(remaining):
            idx = random.randint(0, num_parts - 1)
            amounts[idx] += 1

        random.shuffle(amounts)
        return amounts

    async def claim_envelope(self, interaction: Interaction, message_id: int) -> None:
        """Claim a lì xì envelope."""
        data = self._active_envelopes.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Lì xì này đã hết hiệu lực!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await self._expire_envelope(data)
            await interaction.response.send_message("❌ Lì xì đã hết hạn!", ephemeral=True)
            return

        user_id = interaction.user.id

        if user_id == data["creator_id"]:
            await interaction.response.send_message("❌ Bạn không thể nhận lì xì của chính mình!", ephemeral=True)
            return

        if user_id in data["claims"]:
            await interaction.response.send_message("❌ Bạn đã nhận lì xì này rồi!", ephemeral=True)
            return

        if not data["amounts"]:
            await interaction.response.send_message("❌ Lì xì đã hết!", ephemeral=True)
            return

        reward = data["amounts"].pop()
        data["claims"][user_id] = reward

        await add_currency(data["guild_id"], user_id, data["event_id"], reward)
        await add_contribution(data["guild_id"], user_id, data["event_id"], reward)
        await update_community_progress(data["guild_id"], reward)

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🌸"

        await interaction.response.send_message(f"🧧 Bạn nhận được **+{reward} {emoji}**!", ephemeral=True)

        if not data["amounts"]:
            await self._end_envelope(data)
        else:
            await self._update_envelope_embed(data)

    async def _update_envelope_embed(self, data: dict) -> None:
        """Update the envelope embed with remaining claims."""
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🌸"

        total_parts = len(data["amounts"]) + len(data["claims"])
        remaining = len(data["amounts"])

        creator = self.bot.get_user(data["creator_id"])
        creator_name = creator.display_name if creator else "Ai đó"

        embed = discord.Embed(
            title=f"🧧 LÌ XÌ TỪ {creator_name.upper()}!",
            description=data.get("custom_message") or "Chúc mừng năm mới! 🎊",
            color=event.color if event else 0xFFB7C5,
        )
        embed.add_field(name="💰 Tổng giá trị", value=f"{data['total_amount']} {emoji}", inline=True)
        embed.add_field(name="🎁 Còn lại", value=f"{remaining}/{total_parts} phần", inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(data['expire_time'].timestamp())}:R>", inline=True)
        embed.set_footer(text=f"Người tặng: {creator_name}")

        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            pass

    async def _end_envelope(self, data: dict) -> None:
        """End an envelope when all claims are taken."""
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🌸"

        creator = self.bot.get_user(data["creator_id"])
        creator_name = creator.display_name if creator else "Ai đó"

        claims_text = []
        for user_id, amount in data["claims"].items():
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            claims_text.append(f"🎁 {name}: +{amount} {emoji}")

        embed = discord.Embed(
            title="🧧 LÌ XÌ ĐÃ HẾT!",
            description=f"**Từ {creator_name}**\n\n" + "\n".join(claims_text) if claims_text else "Không ai nhận!",
            color=event.color if event else 0xFFB7C5,
        )

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_envelopes.pop(message.id, None)

    async def _expire_envelope(self, data: dict) -> None:
        """Handle envelope expiration - refund unclaimed amounts."""
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🌸"

        refund = sum(data["amounts"])
        if refund > 0:
            await add_currency(data["guild_id"], data["creator_id"], data["event_id"], refund)

        creator = self.bot.get_user(data["creator_id"])
        creator_name = creator.display_name if creator else "Ai đó"

        claims_text = []
        for user_id, amount in data["claims"].items():
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            claims_text.append(f"🎁 {name}: +{amount} {emoji}")

        desc = f"**Từ {creator_name}**\n\n"
        if claims_text:
            desc += "\n".join(claims_text)
        else:
            desc += "Không ai nhận!"

        if refund > 0:
            desc += f"\n\n💸 Hoàn trả **{refund} {emoji}** cho {creator_name}"

        embed = discord.Embed(
            title="🧧 LÌ XÌ ĐÃ HẾT HẠN!",
            description=desc,
            color=event.color if event else 0xFFB7C5,
        )

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_envelopes.pop(message.id, None)


class LixiManualView(discord.ui.View):
    minigame: LixiManualMinigame

    def __init__(
        self,
        minigame: LixiManualMinigame,
        guild_id: int,
        event_id: str,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.expire_time = expire_time

    @discord.ui.button(label="🧧 Nhận Lì Xì", style=discord.ButtonStyle.danger)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.message:
            await self.minigame.claim_envelope(interaction, interaction.message.id)

    async def on_timeout(self) -> None:
        for msg_id, data in list(self.minigame._active_envelopes.items()):
            if data.get("message") and data["message"].id == msg_id:
                if datetime.now() > data["expire_time"]:
                    await self.minigame._expire_envelope(data)
