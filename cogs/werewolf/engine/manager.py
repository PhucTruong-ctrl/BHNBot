"""High level manager that keeps track of werewolf matches per guild."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Optional, Set

import discord

from ..roles.base import Expansion
from .game import WerewolfGame
from database_manager import db_manager, get_server_config

DB_PATH = "./data/database.db"


class WerewolfManager:
    """Entry point used by the cog to manage matches."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._games: Dict[Tuple[int, Optional[int]], WerewolfGame] = {}
        self._lock = asyncio.Lock()

    async def _get_voice_channel_id(self, guild_id: int) -> Optional[int]:
        """Retrieve voice channel ID from database for guild."""
        try:
            return await get_server_config(guild_id, "werewolf_voice_channel_id")
        except Exception as e:
            return None

    async def create_game(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        host: discord.Member,
        expansions: Set[Expansion],
        game_mode: str = "text",
        voice_channel_id: Optional[int] = None,
    ) -> WerewolfGame:
        async with self._lock:
            if guild is None or channel is None:
                raise RuntimeError("Lệnh này chỉ dùng trong máy chủ.")
            if (guild.id, voice_channel_id) in self._games and not self._games[(guild.id, voice_channel_id)].is_finished:
                raise RuntimeError("Đã có bàn ma sói đang chạy ở kênh này")
            
            # Use provided voice channel ID if mode is "voice"
            if game_mode == "voice":
                if voice_channel_id is None:
                    raise RuntimeError("Voice mode yêu cầu voice_channel_id.")
            
            game = WerewolfGame(self.bot, guild, channel, host, expansions, voice_channel_id=voice_channel_id, game_mode=game_mode)
            self._games[(guild.id, voice_channel_id)] = game
            return game

    def get_game(self, guild_id: int, voice_channel_id: Optional[int] = None) -> Optional[WerewolfGame]:
        key = (guild_id, voice_channel_id)
        game = self._games.get(key)
        if game and game.is_finished:
            self._games.pop(key, None)
            return None
        return game

    async def remove_game(self, guild_id: int, voice_channel_id: Optional[int] = None) -> None:
        async with self._lock:
            key = (guild_id, voice_channel_id)
            game = self._games.pop(key, None)
            if game:
                await game.cleanup()

    async def stop_all(self) -> None:
        async with self._lock:
            games = list(self._games.values())
            self._games.clear()
        for game in games:
            await game.cleanup()

    async def save_game_state(self, guild_id: int, voice_channel_id: Optional[int] = None) -> None:
        """Save Werewolf game state to database for resume after restart"""
        try:
            game = self._games.get((guild_id, voice_channel_id))
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
            
            # Check if session exists
            existing = await db_manager.fetchone(
                "SELECT id FROM game_sessions WHERE guild_id = ? AND game_type = ? AND voice_channel_id IS ?",
                (guild_id, "werewolf", voice_channel_id)
            )
            
            if existing:
                # Update existing session
                await db_manager.modify(
                    "UPDATE game_sessions SET channel_id = ?, game_state = ?, last_saved = CURRENT_TIMESTAMP WHERE guild_id = ? AND game_type = ? AND voice_channel_id IS ?",
                    (game.channel.id, game_state_json, guild_id, "werewolf", voice_channel_id)
                )
            else:
                # Insert new session
                await db_manager.modify(
                    "INSERT INTO game_sessions (guild_id, game_type, voice_channel_id, channel_id, game_state) VALUES (?, ?, ?, ?, ?)",
                    (guild_id, "werewolf", voice_channel_id, game.channel.id, game_state_json)
                )
            
            print(f"[Werewolf] GAME_SAVED [Guild {guild_id}] Phase: {game.phase.name}, Night: {game.night_number}, Day: {game.day_number}, Players: {len(game.players)}")
        except Exception as e:
            print(f"[Werewolf] ERROR saving game state: {e}")

    async def restore_game_state(self, guild_id: int) -> List[dict]:
        """Retrieve saved Werewolf game states from database (returns list of state dicts)"""
        try:
            rows = await db_manager.execute(
                "SELECT game_state, channel_id, voice_channel_id FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                (guild_id, "werewolf")
            )
            
            states = []
            for row in rows:
                game_state = json.loads(row[0])
                channel_id = row[1]
                voice_channel_id = row[2]
                game_state["channel_id"] = channel_id
                game_state["voice_channel_id"] = voice_channel_id
                states.append(game_state)
            
            if states:
                print(f"[Werewolf] GAME_STATES_LOADED [Guild {guild_id}] {len(states)} game(s)")
            return states
        except Exception as e:
            print(f"[Werewolf] ERROR loading game states: {e}")
            return []
