"""Modal components for seasonal events."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ..minigames.thank_letter import ThankLetterMinigame
    from ..minigames.secret_santa import SecretSantaMinigame
    from ..minigames.wishes import WishesMinigame


class ThankLetterModal(discord.ui.Modal, title="Gửi Thư Cảm Ơn"):
    message = discord.ui.TextInput(
        label="Lời cảm ơn của bạn",
        style=discord.TextStyle.paragraph,
        placeholder="Viết lời cảm ơn chân thành...",
        min_length=10,
        max_length=500,
        required=True,
    )

    def __init__(self, minigame: ThankLetterMinigame, receiver: discord.User) -> None:
        super().__init__()
        self.minigame = minigame
        self.receiver = receiver

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.minigame.process_letter(interaction, self.receiver, self.message.value)


class GiftMessageModal(discord.ui.Modal, title="Lời Nhắn Tặng Quà"):
    message = discord.ui.TextInput(
        label="Lời nhắn của bạn",
        style=discord.TextStyle.paragraph,
        placeholder="Viết lời chúc cho người nhận...",
        min_length=5,
        max_length=300,
        required=True,
    )

    def __init__(self, minigame: SecretSantaMinigame) -> None:
        super().__init__()
        self.minigame = minigame

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.minigame.submit_gift_message(interaction, self.message.value)


class BirthdayWishModal(discord.ui.Modal, title="Lời Chúc Sinh Nhật"):
    message = discord.ui.TextInput(
        label="Lời chúc của bạn",
        style=discord.TextStyle.paragraph,
        placeholder="Viết lời chúc mừng sinh nhật...",
        min_length=10,
        max_length=200,
        required=True,
    )

    def __init__(self, minigame: WishesMinigame) -> None:
        super().__init__()
        self.minigame = minigame

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.minigame.process_wish(interaction, self.message.value)
