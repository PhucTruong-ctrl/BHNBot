"""High level manager that keeps track of werewolf matches per guild."""

from __future__ import annotations

import asyncio
from typing import Dict, Optional, Set

import discord

from ..roles.base import Expansion
from .game import WerewolfGame


class WerewolfManager:
    """Entry point used by the cog to manage matches."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._games: Dict[int, WerewolfGame] = {}
        self._lock = asyncio.Lock()

    async def create_game(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        host: discord.Member,
        expansions: Set[Expansion],
    ) -> WerewolfGame:
        async with self._lock:
            if guild is None or channel is None:
                raise RuntimeError("Lệnh này chỉ dùng trong máy chủ.")
            if guild.id in self._games and not self._games[guild.id].is_finished:
                raise RuntimeError("Đã có bàn ma sói đang chạy ở máy chủ này")
            game = WerewolfGame(self.bot, guild, channel, host, expansions)
            self._games[guild.id] = game
            return game

    def get_game(self, guild_id: int) -> Optional[WerewolfGame]:
        game = self._games.get(guild_id)
        if game and game.is_finished:
            self._games.pop(guild_id, None)
            return None
        return game

    async def remove_game(self, guild_id: int) -> None:
        async with self._lock:
            game = self._games.pop(guild_id, None)
            if game:
                await game.cleanup()

    async def stop_all(self) -> None:
        async with self._lock:
            games = list(self._games.values())
            self._games.clear()
        for game in games:
            await game.cleanup()
