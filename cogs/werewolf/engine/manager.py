"""High level manager that keeps track of werewolf matches per guild."""

from __future__ import annotations

import asyncio
import json
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

    async def save_game_state(self, guild_id: int) -> None:
        """Save Werewolf game state to database for resume after restart"""
        try:
            game = self._games.get(guild_id)
            if not game or game.is_finished:
                return
            
            # Build game state snapshot
            game_state = {
                "phase": game.phase.name,
                "night_number": game.night_number,
                "day_number": game.day_number,
                "players": {
                    str(pid): {
                        "member_id": p.member.id,
                        "member_name": p.display_name(),
                        "alive": p.alive,
                        "death_pending": p.death_pending,
                        "roles": [{"name": role.metadata.name, "alignment": role.alignment.name} for role in p.roles],
                        "lover_id": p.lover_id,
                        "charmed": p.charmed,
                        "vote_disabled": p.vote_disabled,
                        "skills_disabled": p.skills_disabled,
                        "mayor": p.mayor,
                        "vote_weight": p.vote_weight,
                        "protected_last_night": p.protected_last_night,
                        "is_sister": p.is_sister,
                        "marked_by_raven": p.marked_by_raven
                    }
                    for pid, p in game.players.items()
                },
                "host_id": game.host.id,
                "expansions": [e.name for e in game.settings.expansions],
                "game_mode": game.game_mode,
                "voice_channel_id": game.voice_channel_id,
                "wolf_thread_id": game._wolf_thread.id if game._wolf_thread else None,
                "piper_id": game._piper_id,
                "lovers": list(game._lovers),
                "charmed": list(game._charmed),
                "sisters_ids": game._sisters_ids,
                "pyro_soaked": list(game._pyro_soaked),
                "pyro_id": game._pyro_id,
                "angel_won": game._angel_won,
                "wolf_brother_id": game._wolf_brother_id,
                "wolf_sister_id": game._wolf_sister_id,
                "elder_man_id": game._elder_man_id,
                "elder_man_group1": game._elder_man_group1,
                "elder_man_group2": game._elder_man_group2,
                "devoted_servant_id": game._devoted_servant_id
            }
            
            game_state_json = json.dumps(game_state)
            
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if session exists
                async with db.execute(
                    "SELECT id FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                    (guild_id, "werewolf")
                ) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    # Update existing session
                    await db.execute(
                        "UPDATE game_sessions SET channel_id = ?, game_state = ?, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ? AND game_type = ?",
                        (game.channel.id, game_state_json, guild_id, "werewolf")
                    )
                else:
                    # Insert new session
                    await db.execute(
                        "INSERT INTO game_sessions (guild_id, game_type, channel_id, game_state) VALUES (?, ?, ?, ?)",
                        (guild_id, "werewolf", game.channel.id, game_state_json)
                    )
                await db.commit()
            
            print(f"[Werewolf] GAME_SAVED [Guild {guild_id}] Phase: {game.phase.name}, Night: {game.night_number}, Day: {game.day_number}, Players: {len(game.players)}")
        except Exception as e:
            print(f"[Werewolf] ERROR saving game state: {e}")

    async def restore_game_state(self, guild_id: int) -> Optional[dict]:
        """Retrieve saved Werewolf game state from database (returns state dict or None)"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT game_state, channel_id FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                    (guild_id, "werewolf")
                ) as cursor:
                    row = await cursor.fetchone()
            
            if not row:
                return None
            
            game_state = json.loads(row[0])
            channel_id = row[1]
            game_state["channel_id"] = channel_id
            
            print(f"[Werewolf] GAME_STATE_LOADED [Guild {guild_id}] Phase: {game_state.get('phase')}, Players: {len(game_state.get('players', {}))}")
            return game_state
        except Exception as e:
            print(f"[Werewolf] ERROR loading game state: {e}")
            return None
