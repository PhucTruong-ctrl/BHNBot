"""High level manager that keeps track of werewolf matches per guild."""

from __future__ import annotations

import asyncio
from typing import Dict, Optional, Set

import aiosqlite
import discord

from ..roles.base import Expansion
from .game import WerewolfGame

DB_PATH = "./data/database.db"


class WerewolfManager:
    """Entry point used by the cog to manage matches."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._games: Dict[int, WerewolfGame] = {}
        self._lock = asyncio.Lock()

    async def _get_voice_channel_id(self, guild_id: int) -> Optional[int]:
        """Retrieve voice channel ID from database for guild."""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT werewolf_voice_channel_id FROM server_config WHERE guild_id = ?",
                    (guild_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            return None

    async def create_game(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        host: discord.Member,
        expansions: Set[Expansion],
        game_mode: str = "text",
    ) -> WerewolfGame:
        async with self._lock:
            if guild is None or channel is None:
                raise RuntimeError("Lệnh này chỉ dùng trong máy chủ.")
            if guild.id in self._games and not self._games[guild.id].is_finished:
                raise RuntimeError("Đã có bàn ma sói đang chạy ở máy chủ này")
            
            # Retrieve voice channel ID from database only if mode is "voice"
            voice_channel_id = None
            if game_mode == "voice":
                voice_channel_id = await self._get_voice_channel_id(guild.id)
            
            game = WerewolfGame(self.bot, guild, channel, host, expansions, voice_channel_id=voice_channel_id, game_mode=game_mode)
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
