"""High level manager that keeps track of werewolf matches per guild."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional, Set, Tuple

import discord

from ..roles.base import Expansion
from .game import WerewolfGame
from database_manager import db_manager, get_server_config
from core.logging import get_logger

logger = get_logger("WerewolfManager")

DB_PATH = "./data/database.db"


class WerewolfManager:
    """Entry point used by the cog to manage matches."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._games: Dict[Tuple[int, Optional[int]], WerewolfGame] = {}
        self._lock = asyncio.Lock()
        logger.info("[Werewolf] Manager initialized")
        
        # Setup centralized voice listener for all games
        self._voice_listener_registered = False
        self._setup_global_voice_listener()

    async def cleanup_orphaned_permissions(self) -> None:
        """Clean up orphaned werewolf game categories.
        
        Scans for categories starting with "🐺 Ma Sói" and deletes them if:
        - Age > 4 hours, OR
        - Inactive (last message in text channel) > 1 hour
        """
        from datetime import datetime, timezone
        
        logger.info("[Werewolf] Starting cleanup of orphaned game categories")
        cleaned_count = 0
        
        for guild in self.bot.guilds:
            try:
                for category in guild.categories:
                    # Check if it's a werewolf category
                    if not category.name.startswith("🐺 Ma Sói"):
                        continue
                    
                    # Verify structure (has text channel)
                    text_channel = None
                    for channel in category.channels:
                        if "diễn-biến" in channel.name:
                            text_channel = channel
                            break
                    
                    if not text_channel:
                        logger.warning(
                            "[Werewolf] Skipping invalid category | guild=%s name=%s",
                            guild.id, category.name
                        )
                        continue
                    
                    # Check if should delete
                    should_delete = False
                    reason = None
                    
                    # Method 1: Age check (>4 hours)
                    age_hours = (datetime.now(timezone.utc) - category.created_at).total_seconds() / 3600
                    if age_hours > 4:
                        should_delete = True
                        reason = f"Age: {age_hours:.1f}h"
                    
                    # Method 2: Inactivity check (>1 hour since last message)
                    if not should_delete:
                        try:
                            last_message = None
                            async for msg in text_channel.history(limit=1):
                                last_message = msg
                                break
                            
                            if last_message:
                                inactive_hours = (datetime.now(timezone.utc) - last_message.created_at).total_seconds() / 3600
                                if inactive_hours > 1:
                                    should_delete = True
                                    reason = f"Inactive: {inactive_hours:.1f}h"
                        except discord.HTTPException:
                            pass
                    
                    # Delete if criteria met
                    if should_delete:
                        try:
                            await category.delete(reason=f"Werewolf: Cleanup - {reason}")
                            cleaned_count += 1
                            logger.info(
                                "[Werewolf] Deleted orphaned category | guild=%s name=%s reason=%s",
                                guild.id, category.name, reason
                            )
                        except Exception as e:
                            logger.error(
                                "[Werewolf] Failed to delete category | guild=%s name=%s error=%s",
                                guild.id, category.name, e
                            )
            
            except Exception as e:
                logger.error("[Werewolf] Error cleaning guild %s: %s", guild.id, e)
        
        logger.info("[Werewolf] Cleanup complete | categories_deleted=%s", cleaned_count)

    def _setup_global_voice_listener(self) -> None:
        """Setup centralized voice state listener for ALL werewolf games.
        
        Fixes P0 vulnerabilities across all games:
        - Dead players reconnecting to speak
        - Alive players joining during night to avoid mute
        
        This single listener handles all active games to avoid listener overwrites.
        """
        if hasattr(self, '_voice_listener_registered') and self._voice_listener_registered:
            return
        
        @self.bot.event
        async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
            """Handle voice state changes for all werewolf games."""
            # Import here to avoid circular dependency
            from .state import Phase
            
            # Skip if not joining a voice channel
            if not after.channel:
                return
            
            # Check all active games to find matching voice channel
            async with self._lock:
                games_to_check = list(self._games.items())
            
            for (guild_id, vc_id), game in games_to_check:
                # Skip if game finished or not in this voice channel
                # Check game.voice_channel directly since dict key may still be (guild_id, None)
                game_vc_id = game.voice_channel.id if game.voice_channel else vc_id
                if game.is_finished or game_vc_id != after.channel.id:
                    continue
                
                # Check if member is a player in this game
                player = game.players.get(member.id)
                if not player:
                    continue
                
                try:
                    # CASE 1: Dead player reconnected → re-mute immediately
                    if not player.alive:
                        await member.edit(mute=True, reason="Werewolf: Dead player auto-muted on reconnect")
                        logger.warning(
                            "Re-muted dead player on reconnect | guild=%s player=%s",
                            guild_id, member.id
                        )
                    
                    # CASE 2: Alive player joined during night → mute immediately
                    elif game.phase == Phase.NIGHT and not before.channel:
                        # Player just joined (wasn't in voice before)
                        await member.edit(mute=True, reason="Werewolf: Joined during night phase")
                        logger.info(
                            "Muted alive player joining during night | guild=%s player=%s phase=%s",
                            guild_id, member.id, game.phase.name
                        )
                except discord.HTTPException as e:
                    logger.error(
                        "Failed to enforce voice mute | guild=%s player=%s error=%s",
                        guild_id, member.id, str(e)
                    )
                
                # Found the game, no need to check others
                break
        
        self._voice_listener_registered = True
        logger.info("[Werewolf] Global voice state listener registered")

    async def _get_voice_channel_id(self, guild_id: int) -> Optional[int]:
        """Retrieve voice channel ID from database for guild."""
        try:
            return await get_server_config(guild_id, "werewolf_voice_channel_id")
        except Exception as e:
            return None

    async def create_game(
        self,
        guild: discord.Guild,
        host: discord.Member,
        expansions: Set[Expansion],
        lobby_channel: discord.TextChannel,
    ) -> WerewolfGame:
        """Create new werewolf game instance.
        
        Args:
            guild: Discord guild
            host: Game host
            expansions: Set of expansions to use
            lobby_channel: Public channel where game was created
        
        Returns:
            New WerewolfGame instance
        """
        async with self._lock:
            if guild is None:
                raise RuntimeError("Lệnh này chỉ dùng trong máy chủ.")
            
            # NOTE: Game tracking will be by category_id after infrastructure creation
            # For now, allow creation (will update key in start())
            
            game = WerewolfGame(
                bot=self.bot,
                guild=guild,
                host=host,
                expansions=expansions,
                lobby_channel=lobby_channel
            )
            
            # Temporary: track by guild only during lobby phase
            # Will update to (guild_id, category_id) after start()
            temp_key = (guild.id, None)
            if temp_key in self._games and not self._games[temp_key].is_finished:
                raise RuntimeError("Đã có bàn ma sói đang chạy trong server này")
            
            self._games[temp_key] = game
            return game

    async def get_game(self, guild_id: int, voice_channel_id: Optional[int] = None) -> Optional[WerewolfGame]:
        """Get active game for guild. Returns None if no game or game is finished."""
        async with self._lock:
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
        """Stop all games with timeout protection."""
        async with self._lock:
            games = list(self._games.values())
            self._games.clear()
        for game in games:
            try:
                await asyncio.wait_for(game.cleanup(), timeout=10)
            except asyncio.TimeoutError:
                logger.warning(f"[Werewolf] Game cleanup timeout for guild {game.guild.id}")
            except Exception as e:
                logger.error(f"[Werewolf] Error during game cleanup: {e}", exc_info=True)

    async def save_game_state(self, guild_id: int, voice_channel_id: Optional[int] = None) -> None:
        """Save Werewolf game state to database for resume after restart"""
        async with self._lock:
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
                
                # Check if session exists (proper NULL handling)
                if voice_channel_id is None:
                    existing = await db_manager.fetchone(
                        "SELECT id FROM game_sessions WHERE guild_id = ? AND game_type = ? AND voice_channel_id IS NULL",
                        (guild_id, "werewolf")
                    )
                else:
                    existing = await db_manager.fetchone(
                        "SELECT id FROM game_sessions WHERE guild_id = ? AND game_type = ? AND voice_channel_id = ?",
                        (guild_id, "werewolf", voice_channel_id)
                    )
                
                if existing:
                    # Update existing session
                    if voice_channel_id is None:
                        await db_manager.modify(
                            "UPDATE game_sessions SET channel_id = ?, game_state = ?, last_saved = CURRENT_TIMESTAMP WHERE guild_id = ? AND game_type = ? AND voice_channel_id IS NULL",
                            (game.channel.id, game_state_json, guild_id, "werewolf")
                        )
                    else:
                        await db_manager.modify(
                            "UPDATE game_sessions SET channel_id = ?, game_state = ?, last_saved = CURRENT_TIMESTAMP WHERE guild_id = ? AND game_type = ? AND voice_channel_id = ?",
                            (game.channel.id, game_state_json, guild_id, "werewolf", voice_channel_id)
                        )
                else:
                    # Insert new session
                    await db_manager.modify(
                        "INSERT INTO game_sessions (guild_id, game_type, voice_channel_id, channel_id, game_state) VALUES (?, ?, ?, ?, ?)",
                        (guild_id, "werewolf", voice_channel_id, game.channel.id, game_state_json)
                    )
                
                logger.info(f"[Werewolf] GAME_SAVED [Guild {guild_id}] Phase: {game.phase.name}, Night: {game.night_number}, Day: {game.day_number}, Players: {len(game.players)}")
            except Exception as e:
                logger.error(f"[Werewolf] ERROR saving game state: {e}", exc_info=True)

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
                logger.info(f"[Werewolf] GAME_STATES_LOADED [Guild {guild_id}] {len(states)} game(s)")
            return states
        except Exception as e:
            logger.error(f"[Werewolf] ERROR loading game states: {e}", exc_info=True)
            return []
