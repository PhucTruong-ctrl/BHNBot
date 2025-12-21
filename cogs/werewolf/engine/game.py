"""Core orchestration for The Werewolves of Miller's Hollow implementation."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from collections import Counter
from typing import Dict, List, Optional, Sequence, Set, Tuple

import discord
from discord import abc as discord_abc

from .role_config import RoleConfig
from database_manager import db_manager
from ..roles import get_role_class, load_all_roles
from ..roles.base import Alignment, Expansion, Role
from .state import GameSettings, Phase, PlayerState
from .voting import VoteSession
from core.logger import setup_logger

DB_PATH = "./data/database.db"
CARD_BACK_URL = "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/banner.png"
# Lowered to 4 for easier local testing; raise back to 6 for production balance
MIN_PLAYERS = 4

load_all_roles()

logger = setup_logger("WerewolfGame", "cogs/werewolf/werewolf.log")


class WerewolfGame:
    """Single running match of Werewolf."""

    def __init__(
        self,
        bot: discord.Client,
        guild: discord.Guild,
        channel: discord.TextChannel,
        host: discord.Member,
        expansions: Set[Expansion],
        voice_channel_id: Optional[int] = None,
        game_mode: str = "text",
    ) -> None:
        self.bot = bot
        self.guild = guild
        self.channel = channel
        self.host = host
        self.voice_channel_id = voice_channel_id
        self.game_mode = game_mode  # "text" or "voice"
        self.werewolf_role: Optional[discord.Role] = None
        self.settings = GameSettings(expansions=set(expansions))
        self.players: Dict[int, PlayerState] = {}
        self.phase = Phase.LOBBY
        self.night_number = 0
        self.day_number = 0
        self.is_finished = False
        self._winner: Optional[Alignment] = None
        self._loop_task: Optional[asyncio.Task] = None
        self._wolf_thread: Optional[discord.Thread] = None
        self._lobby_message: Optional[discord.Message] = None
        self._player_role: Optional[discord.Role] = None  # Role for game participants
        self._lobby_view: Optional[_LobbyView] = None
        # (player_id, cause) where cause in {wolves, white_wolf, witch, pyro, hunter, lynch, lover, scapegoat}
        self._pending_deaths: List[Tuple[int, str]] = []
        self._lovers: Set[int] = set()
        self._charmed: Set[int] = set()
        self._piper_id: Optional[int] = None
        self._stop_event = asyncio.Event()
        self._death_log: List[Tuple[int, str, str]] = []
        self._little_girl_peeking: Optional[int] = None  # Little girl user_id if peeking this night
        self._sisters_ids: List[int] = []  # Two Sisters player IDs
        self._sisters_thread: Optional[discord.Thread] = None
        # Pyromaniac state: set of player IDs soaked in oil (max 6)
        self._pyro_soaked: Set[int] = set()
        self._pyro_id: Optional[int] = None  # Pyromaniac player ID
        self._angel_won = False  # Track if Angel won on Day 1
        self._scapegoat_target: Optional[int] = None  # Target chosen by Scapegoat on tie vote
        self._demon_wolf_curse_target: Optional[int] = None  # Target cursed by Demon Wolf
        self._moon_maiden_disabled: Optional[int] = None  # Player disabled by Moon Maiden this night
        self._hypnotist_charm_target: Optional[int] = None  # Player charmed by Hypnotist this night
        self._pharmacist_antidote_target: Optional[int] = None  # Player targeted by Pharmacist's antidote this night
        self._pharmacist_slept_target: Optional[int] = None  # Player targeted by Pharmacist's sleeping potion this night
        self._assassin_votes_day1: Dict[int, int] = {}  # Track votes day 1 of assassin cycle
        self._assassin_votes_day2: Dict[int, int] = {}  # Track votes day 2 of assassin cycle
        self._wolves_died_today: List[int] = []  # Track which wolves died during day (for Fire Wolf)
        self._wolf_brother_id: Optional[int] = None  # Wolf Brother player ID
        self._wolf_sister_id: Optional[int] = None  # Wolf Sister player ID
        self._judge_activated_double_lynch: bool = False  # Judge activated double lynch this day
        self._actor_protected_target: Optional[int] = None  # Target protected by Actor using Guard ability
        self._actor_heal_target: Optional[int] = None  # Target healed by Actor using Witch Heal ability
        self._actor_hunt_target: Optional[int] = None  # Target to hunt if Actor killed using Hunter ability
        self._actor_raven_target: Optional[int] = None  # Target cursed by Actor using Raven ability
        self._actor_harp_target: Optional[int] = None  # Target charmed by Actor using Hypnotist ability
        self._elder_man_id: Optional[int] = None  # Elder Man player ID
        self._elder_man_group1: List[int] = []  # Group 1 player IDs
        self._elder_man_group2: List[int] = []  # Group 2 player IDs
        self._devoted_servant_id: Optional[int] = None  # Devoted Servant player ID
        self._devoted_servant_stolen_role: Optional[Role] = None  # Stolen role by Devoted Servant
        self._devoted_servant_original_target: Optional[int] = None  # Original target of Devoted Servant swap

    async def open_lobby(self) -> None:
        self._lobby_view = _LobbyView(self)
        embed = self._build_lobby_embed()
        self._lobby_message = await self.channel.send(embed=embed, view=self._lobby_view)
        logger.info("Lobby opened | guild=%s channel=%s host=%s", self.guild.id, self.channel.id, self.host.id)

    def _build_lobby_embed(self) -> discord.Embed:
        player_lines = [f"- {player.display_name()}" for player in self.list_players()]
        players_text = "\n".join(player_lines) if player_lines else "Chưa có người tham gia"
        expansion_labels = {
            Expansion.NEW_MOON: "New Moon",
            Expansion.THE_VILLAGE: "The Village",
        }
        expansions = ", ".join(expansion_labels[exp] for exp in self.settings.expansions) if self.settings.expansions else "Bản cơ bản"
        embed = discord.Embed(
            title="Ma Sói – Werewolves of Miller's Hollow",
            description="Sử dụng nút bên dưới để tham gia. Chủ bàn có thể bật mở rộng.",
            colour=discord.Colour.dark_red(),
        )
        embed.add_field(name="Người tham gia", value=f"{len(self.players)} người\n{players_text}", inline=False)
        embed.add_field(name="Mở rộng", value=expansions, inline=False)
        embed.set_image(url=CARD_BACK_URL)
        return embed

    async def _refresh_lobby(self) -> None:
        if not self._lobby_message:
            return
        embed = self._build_lobby_embed()
        try:
            await self._lobby_message.edit(embed=embed)
        except discord.HTTPException:
            pass

    async def cleanup(self) -> None:
        self._stop_event.set()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task
        if self._lobby_message and not self.is_finished:
            try:
                await self._lobby_message.edit(content="Bàn chơi đã huỷ.", embed=None, view=None)
            except discord.HTTPException:
                pass
        if self._wolf_thread:
            try:
                await self._wolf_thread.delete()
            except discord.HTTPException:
                pass
        # Unmute all players in voice channel
        await self._unmute_voice(force_unmute_all=True)
        # Delete player role if it exists
        if self._player_role:
            try:
                await self._player_role.delete(reason="Werewolf: Game ended - cleanup role")
            except discord.HTTPException:
                pass
        # Delete werewolf role if it exists
        if self.werewolf_role:
            try:
                await self.werewolf_role.delete(reason="Werewolf: Game ended - cleanup role")
            except discord.HTTPException:
                pass
    
    async def _save_game_state(self) -> None:
        """Save current game state to database (called by game loop)"""
        try:
            from .manager import WerewolfManager
            # Get manager from bot cog
            cog = self.bot.get_cog("WerewolfCog")
            if not cog or not hasattr(cog, 'manager'):
                return
            
            await cog.manager.save_game_state(self.guild.id)
        except Exception as e:
            logger.error("Error saving game state: %s", str(e), exc_info=True)
    
    async def _delete_game_state(self) -> None:
        """Delete saved game state from database when game finishes"""
        try:
            await db_manager.modify(
                "DELETE FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                (self.guild.id, "werewolf")
            )
        except Exception as e:
            logger.error("Error deleting game state: %s", str(e), exc_info=True)

    def list_players(self) -> Sequence[PlayerState]:
        return list(self.players.values())

    def alive_players(self) -> List[PlayerState]:
        return [p for p in self.players.values() if p.alive and not p.death_pending]

    def _is_player_eligible_for_action(self, player: PlayerState) -> bool:
        """Check if player can take night/day actions (alive, not pending death, and not disabled by Fire Wolf)."""
        return player.alive and not player.death_pending and not player.skills_disabled

    def alive_by_alignment(self, alignment: Alignment) -> List[PlayerState]:
        result = [p for p in self.alive_players() if any(r.alignment == alignment for r in p.roles)]
        logger.info(">>> alive_by_alignment | guild=%s alignment=%s count=%s", 
                     self.guild.id, alignment.value, len(result))
        return result

    def get_active_werewolves(self, filter_alive: bool = True) -> List[PlayerState]:
        """Get werewolves excluding Avengers on werewolf side (they don't participate in wolf votes/actions)."""
        players_to_check = self.alive_players() if filter_alive else self.players.values()
        wolves = []
        for p in players_to_check:
            if any(r.alignment == Alignment.WEREWOLF for r in p.roles):
                # Check if this is an Avenger on werewolf side
                is_avenger_wolf_side = False
                for role in p.roles:
                    if hasattr(role, '__class__') and role.__class__.__name__ == 'Avenger':
                        if hasattr(role, 'chosen_side') and role.chosen_side == Alignment.WEREWOLF:
                            is_avenger_wolf_side = True
                            break
                
                # Only add if not an Avenger on werewolf side
                if not is_avenger_wolf_side:
                    wolves.append(p)
        
        return wolves

    async def add_player(self, member: discord_abc.User) -> None:
        if self.phase != Phase.LOBBY:
            raise RuntimeError("Không thể tham gia sau khi trận đấu đã bắt đầu")
        guild_member = member if isinstance(member, discord.Member) else self.guild.get_member(member.id)
        if guild_member is None:
            raise RuntimeError("Không thể xác định thành viên trong máy chủ")
        if guild_member.id in self.players:
            return
        self.players[guild_member.id] = PlayerState(member=guild_member)
        await self._refresh_lobby()
        logger.info("Player joined lobby | guild=%s channel=%s player=%s", self.guild.id, self.channel.id, guild_member.id)

    async def remove_player(self, member: discord_abc.User) -> None:
        if self.phase != Phase.LOBBY:
            raise RuntimeError("Không thể rời bàn sau khi trận đấu đã bắt đầu")
        guild_member = member if isinstance(member, discord.Member) else self.guild.get_member(member.id)
        if guild_member is None:
            return
        self.players.pop(guild_member.id, None)
        await self._refresh_lobby()
        logger.info("Player left lobby | guild=%s channel=%s player=%s", self.guild.id, self.channel.id, guild_member.id)

    async def toggle_expansion(self, expansion: Expansion) -> None:
        if self.phase != Phase.LOBBY:
            return
        if expansion in self.settings.expansions:
            self.settings.expansions.remove(expansion)
            logger.info("Expansion disabled | guild=%s expansion=%s", self.guild.id, expansion.value)
        else:
            self.settings.expansions.add(expansion)
            logger.info("Expansion enabled | guild=%s expansion=%s", self.guild.id, expansion.value)
        await self._refresh_lobby()

    async def start(self) -> None:
        if self.phase != Phase.LOBBY:
            raise RuntimeError("Bàn chơi đã khởi động")
        if len(self.players) < MIN_PLAYERS:
            raise RuntimeError("Cần ít nhất 6 người mới bắt đầu được")
        self.phase = Phase.NIGHT
        self.night_number = 1
        await self._assign_roles()
        await self._create_player_role()  # Create role and set permissions efficiently
        await self._notify_roles()
        await self._create_wolf_thread()
        await self._announce_role_composition()
        if self._lobby_message:
            try:
                await self._lobby_message.edit(content="Trận đấu đã bắt đầu", view=None)
            except discord.HTTPException:
                pass
        self._loop_task = asyncio.create_task(self._game_loop())
        logger.info("Game started | guild=%s channel=%s players=%s expansions=%s", self.guild.id, self.channel.id, len(self.players), list(self.settings.expansions))

    async def _game_loop(self) -> None:
        try:
            while not self.is_finished and not self._stop_event.is_set():
                await self._run_night()
                logger.info("After night: checking win condition | guild=%s night=%s", 
                            self.guild.id, self.night_number)
                try:
                    if self._check_win_condition():
                        logger.info("Game ending after night | guild=%s winner=%s", 
                                    self.guild.id, self._winner.value if self._winner else None)
                        break
                except Exception as e:
                    logger.error("Exception in _check_win_condition after night | guild=%s error=%s", 
                                self.guild.id, str(e), exc_info=True)
                    raise
                
                # Save game state after night
                await self._save_game_state()
                
                await self._run_day()
                logger.info("After day: checking win condition | guild=%s day=%s", 
                            self.guild.id, self.day_number)
                try:
                    if self._check_win_condition():
                        logger.info("Game ending after day | guild=%s winner=%s", 
                                    self.guild.id, self._winner.value if self._winner else None)
                        break
                except Exception as e:
                    logger.error("Exception in _check_win_condition after day | guild=%s error=%s", 
                                self.guild.id, str(e), exc_info=True)
                    raise
                
                # Save game state after day
                await self._save_game_state()
        finally:
            # Unmute all players and enable text chat before announcing winner
            await self._force_unmute_all()
            await self._enable_text_chat()
            await self._announce_winner()
            # Clear all channel permissions to reset for next game
            await self._clear_channel_permissions()
            self.is_finished = True
            if self._wolf_thread:
                with contextlib.suppress(discord.HTTPException):
                    await self._wolf_thread.delete()
            if self._sisters_thread:
                with contextlib.suppress(discord.HTTPException):
                    await self._sisters_thread.delete()
            
            # Delete saved game state when game finishes
            await self._delete_game_state()

    async def _run_night(self) -> None:
        self.phase = Phase.NIGHT
        for player in self.alive_players():
            player.reset_night_flags()
        # Announce night with embed
        embed = discord.Embed(
            title=f"🌙 Đêm {self.night_number}",
            description="Buông xuống. Tất cả đi ngủ.",
            colour=discord.Colour.dark_blue(),
        )
        embed.set_image(url=CARD_BACK_URL)
        await self.channel.send(embed=embed)
        await self._run_countdown(self.channel, f"Đêm {self.night_number}", self.settings.night_intro_duration)
        logger.info("Night start | guild=%s channel=%s night=%s", self.guild.id, self.channel.id, self.night_number)
        
        # Disable text chat and mute voice channel for night phase
        await self._disable_text_chat()
        if self.game_mode == "voice":
            await self._mute_voice()
        
        # Mute Werewolf Player role during night
        if self.werewolf_role and self.voice_channel_id:
            channel = self.bot.get_channel(self.voice_channel_id)
            if isinstance(channel, discord.VoiceChannel):
                await channel.set_permissions(self.werewolf_role, speak=False)
        
        # Wake Two Sisters on even nights (2, 4, 6...) for coordination
        if self.night_number % 2 == 0 and len(self._sisters_ids) == 2:
            await self._wake_sisters()

        await self._resolve_role_sequence(first_night=self.night_number == 1)
        await self._resolve_pending_deaths("night")
        self.night_number += 1

    async def _run_day(self) -> None:
        self.phase = Phase.DAY
        self.day_number += 1
        
        # Unmute Werewolf Player role during day
        if self.werewolf_role and self.voice_channel_id:
            channel = self.bot.get_channel(self.voice_channel_id)
            if isinstance(channel, discord.VoiceChannel):
                await channel.set_permissions(self.werewolf_role, speak=True)
        
        # Reset wolves died tracking for the new day
        self._wolves_died_today = []
        
        # Reset Judge double lynch flag for the new day
        self._judge_activated_double_lynch = False
        
        # Enable text chat and unmute voice channel for day phase
        await self._enable_text_chat()
        if self.game_mode == "voice":
            await self._unmute_voice()
        
        announcements = []
        new_deaths = [p for p in self.list_players() if not p.alive and p.death_pending]
        if new_deaths:
            deaths_text = ", ".join(p.display_name() for p in new_deaths)
            announcements.append(f"Sáng nay phát hiện {deaths_text} đã chết.")
        else:
            announcements.append("Sáng nay bình yên, không ai chết.")
        await self.channel.send("\n".join(announcements))
        for player in new_deaths:
            player.death_pending = False
        
        # Calculate dynamic discussion time based on alive players
        alive_count = len(self.alive_players())
        discussion_time = self.settings.calculate_discussion_time(alive_count)
        
        # NEW: Run discussion with skip vote feature
        await self._run_discussion_phase(alive_count, discussion_time)
        
        # Execute day phase role actions (e.g., Cavalry) before voting
        for player in self.alive_players():
            for role in player.roles:
                try:
                    await role.on_day(self, player, self.day_number)
                except Exception as e:
                    logger.error(
                        "Error in role on_day | guild=%s player=%s role=%s error=%s",
                        self.guild.id,
                        player.user_id,
                        role.metadata.name,
                        str(e),
                        exc_info=True,
                    )
        
        # Check if game is still running after day actions (cavalry may end it)
        if not self.is_finished:
            await self._run_day_vote()
        
        # Reset vote_disabled from Pharmacist's sleeping potion after day voting is complete
        for player in self.alive_players():
            player.vote_disabled = False
        logger.info("Day start | guild=%s channel=%s day=%s deaths=%s", self.guild.id, self.channel.id, self.day_number, [p.user_id for p in new_deaths])

    async def _resolve_pending_deaths(self, phase_label: str) -> None:
        if not self._pending_deaths:
            return
        # Deduplicate by player id while keeping first cause
        unique: Dict[int, str] = {}
        for pid, cause in self._pending_deaths:
            if pid not in unique:
                unique[pid] = cause
        
        # Store the list of died player IDs for wild child check BEFORE clearing
        died_players = list(unique.keys())
        
        # SECURITY: Only clear after we have copied the list
        self._pending_deaths.clear()
        
        try:
            for pid, cause in unique.items():
                player = self.players.get(pid)
                if not player:
                    logger.warning("Player not found for death resolution | guild=%s pid=%s", 
                                   self.guild.id, pid)
                    continue
                # SECURITY: Double-check player is alive and not already marked dead
                if not player.alive or player.death_pending:
                    logger.warning("Skipping death resolution for already-dead player | guild=%s player=%s", 
                                   self.guild.id, pid)
                    continue
                player.alive = False
                player.death_pending = True
                try:
                    await self._handle_death(player, cause=cause)
                except Exception as e:
                    logger.error(
                        "Error in _handle_death | guild=%s player=%s cause=%s error=%s",
                        self.guild.id, pid, cause, str(e), exc_info=True
                    )
                    # Continue processing other deaths even if one fails
        except Exception as e:
            logger.error(
                "Error in _resolve_pending_deaths | guild=%s error=%s",
                self.guild.id, str(e), exc_info=True
            )
        
        # Check if any wild children should transform
        try:
            await self._check_wild_child_transformation(died_players)
        except Exception as e:
            logger.error(
                "Error in _check_wild_child_transformation | guild=%s error=%s",
                self.guild.id, str(e), exc_info=True
            )

    async def _check_wild_child_transformation(self, died_player_ids: List[int]) -> None:
        """Check if any Wild Child should transform into werewolf."""
        from ..roles.villagers.wild_child import WildChild
        
        for player in self.players.values():
            if not player.alive or not player.roles:
                continue
            
            # Check if this player is a Wild Child
            wild_child = None
            for role in player.roles:
                if role.metadata.name == "Đứa Con Hoang":
                    wild_child = role
                    break
            
            if not wild_child:
                continue
            
            # Get the wild child role and check if chosen one died
            if not isinstance(wild_child, WildChild):
                continue
            
            # Check if the chosen one died
            if wild_child.chosen_one_id in died_player_ids:
                await wild_child.check_transformation(self, player, wild_child.chosen_one_id)

        # Check if Demon Wolf cursed someone
        if self._demon_wolf_curse_target:
            target_id = self._demon_wolf_curse_target
            target = self.players.get(target_id)
            
            if target and target.alive:
                # Add Werewolf role to the cursed player
                from ..roles.werewolves.werewolf import Werewolf
                target.add_role(Werewolf())
                
                # Add to wolf thread
                if self._wolf_thread:
                    await self._wolf_thread.add_user(target.member)
                
                # Notify the cursed player
                await target.member.send(
                    "Bạn đã bị Sói Quỷ nguyền rủa! Bạn sẽ trở thành Ma Sói từ đêm tiếp theo. Bạn vẫn giữ vai trò cũ."
                )
                
                # Notify wolves about new member
                if self._wolf_thread:
                    await self._wolf_thread.send(
                        f"{target.display_name()} đã được nguyền rủa thành Ma Sói! Họ sẽ gia nhập bầy từ đêm tiếp theo."
                    )
            
            self._demon_wolf_curse_target = None

    async def _run_day_vote(self) -> None:
        alive = self.alive_players()
        eligible: List[int] = []
        
        # Check if Scapegoat chose someone for automatic lynching today
        if self._scapegoat_target:
            target_player = self.players.get(self._scapegoat_target)
            if target_player and target_player.alive:
                await self.channel.send(f"Oan nhân đã chỉ định {target_player.display_name()} sẽ bị treo cổ ngày hôm nay.")
                target_player.alive = False
                await self._handle_death(target_player, cause="lynch")
                await self._resolve_pending_deaths("hunter")
                self._scapegoat_target = None  # Clear the target
                logger.info("Scapegoat target lynched | guild=%s player=%s", self.guild.id, target_player.user_id)
                return
            self._scapegoat_target = None  # Clear if target is dead
        
        if len(alive) <= 2:
            await self.channel.send("Không đủ người sống để bỏ phiếu ban ngày.")
            return
        eligible = [p.user_id for p in alive if not p.vote_disabled]
        logger.info("Day vote start | guild=%s day=%s eligible=%s", self.guild.id, self.day_number, eligible)
        options = {p.user_id: p.display_name() for p in alive}
        vote = VoteSession(
            self.bot,
            self.channel,
            title=f"Bỏ phiếu treo cổ ngày {self.day_number}",
            description="Chọn người mà bạn nghi ngờ là ma sói.",
            options=options,
            eligible_voters=eligible,
            duration=self.settings.day_vote_duration,
            allow_skip=True,
            vote_weights={p.user_id: p.vote_weight for p in alive},
        )
        result = await vote.start()
        tally = Counter(result.tally)
        
        # Track votes for Assassin (2-day cycle: day 1 & day 2)
        if self.day_number % 2 == 1:  # Odd days: 1, 3, 5...
            self._assassin_votes_day1 = dict(tally)
            logger.info("Assassin votes day 1 tracked | guild=%s day=%s votes=%s", self.guild.id, self.day_number, self._assassin_votes_day1)
        else:  # Even days: 2, 4, 6...
            self._assassin_votes_day2 = dict(tally)
            logger.info("Assassin votes day 2 tracked | guild=%s day=%s votes=%s", self.guild.id, self.day_number, self._assassin_votes_day2)
        
        # Apply Raven bonus (+2 phiếu)
        for player in alive:
            if player.marked_by_raven:
                tally[player.user_id] += 2
        
        # Apply Two Sisters bonus (+1 phiếu nếu cùng vote)
        if len(self._sisters_ids) == 2 and result.votes_by_voter:
            votes_by_voter = result.votes_by_voter
            sister1_vote = votes_by_voter.get(self._sisters_ids[0])
            sister2_vote = votes_by_voter.get(self._sisters_ids[1])
            
            if sister1_vote is not None and sister1_vote == sister2_vote:
                tally[sister1_vote] += 1
                logger.info("Sisters bonus vote applied | guild=%s day=%s target=%s", self.guild.id, self.day_number, sister1_vote)
        
        if not tally:
            await self.channel.send("Không có ai bị trưng cầu đủ phiếu.")
            return
        top = tally.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            # Check if Mayor/Captain is alive to break tie
            mayor = next((p for p in alive if p.mayor), None)
            if mayor:
                # Mayor breaks the tie
                tied = [pid for pid, count in top if count == top[0][1]]
                tie_options = {pid: self.players[pid].display_name() for pid in tied if pid in self.players}
                
                await self.channel.send(f"⚖️ Hòa phiếu! Trưởng Làng {mayor.display_name()} sẽ quyết định.")
                choice = await self._prompt_dm_choice(
                    mayor,
                    title="Trưởng Làng - Phá vỡ hòa phiếu",
                    description="Hòa phiếu xảy ra. Bạn quyết định ai sẽ bị treo cổ.",
                    options=tie_options,
                    allow_skip=False,
                    timeout=30,
                )
                
                if choice and choice in tie_options:
                    target_player = self.players.get(choice)
                    if target_player:
                        await self.channel.send(f"🎖️ Trưởng Làng đã quyết định: {target_player.display_name()} bị treo cổ.")
                        logger.info("Mayor broke tie | guild=%s mayor=%s target=%s", self.guild.id, mayor.user_id, choice)
                    else:
                        await self.channel.send("Dân làng tranh cãi không dứt, chưa ai bị treo cổ.")
                        logger.info("Day vote tie no execution | guild=%s day=%s", self.guild.id, self.day_number)
                        return
                else:
                    await self.channel.send("Trưởng Làng không quyết định được, không ai bị treo cổ.")
                    logger.info("Mayor failed to break tie | guild=%s day=%s", self.guild.id, self.day_number)
                    return
            else:
                # No mayor, check scapegoat
                scapegoat = self._find_role_holder("Oan Nhân")
                if scapegoat:
                    await self.channel.send("Lá phiếu bế tắc. Oan nhân phải ra đi thay làng.")
                    scapegoat.alive = False
                    await self._handle_death(scapegoat, cause="tie")
                    logger.info("Scapegoat executed due to tie | guild=%s player=%s", self.guild.id, scapegoat.user_id)
                    return
                await self.channel.send("Dân làng tranh cãi không dứt, chưa ai bị treo cổ.")
                logger.info("Day vote tie no execution | guild=%s day=%s", self.guild.id, self.day_number)
                return
        target_player = self.players.get(top[0][0])
        if not target_player:
            await self.channel.send("Không có kết quả rõ ràng.")
            return
        
        await self.channel.send(f"🎪 **{target_player.display_name()} bị đưa lên giàn treo cổ.**")
        
        # NEW: Defense Phase (Biện hộ)
        await self._run_defense_phase(target_player)
        
        # NEW: Judgment Phase (Biểu quyết sống/chết)
        should_execute = await self._run_judgment_phase(target_player)
        
        # Track fool hanged for achievement
        if should_execute and target_player.role and target_player.role.name == "Fool":
            target_player.fool_hanged = True
            logger.info("Fool hanged tracked | guild=%s fool=%s", self.guild.id, target_player.user_id)
        
        if not should_execute or not target_player.alive:
            # Player was spared or already dead from defense phase
            logger.info("Player spared or dead | guild=%s player=%s", self.guild.id, target_player.user_id)
            return
        
        # Proceed with execution
        await self._run_last_words_phase(target_player)
        
        # Check if Assassin should be activated (on even days after 2-day cycle)
        if self.day_number % 2 == 0:  # Even days: 2, 4, 6... (end of 2-day cycle)
            # Calculate total votes from both days
            assassin_votes_day1 = self._assassin_votes_day1.get(target_player.user_id, 0)
            assassin_votes_day2 = self._assassin_votes_day2.get(target_player.user_id, 0)
            total_assassin_votes = assassin_votes_day1 + assassin_votes_day2
            
            if total_assassin_votes >= 4:
                assassin = self._find_role_holder("Thích Khách")
                if assassin and assassin.alive:
                    assassin_role = assassin.role
                    if hasattr(assassin_role, 'can_act_this_night'):
                        assassin_role.can_act_this_night = True  # type: ignore[attr-defined]
                        assassin_role.votes_day1 = assassin_votes_day1  # type: ignore[attr-defined]
                        assassin_role.votes_day2 = assassin_votes_day2  # type: ignore[attr-defined]
                        await assassin.member.send(
                            f"💀 **Bạn nhận được {total_assassin_votes} phiếu trong 2 ngày ({assassin_votes_day1}+{assassin_votes_day2})!** Bạn có thể lặng lẽ giết 1 người vào buổi tối."
                        )
                        logger.info("Assassin notified | guild=%s assassin=%s total_votes=%s day1=%s day2=%s night=%s", 
                                    self.guild.id, assassin.user_id, total_assassin_votes, assassin_votes_day1, assassin_votes_day2, self.night_number + 1)
        
        # Check for Devoted Servant power before revealing role
        await self._check_devoted_servant_power(target_player)
        
        if target_player.alive:
            target_player.alive = False
            await self._handle_death(target_player, cause="lynch")
            # Resolve any immediate retaliations (e.g., Hunter) during the day
            await self._resolve_pending_deaths("hunter")
            logger.info("Player lynched | guild=%s player=%s", self.guild.id, target_player.display_name())
            
            # Check if Judge activated double lynch
            if self._judge_activated_double_lynch:
                alive_after_first = self.alive_players()
                if len(alive_after_first) >= 2:
                    # Need a second lynch
                    await self.channel.send("🎭 **Thẩm phán đã kích hoạt ám hiệu! Sẽ có thêm 1 người nữa bị treo cổ ngay lập tức!**")
                    
                    # Create a second vote for the second lynch
                    options_second = {p.user_id: p.display_name() for p in alive_after_first}
                    vote_second = VoteSession(
                        self.bot,
                        self.channel,
                        title=f"Bỏ phiếu treo cổ lần 2 (Thẩm Phán) ngày {self.day_number}",
                        description="Chọn người thứ hai sẽ bị treo cổ.",
                        options=options_second,
                        eligible_voters=[p.user_id for p in alive_after_first],
                        duration=30,  # Shorter vote time for second lynch
                        allow_skip=True,
                        vote_weights={p.user_id: p.vote_weight for p in alive_after_first},
                    )
                    result_second = await vote_second.start()
                    tally_second = Counter(result_second.tally)
                    
                    if tally_second:
                        top_second = tally_second.most_common()
                        target_player_second = self.players.get(top_second[0][0])
                        if target_player_second and target_player_second.alive:
                            await self.channel.send(f"{target_player_second.display_name()} bị dân làng treo cổ lần thứ hai.")
                            
                            # Check for Devoted Servant power on SECOND lynch too
                            logger.info("Judge double lynch: checking Devoted Servant for second target | guild=%s target=%s", 
                                       self.guild.id, target_player_second.user_id)
                            await self._check_devoted_servant_power(target_player_second)
                            
                            target_player_second.alive = False
                            await self._handle_death(target_player_second, cause="lynch")
                            await self._resolve_pending_deaths("hunter")
                            logger.info("Second lynch executed (Judge) | guild=%s player=%s", 
                                       self.guild.id, target_player_second.display_name())
                else:
                    logger.info("Not enough players for second lynch | guild=%s", self.guild.id)

    async def _run_discussion_phase(self, alive_count: int, discussion_time: int) -> None:
        """
        Discussion/Thảo luận phase with dynamic timing and Skip Vote feature.
        
        Formula: Base time (60s) + (alive_players * 30s)
        Example: 10 players = 60 + (10 * 30) = 360s (6 minutes)
        
        Allow Skip Vote: Players can vote to skip discussion at ANY TIME during discussion.
        Skip vote: If ALL alive players vote skip, immediately proceed to voting phase.
        Menu stays available without timeout throughout discussion time.
        """
        if not self.settings.allow_skip_vote:
            # No skip feature, just run normal countdown
            await self._run_countdown(
                self.channel,
                f"Thảo luận ngày {self.day_number} ({alive_count} người sống)",
                discussion_time
            )
            return
        
        # Create skip vote menu
        alive_players = self.alive_players()
        skip_vote_view = _DiscussionSkipVoteView(self, alive_players)
        
        embed = discord.Embed(
            title=f"⏱️ Thảo luận ngày {self.day_number}",
            description=f"👥 **{alive_count} người sống** • ⏳ **{discussion_time}s**\n\n"
                       f"💬 Hãy thảo luận về ai là Ma Sói!\n\n"
                       f"🔘 **Phiếu bỏ qua:** Nếu **TẤT CẢ** người chơi đều chọn bỏ qua, "
                       f"sẽ kết thúc thảo luận và đi thẳng đến treo cổ.",
            colour=discord.Colour.blue()
        )
        embed.set_footer(text=f"Menu luôn sẵn sàng, không timeout")
        
        skip_message = await self.channel.send(embed=embed, view=skip_vote_view)
        skip_vote_view.message = skip_message
        
        logger.info("Discussion phase started with skip voting | guild=%s day=%s time=%s alive=%s", 
                   self.guild.id, self.day_number, discussion_time, alive_count)
        
        # Run countdown while monitoring skip votes
        start_time = asyncio.get_event_loop().time()
        remaining_time = discussion_time
        
        while remaining_time > 0:
            # Check if all players voted to skip
            if skip_vote_view.can_skip():
                await self.channel.send("✅ **Tất cả người chơi đều bỏ qua thảo luận!**\n💨 Chuyển sang giai đoạn treo cổ...")
                logger.info("Discussion skipped by all players | guild=%s day=%s", self.guild.id, self.day_number)
                skip_vote_view.stop()
                break
            
            # Sleep and check remaining time
            await asyncio.sleep(1)
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining_time = discussion_time - int(elapsed)
            
            # Update countdown every 5 seconds
            if int(elapsed) % 5 == 0 and remaining_time > 0:
                skip_votes = len(skip_vote_view.skip_votes)
                skip_embed = discord.Embed(
                    title=f"⏱️ Thảo luận ngày {self.day_number}",
                    description=f"⏳ **{remaining_time}s** còn lại\n"
                               f"🔘 Bỏ qua: {skip_votes}/{alive_count}",
                    colour=discord.Colour.blue()
                )
                try:
                    await skip_message.edit(embed=skip_embed, view=skip_vote_view)
                except discord.HTTPException:
                    pass
        
        skip_vote_view.stop()
        
        # Final summary
        skip_votes = len(skip_vote_view.skip_votes)
        if skip_votes > 0:
            await self.channel.send(f"📊 **Kết quả bỏ phiếu:** {skip_votes}/{alive_count} người chọn bỏ qua")
        
        logger.info("Discussion phase ended | guild=%s day=%s skip_votes=%s", 
                   self.guild.id, self.day_number, skip_votes)

    async def _run_defense_phase(self, target_player: PlayerState) -> None:
        """
        Defense/Biện hộ phase: Allow the nominated player to speak for their defense.
        Duration: day_defense_duration seconds (default: 75 seconds)
        """
        defense_time = self.settings.day_defense_duration
        
        await self.channel.send(
            f"⏱️ **Biện hộ:** {target_player.display_name()} có {defense_time} giây để thuyết phục mọi người. (Cả làng vui lòng lắng nghe...)"
        )
        logger.info("Defense phase started | guild=%s player=%s duration=%s", 
                   self.guild.id, target_player.user_id, defense_time)
        
        await self._run_countdown(self.channel, "Phiên biện hộ", defense_time)

    async def _run_judgment_phase(self, target_player: PlayerState) -> bool:
        """
        Judgment/Biểu quyết phase: Vote Kill or Spare (Giết hoặc Tha).
        Duration: day_judgment_duration seconds (default: 20 seconds)
        
        Returns: True if player should be executed, False if spared
        """
        alive_players = self.alive_players()
        judgment_time = self.settings.day_judgment_duration
        
        # Setup voting options: Kill (Giết) or Spare (Tha)
        judgment_options = {
            1: "Giết",
            2: "Tha",
        }
        
        await self.channel.send(
            f"📋 **Biểu quyết:** Bạn có {judgment_time} giây để quyết định: **Giết** hay **Tha** {target_player.display_name()}?"
        )
        
        logger.info("Judgment phase started | guild=%s player=%s duration=%s", 
                   self.guild.id, target_player.user_id, judgment_time)
        
        # Create a judgment vote with Kill/Spare options
        from .voting import VoteSession
        judgment_vote = VoteSession(
            self.bot,
            self.channel,
            title=f"Biểu quyết: {target_player.display_name()}",
            description="Bạn có muốn giết hay tha người này?",
            options=judgment_options,
            eligible_voters=[p.user_id for p in alive_players if not p.vote_disabled],
            duration=judgment_time,
            allow_skip=False,
            vote_weights={p.user_id: p.vote_weight for p in alive_players},
        )
        
        result = await judgment_vote.start()
        tally = Counter(result.tally)
        
        if not tally:
            # No votes cast - default to sparing
            await self.channel.send(f"Không ai quyết định được, {target_player.display_name()} được tha.")
            return False
        
        # Count votes for Kill (1) vs Spare (2)
        kill_votes = tally.get(1, 0)
        spare_votes = tally.get(2, 0)
        
        await self.channel.send(f"📊 Kết quả: **Giết** {kill_votes} phiếu | **Tha** {spare_votes} phiếu")
        
        if kill_votes > spare_votes:
            await self.channel.send(f"⚖️ Dân làng quyết định **GIẾT** {target_player.display_name()}.")
            return True
        elif spare_votes > kill_votes:
            await self.channel.send(f"⚖️ Dân làng quyết định **THA** {target_player.display_name()}.")
            return False
        else:
            # Tie in judgment - default to sparing
            await self.channel.send(f"Hòa phiếu, {target_player.display_name()} được tha.")
            return False

    async def _run_last_words_phase(self, target_player: PlayerState) -> None:
        """
        Last Words/Trăng trối phase: Allow the condemned player to speak final words.
        Duration: day_last_words_duration seconds (default: 10 seconds)
        """
        last_words_time = self.settings.day_last_words_duration
        
        await self.channel.send(
            f"💬 **Lời cuối cùng:** {target_player.display_name()} có {last_words_time} giây để nói lời tạm biệt..."
        )
        logger.info("Last words phase started | guild=%s player=%s duration=%s", 
                   self.guild.id, target_player.user_id, last_words_time)
        
        await self._run_countdown(self.channel, "Lời cuối cùng", last_words_time)
        
        await self.channel.send(f"💀 **{target_player.display_name()} đã bị xử tử.** 🪦")

    async def _assign_roles(self) -> None:
        player_ids = list(self.players.keys())
        random.shuffle(player_ids)
        
        # First, build layout without thief bonus to check if thief is in the game
        role_layout = self._build_role_layout(len(player_ids), has_thief=False)
        random.shuffle(role_layout)
        
        # Check if thief was randomly assigned in the layout
        has_thief_role = any(cls().metadata.name == "Tên Trộm" for cls in role_layout)
        
        if has_thief_role:
            # Rebuild layout with 2 extra cards for thief
            role_layout = self._build_role_layout(len(player_ids), has_thief=True)
            random.shuffle(role_layout)
        
        extra_cards: List[Role] = []
        thief_id: Optional[int] = None
        
        # Assign first N roles to players
        for player_id, role_cls in zip(player_ids, role_layout[:len(player_ids)]):
            role = role_cls()
            if role.metadata.name == "Tên Trộm":
                thief_id = player_id
            self.players[player_id].roles = [role]
            logger.info(
                "Role assigned | guild=%s player=%s name=%s alignment=%s",
                self.guild.id,
                player_id,
                role.metadata.name,
                role.alignment,
            )
        
        # If thief exists, the last 2 roles become extra cards
        if thief_id is not None and len(role_layout) > len(player_ids):
            thief = self.players[thief_id]
            extra_role_classes = role_layout[len(player_ids):]
            extra_cards = [role_cls() for role_cls in extra_role_classes]
            thief.role.extra_cards = extra_cards  # type: ignore[attr-defined]
            logger.info(
                "Thief extra cards generated | guild=%s cards=%s",
                self.guild.id,
                [role.metadata.name for role in extra_cards]
            )
        for player in self.players.values():
            # Call on_assign for all roles
            for role in player.roles:
                await role.on_assign(self, player)
        
        # Detect Two Sisters and notify them of each other
        sisters = [p for p in self.players.values() if getattr(p, "is_sister", False)]
        if len(sisters) == 2:
            self._sisters_ids = [s.user_id for s in sisters]
            try:
                await sisters[0].member.send(f"👯 Bạn là Hai Chị Em cùng với: {sisters[1].display_name()}")
                await sisters[1].member.send(f"👯 Bạn là Hai Chị Em cùng với: {sisters[0].display_name()}")
            except discord.HTTPException:
                pass
            logger.info("Two Sisters identified | guild=%s sisters=%s", self.guild.id, self._sisters_ids)
        
        # Detect Wolf Brother & Sister and pair them
        wolf_siblings = [(p, p.roles[0]) for p in self.players.values() if p.roles and p.roles[0].metadata.name in ("Sói Anh", "Sói Em")]
        
        # VALIDATION: Ensure both Wolf Brother and Sister are present together (not partial assignment)
        wolf_brother_count = sum(1 for p, r in wolf_siblings if r.metadata.name == "Sói Anh")
        wolf_sister_count = sum(1 for p, r in wolf_siblings if r.metadata.name == "Sói Em")
        
        if wolf_brother_count != wolf_sister_count:
            logger.error(
                "CRITICAL: Incomplete Wolf Sibling assignment | guild=%s brothers=%s sisters=%s",
                self.guild.id, wolf_brother_count, wolf_sister_count
            )
            # If we have one but not the other, log the error and continue (shouldn't happen with new role_config logic)
        elif wolf_brother_count == 1 and wolf_sister_count == 1:
            # Both are present - proceed with pairing
            player1, role1 = wolf_siblings[0]
            player2, role2 = wolf_siblings[1]
            
            # Randomly decide who is brother and who is sister
            if random.random() < 0.5:
                brother_player, sister_player = player1, player2
                brother_role, sister_role = role1, role2
            else:
                brother_player, sister_player = player2, player1
                brother_role, sister_role = role2, role1
            
            # If we need to swap roles (if assigned wrong), do it now
            if brother_role.metadata.name != "Sói Anh":
                # Swap roles
                brother_player.roles = [sister_role]
                sister_player.roles = [brother_role]
                brother_role, sister_role = sister_role, brother_role
            
            # Link them together
            self._wolf_brother_id = brother_player.user_id
            self._wolf_sister_id = sister_player.user_id
            brother_role.sister_id = sister_player.user_id
            sister_role.brother_id = brother_player.user_id
            
            logger.info(
                "Wolf siblings paired | guild=%s brother=%s sister=%s",
                self.guild.id,
                brother_player.user_id,
                sister_player.user_id,
            )

        # Create Werewolf Player role for voice mode
        if self.game_mode == "voice" and self.voice_channel_id:
            self.werewolf_role = await self.guild.create_role(name="Werewolf Player", permissions=discord.Permissions.none())
            for player in self.players.values():
                if any(role.alignment == Alignment.WEREWOLF for role in player.roles):
                    await player.member.add_roles(self.werewolf_role)

    async def _notify_roles(self) -> None:
        wolf_players = [p for p in self.players.values() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        wolf_names = ", ".join(p.display_name() for p in wolf_players) or "Không có"
        for player in self.players.values():
            roles = player.roles
            if not roles:
                continue
            # Notify for primary (first) role
            role = roles[0]
            embed = discord.Embed(
                title=f"Bạn là: {role.metadata.name}",
                description=role.format_private_information(),
                colour=discord.Colour.dark_gold(),
            )
            # Add information about additional roles
            if len(roles) > 1:
                additional_roles = ", ".join(r.metadata.name for r in roles[1:])
                embed.add_field(name="Vai trò thêm", value=additional_roles, inline=False)
            
            embed.add_field(name="Phe", value=player.faction_view(), inline=True)
            embed.add_field(name="Đồng đội", value=wolf_names if any(r.alignment == Alignment.WEREWOLF for r in roles) else "Ẩn danh", inline=True)
            embed.set_image(url=role.metadata.card_image_url)
            # SECURITY: Use safe DM with error handling
            await self._safe_send_dm(player.member, embed=embed)
            # Rate limit protection: small delay between DMs
            await asyncio.sleep(0.1)

    async def _announce_role_composition(self) -> None:
        """Announce all roles in the game at the start."""
        from collections import Counter
        # Count all roles (including additional ones)
        all_role_names = []
        for p in self.players.values():
            for role in p.roles:
                all_role_names.append(role.metadata.name)
        role_counts = Counter(all_role_names)
        
        embed = discord.Embed(
            title="🎴 Các Vai Trò Trong Game",
            description=f"Trận đấu có {len(self.players)} người chơi với các vai trò sau:",
            colour=discord.Colour.gold(),
        )
        
        # Group by alignment
        village_roles = []
        wolf_roles = []
        neutral_roles = []
        
        for role_name, count in role_counts.items():
            role_cls = get_role_class(role_name)
            if not role_cls:
                continue
            role_instance = role_cls()
            display = f"{role_name} x{count}" if count > 1 else role_name
            
            if role_instance.alignment == Alignment.VILLAGE:
                village_roles.append(display)
            elif role_instance.alignment == Alignment.WEREWOLF:
                wolf_roles.append(display)
            else:
                neutral_roles.append(display)
        
        if village_roles:
            embed.add_field(name="🏘️ Phe Dân Làng", value="\n".join(village_roles), inline=True)
        if wolf_roles:
            embed.add_field(name="🐺 Phe Ma Sói", value="\n".join(wolf_roles), inline=True)
        if neutral_roles:
            embed.add_field(name="⚖️ Phe Trung Lập", value="\n".join(neutral_roles), inline=True)
        
        embed.set_footer(text="Vai trò của bạn đã được gửi qua DM")
        embed.set_image(url=CARD_BACK_URL)
        await self.channel.send(embed=embed)

    async def _wake_sisters(self) -> None:
        """Wake Two Sisters on even nights for coordination via thread."""
        if not self._sisters_ids or len(self._sisters_ids) != 2:
            return
        
        sisters_alive = [self.players[sid] for sid in self._sisters_ids if sid in self.players and self.players[sid].alive]
        if len(sisters_alive) != 2:
            return
        
        # Create or reuse thread
        if not self._sisters_thread:
            try:
                self._sisters_thread = await self.channel.create_thread(
                    name=f"Hai Chị Em - Đêm {self.night_number}",
                    auto_archive_duration=60
                )
            except discord.HTTPException:
                logger.warning("Failed to create sisters thread | guild=%s", self.guild.id)
                return
        
        # Add both sisters to thread
        for sister in sisters_alive:
            try:
                await self._sisters_thread.add_user(sister.member)
            except discord.HTTPException:
                pass
        
        # Notify them
        try:
            await self._sisters_thread.send(
                f"👯 **Hai Chị Em thức dậy!**\n"
                f"{sisters_alive[0].display_name()} và {sisters_alive[1].display_name()}\n\n"
                f"Các bạn có thể bàn luận để quyết định chiến lược cứu làng trong ngày hôm sau. "
                f"Nếu cùng bỏ phiếu cho một người, sẽ được cộng thêm 1 phiếu!"
            )
        except discord.HTTPException:
            pass
        
        logger.info("Sisters woken up | guild=%s night=%s sisters=%s", self.guild.id, self.night_number, self._sisters_ids)

    def _announce_role_action(self, role: Role, duration: int = 45) -> asyncio.Task:
        """Announce a specific role is taking action with a countdown (cannot skip).
        Returns a task that completes when countdown finishes."""
        async def _run_countdown() -> None:
            embed = discord.Embed(
                title=f"{role.metadata.name} Dậy đi!",
                description=f"Đang hành động... (Thời gian: {duration}s)",
                colour=discord.Colour.purple(),
            )
            embed.set_thumbnail(url=role.metadata.card_image_url)
            try:
                message = await self.channel.send(embed=embed)
                # Show countdown with fixed time - cannot skip
                remaining = duration
                step = 5
                while remaining > 0:
                    await asyncio.sleep(min(step, remaining))
                    remaining -= step
                    if remaining < 0:
                        remaining = 0
                    try:
                        embed.description = f"Đang hành động... (Thời gian: {remaining}s)"
                        await message.edit(embed=embed)
                    except discord.HTTPException:
                        pass
                # Final message when time is up
                try:
                    embed.description = "Đã hoàn thành."
                    await message.edit(embed=embed)
                except discord.HTTPException:
                    pass
            except discord.HTTPException as e:
                logger.warning("Failed to announce role action | guild=%s role=%s error=%s", 
                              self.guild.id, role.metadata.name, str(e))
        
        # Return the background task
        return asyncio.create_task(_run_countdown())

    async def _create_player_role(self) -> None:
        """Create a role for game participants to manage channel permissions efficiently."""
        try:
            # Create the role
            self._player_role = await self.guild.create_role(
                name="Werewolf Player",
                color=discord.Color.dark_blue(),
                reason="Werewolf: Game participant role for channel permissions"
            )
            
            # Set channel permissions for the role
            await self.channel.set_permissions(
                self._player_role,
                send_messages=True,
                read_messages=True,
                reason="Werewolf: Allow players to chat in game channel"
            )
            
            # Assign role to all players with rate limiting protection
            for player in self.players.values():
                try:
                    await player.member.add_roles(self._player_role, reason="Werewolf: Add player to game")
                    await asyncio.sleep(0.1)  # Rate limit protection
                except discord.HTTPException as e:
                    logger.warning("Failed to add role to player | guild=%s player=%s error=%s",
                                 self.guild.id, player.user_id, str(e))
            
            logger.info("Player role created and assigned | guild=%s role=%s players=%s",
                       self.guild.id, self._player_role.id, len(self.players))
        except discord.HTTPException as e:
            logger.error("Failed to create player role | guild=%s error=%s", self.guild.id, str(e))
            # Fallback: set individual permissions if role creation fails
            await self._fallback_individual_permissions()

    async def _fallback_individual_permissions(self) -> None:
        """Fallback: Set individual permissions for each player (rate-limited)."""
        logger.warning("Using fallback individual permissions | guild=%s players=%s", self.guild.id, len(self.players))
        for player in self.players.values():
            try:
                await self.channel.set_permissions(
                    player.member,
                    send_messages=True,
                    read_messages=True,
                    reason="Werewolf: Allow player to chat in game channel"
                )
                await asyncio.sleep(0.1)  # Rate limit protection
            except discord.HTTPException as e:
                logger.warning("Failed to set permissions for player | guild=%s player=%s error=%s",
                             self.guild.id, player.user_id, str(e))

    async def _create_wolf_thread(self) -> None:
        # Get wolves but exclude Avengers on werewolf side (they don't join wolf thread)
        wolves = []
        for p in self.players.values():
            if any(r.alignment == Alignment.WEREWOLF for r in p.roles):
                # Check if this is an Avenger on werewolf side
                is_avenger_wolf_side = False
                for role in p.roles:
                    if hasattr(role, '__class__') and role.__class__.__name__ == 'Avenger':
                        if hasattr(role, 'chosen_side') and role.chosen_side == Alignment.WEREWOLF:
                            is_avenger_wolf_side = True
                            break
                
                # Only add to wolves if not an Avenger on werewolf side
                if not is_avenger_wolf_side:
                    wolves.append(p)
                else:
                    logger.info("Avenger on werewolf side excluded from wolf thread | guild=%s player=%s", 
                               self.guild.id, p.user_id)
        
        if not wolves:
            return
        name = f"{self.settings.wolf_thread_name} - Đêm 1"
        try:
            self._wolf_thread = await self.channel.create_thread(name=name, auto_archive_duration=60)
        except discord.HTTPException:
            await self.channel.send("Không tạo được thread cho Ma Sói.")
            return
        wolf_mentions = " ".join(p.member.mention for p in wolves)
        await self._wolf_thread.send(f"{wolf_mentions} đây là nơi bàn kế hoạch. Hãy dùng menu để chọn mục tiêu mỗi đêm.")

    async def _mute_voice(self) -> None:
        """Mute all players in voice channel during night phase, keep dead players muted."""
        if not self.voice_channel_id:
            return
        try:
            voice_channel = self.bot.get_channel(self.voice_channel_id)
            if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
                logger.warning("Voice channel not found or invalid | guild=%s channel_id=%s", self.guild.id, self.voice_channel_id)
                return
            
            # Mute all players currently in the voice channel
            muted_count = 0
            for member in voice_channel.members:
                try:
                    await member.edit(mute=True, reason="Werewolf: Night phase - mute")
                    muted_count += 1
                except discord.HTTPException as e:
                    logger.warning("Failed to mute member | guild=%s member=%s error=%s", 
                                 self.guild.id, member.id, str(e))
            
            logger.info("Voice muted | guild=%s voice_channel=%s muted_count=%s", 
                       self.guild.id, self.voice_channel_id, muted_count)
        except Exception as e:
            logger.error("Failed to mute voice channel | guild=%s error=%s", self.guild.id, str(e), exc_info=True)

    async def _unmute_voice(self, force_unmute_all: bool = False) -> None:
        """Unmute alive players in voice channel during day phase, keep dead players muted.
        
        Args:
            force_unmute_all: If True, unmute all players regardless of alive status (used in cleanup).
        """
        if not self.voice_channel_id:
            return
        try:
            voice_channel = self.bot.get_channel(self.voice_channel_id)
            if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
                logger.warning("Voice channel not found or invalid | guild=%s channel_id=%s", self.guild.id, self.voice_channel_id)
                return
            
            # Unmute only alive players in the voice channel
            unmuted_count = 0
            for member in voice_channel.members:
                # Check if player is alive
                player = self.players.get(member.id)
                if not force_unmute_all and player and not player.alive:
                    # Keep dead players muted (unless force_unmute_all)
                    try:
                        if member.voice and not member.voice.mute:
                            await member.edit(mute=True, reason="Werewolf: Dead player must stay muted")
                    except discord.HTTPException:
                        pass
                    continue
                
                try:
                    await member.edit(mute=False, reason="Werewolf: Day phase - unmute" if not force_unmute_all else "Werewolf: Game ended - unmute all")
                    unmuted_count += 1
                except discord.HTTPException as e:
                    logger.warning("Failed to unmute member | guild=%s member=%s error=%s", 
                                 self.guild.id, member.id, str(e))
            
            logger.info("Voice unmuted | guild=%s voice_channel=%s unmuted_count=%s force_unmute_all=%s", 
                       self.guild.id, self.voice_channel_id, unmuted_count, force_unmute_all)
        except Exception as e:
            logger.error("Failed to unmute voice channel | guild=%s error=%s", self.guild.id, str(e), exc_info=True)

    async def _disable_text_chat(self) -> None:
        """Disable text chat in game channel (only during night phase)."""
        try:
            everyone_role = self.guild.default_role
            await self.channel.set_permissions(
                everyone_role,
                send_messages=False,
                reason="Werewolf: Night phase - disable text chat"
            )
            logger.info("Text chat disabled | guild=%s channel=%s", self.guild.id, self.channel.id)
        except discord.HTTPException as e:
            logger.error("Failed to disable text chat | guild=%s error=%s", self.guild.id, str(e))

    async def _enable_text_chat(self) -> None:
        """Re-enable text chat in game channel (only during day phase)."""
        try:
            everyone_role = self.guild.default_role
            # Set to None to inherit channel defaults
            await self.channel.set_permissions(
                everyone_role,
                send_messages=None,
                reason="Werewolf: Day phase - enable text chat"
            )
            logger.info("Text chat enabled | guild=%s channel=%s", self.guild.id, self.channel.id)
        except discord.HTTPException as e:
            logger.error("Failed to enable text chat | guild=%s error=%s", self.guild.id, str(e))

    async def _run_wolf_vote(self) -> Optional[int]:
        """Run wolf vote to choose a target for the night kill."""
        wolves = [p for p in self.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        candidates = self.alive_players()
        if not wolves or not candidates:
            return None
        channel = self._wolf_thread or self.channel
        options = {p.user_id: p.display_name() for p in candidates}
        vote = VoteSession(
            self.bot,
            channel,
            title=f"Ma Sói chọn con mồi (Đêm {self.night_number})",
            description="Chọn người muốn tấn công. Hòa phiếu thì đêm yên bình.",
            options=options,
            eligible_voters=[w.user_id for w in wolves],
            duration=self.settings.night_vote_duration,
            allow_skip=True,
        )
        result = await vote.start()
        return result.winning_target_id if not result.is_tie else None

    def _calculate_night_action_duration(self, *, first_night: bool) -> int:
        """Calculate estimated total duration for all night role actions."""
        duration = 0
        # Thief (first night only)
        if first_night and self._find_role_holder("Tên Trộm"):
            duration += 60
        # Cupid (first night only)
        if first_night and self._find_role_holder("Thần Tình Yêu"):
            duration += 120  # 2 lovers
        # Wolf vote
        wolves = [p for p in self.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        if wolves:
            duration += self.settings.night_vote_duration
        # Guard
        if self._find_role_holder("Bảo Vệ"):
            duration += 60
        # Seer
        if self._find_role_holder("Tiên Tri"):
            duration += 60
        # Witch
        if self._find_role_holder("Phù Thủy"):
            duration += 120  # heal + poison
        # White Wolf (every other night)
        if self.night_number % 2 == 0 and self._find_role_holder("Sói Trắng"):
            duration += 60
        # Raven
        if self._find_role_holder("Con Quạ"):
            duration += 60
        # Piper
        if self._find_role_holder("Thổi Sáo"):
            duration += 120  # 2 targets
        # Pyromaniac
        pyro = self._find_role_holder("Kẻ Phóng Hỏa")
        if pyro and not getattr(pyro.role, "ignited", False):
            duration += 60
        # Night intro duration
        duration += self.settings.night_intro_duration
        return max(duration, 60)  # Minimum 60s

    async def _resolve_role_sequence(self, *, first_night: bool) -> None:
        try:
            # Reset Moon Maiden disabled flag each night
            self._moon_maiden_disabled = None
            # Reset Hypnotist charm target each night
            self._hypnotist_charm_target = None
            # Reset Pharmacist targets each night
            self._pharmacist_antidote_target = None
            self._pharmacist_slept_target = None
            # Reset Assassin votes on even nights (after 2-day cycle ends)
            if self.night_number % 2 == 0:
                self._assassin_votes_day1 = {}
                self._assassin_votes_day2 = {}
                logger.info("Assassin votes reset for new cycle | guild=%s night=%s", self.guild.id, self.night_number)
            
            announce_task = None
            thief = self._find_role_holder("Tên Trộm")
            if first_night and thief and self._is_player_eligible_for_action(thief):
                announce_task = self._announce_role_action(thief.role)
                await self._handle_thief(thief)
                if announce_task:
                    await announce_task
                logger.info("Thief resolved | guild=%s player=%s", self.guild.id, thief.user_id)
            cupid = self._find_role_holder("Thần Tình Yêu")
            if first_night and cupid and self._is_player_eligible_for_action(cupid):
                announce_task = self._announce_role_action(cupid.role)
                await self._handle_cupid(cupid)
                if announce_task:
                    await announce_task
                logger.info("Cupid resolved | guild=%s player=%s", self.guild.id, cupid.user_id)
            
            # Handle Wolf Brother & Sister first-night recognition
            if first_night and self._wolf_brother_id and self._wolf_sister_id:
                brother = self.players.get(self._wolf_brother_id)
                sister = self.players.get(self._wolf_sister_id)
                if brother and sister and brother.alive and sister.alive:
                    # Call on_first_night for both siblings
                    for role in brother.roles:
                        if hasattr(role, 'on_first_night'):
                            try:
                                await role.on_first_night(self, brother)
                                logger.info("Wolf Brother first-night resolved | guild=%s player=%s", self.guild.id, brother.user_id)
                            except Exception as e:
                                logger.error("Error in Wolf Brother first-night | guild=%s player=%s error=%s", 
                                           self.guild.id, brother.user_id, str(e), exc_info=True)
                    
                    for role in sister.roles:
                        if hasattr(role, 'on_first_night'):
                            try:
                                await role.on_first_night(self, sister)
                                logger.info("Wolf Sister first-night resolved | guild=%s player=%s", self.guild.id, sister.user_id)
                            except Exception as e:
                                logger.error("Error in Wolf Sister first-night | guild=%s player=%s error=%s", 
                                           self.guild.id, sister.user_id, str(e), exc_info=True)
            
            wolves = [p for p in self.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
            announce_task = None
            wolves = self.get_active_werewolves()
            if wolves:
                announce_task = self._announce_role_action(wolves[0].roles[0])
            
            # Handle little girl peeking before wolf vote (so wolves can see the discovery message)
            little_girl = self._find_role_holder("Cô Bé")
            if little_girl and self._is_player_eligible_for_action(little_girl):
                await self._handle_little_girl(little_girl)
            
            # Run wolf vote - if little girl was discovered, wolves can choose to kill her instead
            target_id = await self._run_wolf_vote()
            if announce_task:
                await announce_task
            logger.info("Wolf vote target | guild=%s night=%s target=%s", self.guild.id, self.night_number, target_id)
            
            # If little girl was discovered, ask wolves quickly if they want to switch kill to her
            if self._little_girl_peeking:
                try:
                    # Run a quick yes/no vote in wolf thread - NO COUNTDOWN, IMMEDIATE
                    channel = self._wolf_thread or self.channel
                    options = {
                        self._little_girl_peeking: "Giết người hé mắt (Cô Bé)",
                        target_id if target_id is not None else -1: "Giữ mục tiêu cũ",
                    }
                    vote = VoteSession(
                        self.bot,
                        channel,
                        title=f"Ma Sói xác nhận mục tiêu (Đêm {self.night_number})",
                        description="Bạn có muốn đổi sang giết người hé mắt không?",
                        options=options,
                        eligible_voters=[w.user_id for w in wolves],
                        duration=15,
                        allow_skip=False,
                    )
                    confirm = await vote.start()
                    if not confirm.is_tie and confirm.winning_target_id in options:
                        target_id = confirm.winning_target_id if confirm.winning_target_id != -1 else target_id
                        logger.info("Wolves confirmation applied | guild=%s night=%s target=%s", self.guild.id, self.night_number, target_id)
                finally:
                    # Reset peeking flag regardless
                    self._little_girl_peeking = None
            
            guard = self._find_role_holder("Bảo Vệ")
            announce_task = None
            if guard and self._is_player_eligible_for_action(guard):
                announce_task = self._announce_role_action(guard.role)
            protected_id = await self._handle_guard(guard) if guard and self._is_player_eligible_for_action(guard) else None
            if announce_task:
                await announce_task
            logger.info("Guard protected | guild=%s night=%s target=%s", self.guild.id, self.night_number, protected_id)
            killed_id = target_id if target_id != protected_id else None
            # Track bodyguard save achievement
            if guard and target_id == protected_id and killed_id is None:
                guard.bodyguard_saves += 1
                logger.info("Bodyguard save counted | guild=%s bodyguard=%s saves=%s", self.guild.id, guard.user_id, guard.bodyguard_saves)
            if killed_id and self._handle_elder_resistance(killed_id):
                killed_id = None
            
            white_wolf = self._find_role_holder("Sói Trắng")
            announce_task = None
            if white_wolf and self.night_number % 2 == 0 and self._is_player_eligible_for_action(white_wolf):
                announce_task = self._announce_role_action(white_wolf.role)
            betrayer_kill = await self._handle_white_wolf(white_wolf) if white_wolf and self.night_number % 2 == 0 and self._is_player_eligible_for_action(white_wolf) else None
            if announce_task:
                await announce_task
            
            seer = self._find_role_holder("Tiên Tri")
            if seer and self._is_player_eligible_for_action(seer):
                announce_task = self._announce_role_action(seer.role)
                await self._handle_seer(seer)
                if announce_task:
                    await announce_task
            
            witch = self._find_role_holder("Phù Thủy")
            if witch and self._is_player_eligible_for_action(witch):
                announce_task = self._announce_role_action(witch.role)
                killed_id = await self._handle_witch(witch, killed_id)
                if announce_task:
                    await announce_task
            
            raven = self._find_role_holder("Con Quạ")
            if raven and self._moon_maiden_disabled != raven.user_id and self._is_player_eligible_for_action(raven):
                announce_task = self._announce_role_action(raven.role)
                await self._handle_raven(raven)
                if announce_task:
                    await announce_task
            
            piper = self._find_role_holder("Thổi Sáo")
            if piper and self._moon_maiden_disabled != piper.user_id and self._is_player_eligible_for_action(piper):
                announce_task = self._announce_role_action(piper.role)
                await self._handle_piper(piper)
                if announce_task:
                    await announce_task
            
            pyro = self._find_role_holder("Kẻ Phóng Hỏa")
            if pyro and not getattr(pyro.role, "ignited", False) and self._is_player_eligible_for_action(pyro):
                announce_task = self._announce_role_action(pyro.role)
                await self._handle_pyromaniac(pyro)
                if announce_task:
                    await announce_task
            
            hypnotist = self._find_role_holder("Cổ Hoặc Sư")
            if hypnotist and self._is_player_eligible_for_action(hypnotist):
                announce_task = self._announce_role_action(hypnotist.role)
                await self._handle_hypnotist(hypnotist)
                if announce_task:
                    await announce_task
            
            moon_maiden = self._find_role_holder("Nguyệt Nữ")
            if moon_maiden and self._is_player_eligible_for_action(moon_maiden):
                announce_task = self._announce_role_action(moon_maiden.role)
                await self._handle_moon_maiden(moon_maiden)
                if announce_task:
                    await announce_task
            
            # Fire Wolf ability - trigger if wolves died during the day
            fire_wolf = self._find_role_holder("Sói Lửa")
            if fire_wolf and self._is_player_eligible_for_action(fire_wolf):
                # Check if any wolves died today (first ability trigger)
                if len(self._wolves_died_today) >= 1 and not getattr(fire_wolf.role, 'has_used_ability_first', False):
                    # Mark that first wolf death triggered the ability
                    fire_wolf._fire_wolf_trigger_first = True
                    announce_task = self._announce_role_action(fire_wolf.role)
                    await fire_wolf.role.on_night(self, fire_wolf, self.night_number)
                    if announce_task:
                        await announce_task
                    logger.info(
                        "Fire Wolf triggered (first wolf death) | guild=%s fire_wolf=%s wolves_died=%s",
                        self.guild.id, fire_wolf.user_id, len(self._wolves_died_today)
                    )
                # Check if 2+ wolves died today (second ability trigger)
                elif len(self._wolves_died_today) >= 2 and not getattr(fire_wolf.role, 'has_used_ability_second', False):
                    fire_wolf.role.can_use_again = True
                    announce_task = self._announce_role_action(fire_wolf.role)
                    await fire_wolf.role.on_night(self, fire_wolf, self.night_number)
                    if announce_task:
                        await announce_task
                    logger.info(
                        "Fire Wolf triggered (2+ wolves died) | guild=%s fire_wolf=%s wolves_died=%s",
                        self.guild.id, fire_wolf.user_id, len(self._wolves_died_today)
                    )
            
            if killed_id:
                self._pending_deaths.append((killed_id, "wolves"))
            if betrayer_kill:
                self._pending_deaths.append((betrayer_kill, "white_wolf"))
            
            # Call on_night for roles with night actions
            for player in self.alive_players():
                if self._is_player_eligible_for_action(player):
                    for role in player.roles:
                        if hasattr(role, 'on_night') and role.night_order > 0:
                            try:
                                await role.on_night(self, player, self.night_number)
                                logger.info("Role on_night called | guild=%s player=%s role=%s", self.guild.id, player.user_id, role.metadata.name)
                            except Exception as e:
                                logger.error("Error in role on_night | guild=%s player=%s role=%s error=%s", self.guild.id, player.user_id, role.metadata.name, str(e), exc_info=True)
            
            logger.info("Night resolution | guild=%s night=%s killed=%s extra=%s", self.guild.id, self.night_number, killed_id, betrayer_kill)
        except Exception as e:
            logger.error("CRITICAL: Exception in _resolve_role_sequence | guild=%s night=%s error=%s", 
                        self.guild.id, self.night_number, str(e), exc_info=True)
            raise

    async def _handle_thief(self, thief: PlayerState) -> None:
        role = thief.role
        extra_cards = getattr(role, "extra_cards", [])
        if not extra_cards:
            return
        
        # Check if any of the extra cards is a werewolf
        wolf_indices = [idx for idx, card in enumerate(extra_cards) if card.alignment == Alignment.WEREWOLF]
        has_wolf = len(wolf_indices) > 0
        
        # Build options - if has wolf, only show wolf cards
        if has_wolf:
            options = {idx: card.metadata.name for idx, card in enumerate(extra_cards) if card.alignment == Alignment.WEREWOLF}
            description = "⚠️ Có ít nhất một lá Sói! Bạn BẮT BUỘC phải chọn Sói.\n\nChọn một trong các lá bài Sói:"
        else:
            options = {idx: card.metadata.name for idx, card in enumerate(extra_cards)}
            description = "Chọn một trong hai lá bài bỏ dư:"
        
        result = await self._prompt_dm_choice(
            thief,
            title="Tên trộm chọn vai mới",
            description=description,
            options=options,
            allow_skip=False,
        )
        if result is None:
            return
        
        new_role = extra_cards[result]
        old_role_name = thief.role.metadata.name
        thief.role = new_role
        await new_role.on_assign(self, thief)
        
        # If thief becomes a werewolf, add to wolf thread
        if new_role.alignment == Alignment.WEREWOLF and self._wolf_thread:
            try:
                await self._wolf_thread.add_user(thief.member)
                # Notify other wolves
                wolf_players = [p for p in self.players.values() 
                               if p.alive and any(r.alignment == Alignment.WEREWOLF for r in p.roles) and p.user_id != thief.user_id]
                wolf_mention = " ".join(p.member.mention for p in wolf_players)
                if wolf_mention:
                    await self._wolf_thread.send(f"{wolf_mention} - {thief.display_name()} đã trở thành {new_role.metadata.name} và gia nhập bầy sói!")
                logger.info("Thief joined wolf thread | guild=%s player=%s", self.guild.id, thief.user_id)
            except discord.HTTPException as e:
                logger.warning("Failed to add thief to wolf thread | guild=%s player=%s error=%s", 
                             self.guild.id, thief.user_id, str(e))
        
        try:
            await thief.member.send(f"Bạn đã chọn '{new_role.metadata.name}'.")
        except discord.HTTPException:
            pass
        logger.info("Thief chose role | guild=%s player=%s old_role=%s new_role=%s", 
                   self.guild.id, thief.user_id, old_role_name, new_role.metadata.name)

    async def _handle_cupid(self, cupid: PlayerState) -> None:
        logger.info("_handle_cupid START | guild=%s cupid=%s", self.guild.id, cupid.user_id)
        available = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != cupid.user_id}
        lovers: List[int] = []
        while len(lovers) < 2 and available:
            choice = await self._prompt_dm_choice(
                cupid,
                title="Thần tình yêu",
                description=f"Chọn người yêu thứ {len(lovers) + 1}.",
                options=available,
                allow_skip=False,
            )
            if choice is None or choice not in available:
                logger.info("Cupid skipped lover selection | guild=%s cupid=%s lovers_count=%s night=%s", 
                            self.guild.id, cupid.user_id, len(lovers), self.night_number)
                break
            lovers.append(choice)
            available.pop(choice, None)
        
        if len(lovers) == 2:
            a = self.players[lovers[0]]
            b = self.players[lovers[1]]
            a.lover_id = b.user_id
            b.lover_id = a.user_id
            self._lovers = {a.user_id, b.user_id}
            try:
                await a.member.send(f"Bạn và {b.display_name()} đã trúng mũi tên tình ái.")
                await b.member.send(f"Bạn và {a.display_name()} đã trúng mũi tên tình ái.")
            except discord.HTTPException:
                pass
            logger.info("Cupid linked lovers | guild=%s cupid=%s lovers=%s", self.guild.id, cupid.user_id, self._lovers)
        else:
            logger.info("Cupid incomplete lovers | guild=%s cupid=%s lovers_count=%s", 
                        self.guild.id, cupid.user_id, len(lovers))
        logger.info("_handle_cupid END | guild=%s cupid=%s", self.guild.id, cupid.user_id)

    async def _handle_guard(self, guard: PlayerState) -> Optional[int]:
        """Handle Guard night action with retry logic and filtering of unavailable targets."""
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            
            # Build available options - exclude last protected target
            last_target = getattr(guard.role, "last_protected", None)
            options = {
                p.user_id: p.display_name() 
                for p in self.alive_players() 
                if p.user_id != last_target  # Hide person protected last night
            }
            
            if not options:
                # No valid targets left (shouldn't happen, but safety check)
                await guard.member.send("Không có người nào có thể bảo vệ.")
                return None
            
            choice = await self._prompt_dm_choice(
                guard,
                title="Bảo vệ thức giấc",
                description="Chọn người cần bảo vệ đêm nay.\n*(Người được bảo vệ đêm trước đã bị ẩn)*" if last_target else "Chọn người cần bảo vệ đêm nay.",
                options=options,
                allow_skip=True,
            )
            
            if choice is None:
                # Player skipped
                return None
            
            target_id = choice
            target = self.players.get(target_id)
            
            if not target:
                await guard.member.send("Lựa chọn không hợp lệ. Vui lòng thử lại.")
                continue
            
            # Validate choice
            if target_id == guard.user_id and not guard.role.can_self_target():
                await guard.member.send(
                    "❌ Bạn không thể tiếp tục tự bảo vệ đêm này.\n"
                    "💡 Vui lòng chọn người khác."
                )
                continue  # Ask again instead of returning None
            
            # All validations passed
            target.protected_last_night = True
            if target_id == guard.user_id:
                guard.role.mark_self_target()
                await guard.member.send(
                    "✅ Bạn đã chọn bảo vệ chính mình đêm nay.\n"
                    "⚠️ Bạn sẽ không thể tự bảo vệ nữa."
                )
            guard.role.last_protected = target_id
            logger.info("Guard protected | guild=%s player=%s target=%s", self.guild.id, guard.user_id, target_id)
            return target_id
        
        # Max attempts reached
        await guard.member.send("⏱️ Hết thời gian, bảo vệ bị bỏ qua.")
        logger.info("Guard timeout | guild=%s player=%s attempts=%s", self.guild.id, guard.user_id, attempt)
        return None

    async def _check_devoted_servant_power(self, target_player: PlayerState) -> None:
        """Check if Devoted Servant wants to take the role of the lynched player.
        
        Implements official rulebook edge cases:
        - Lover: cannot use power, but old lover dies of sorrow if accepting
        - Sheriff/Town Crier: special succession rules
        - Charmed/Infected: status is preserved in new role
        """
        logger.info("_check_devoted_servant_power START | guild=%s target=%s", 
                   self.guild.id, target_player.user_id)
        
        servant = self._find_role_holder("Người Tôi Tớ Trung Thành")
        if not servant:
            logger.debug("No Devoted Servant found | guild=%s", self.guild.id)
            return
        
        if not servant.alive:
            logger.debug("Devoted Servant is dead | guild=%s servant=%s", 
                        self.guild.id, servant.user_id)
            return
        
        # Check if servant already used the power
        servant_role = servant.roles[0] if servant.roles else None
        if not servant_role or servant_role.metadata.name != "Người Tôi Tớ Trung Thành":
            logger.warning("Servant role not found or mismatch | guild=%s servant=%s roles=%s", 
                          self.guild.id, servant.user_id, [r.metadata.name for r in servant.roles])
            return
        
        if hasattr(servant_role, 'has_used_power') and servant_role.has_used_power:  # type: ignore[attr-defined]
            logger.info("Devoted Servant already used power | guild=%s servant=%s", 
                       self.guild.id, servant.user_id)
            return
        
        # Check if servant is a lover (cannot use power per official rules)
        if servant.user_id in self._lovers:
            logger.info("Devoted Servant is a lover, cannot use power | guild=%s servant=%s", 
                       self.guild.id, servant.user_id)
            await servant.member.send("⚠️ Vì bạn là tình nhân, bạn không thể sử dụng kỹ năng Người Tôi Tớ Trung Thành.")
            return
        
        logger.info("Checking Devoted Servant power | guild=%s servant=%s target=%s target_role=%s", 
                   self.guild.id, servant.user_id, target_player.user_id,
                   target_player.roles[0].metadata.name if target_player.roles else "Unknown")
        
        try:
            # Prompt Devoted Servant to use power (before revealing target's role)
            use_power = await self._prompt_dm_choice(
                servant,
                title="Người Tôi Tớ Trung Thành - Sử Dụng Kỹ Năng",
                description=f"{target_player.display_name()} vừa bị treo cổ. Bạn có muốn lộ diện và nhận lấy vai trò của họ không?\n\n⚠️ Nếu đồng ý, vai trò của bạn sẽ bị lộ diện, nhưng vai trò của {target_player.display_name()} sẽ vẫn bí mật.",
                options={1: "✅ Lộ diện và nhận lấy vai trò", 2: "❌ Không, giữ bí mật"},
                allow_skip=False,
            )
            
            if use_power == 1:
                # Store the stolen role and mark as used
                if target_player.roles:
                    stolen_role = target_player.roles[0]
                    self._devoted_servant_stolen_role = stolen_role
                    self._devoted_servant_original_target = target_player.user_id
                    servant_role.has_used_power = True  # type: ignore[attr-defined]
                    
                    # HANDLE EDGE CASES from official rulebook
                    if hasattr(servant_role, 'handle_stolen_role_assignment'):
                        await servant_role.handle_stolen_role_assignment(self, servant, stolen_role)  # type: ignore[attr-defined]
                    
                    # Announce Devoted Servant revealing herself
                    import discord
                    embed = discord.Embed(
                        title="🤝 **Người Tôi Tớ Trung Thành - Lộ Diện**",
                        description=f"{servant.display_name()} là **Người Tôi Tớ Trung Thành** và đã lộ diện!",
                        colour=discord.Colour.teal(),
                    )
                    embed.add_field(
                        name="📝 **Hành Động**",
                        value=f"Họ nhận lấy vai trò của {target_player.display_name()} (bí mật).",
                        inline=False
                    )
                    
                    # Add edge case information if applicable
                    target_role_name = stolen_role.metadata.name if hasattr(stolen_role, 'metadata') else "Unknown"
                    if target_role_name == "Thần Tình Yêu" or "Lover" in stolen_role.__class__.__name__:
                        embed.add_field(
                            name="⚠️ **Quy Tắc Đặc Biệt**",
                            value="Người Tôi Tớ không trở thành Tình Nhân, nhưng người yêu cũ chết vì đau buồn.",
                            inline=False
                        )
                    
                    await self.channel.send(embed=embed)
                    
                    logger.info("Devoted Servant USED power | guild=%s servant=%s target=%s stolen_role=%s",
                               self.guild.id, servant.user_id, target_player.user_id, 
                               self._devoted_servant_stolen_role.metadata.name)
                    logger.info("_check_devoted_servant_power END (power used) | guild=%s servant=%s", 
                               self.guild.id, servant.user_id)
            else:
                logger.info("Devoted Servant CHOSE NOT to use power | guild=%s servant=%s target=%s",
                           self.guild.id, servant.user_id, target_player.user_id)
                logger.info("_check_devoted_servant_power END (power not used) | guild=%s servant=%s", 
                           self.guild.id, servant.user_id)
        
        except Exception as e:
            logger.error("ERROR in Devoted Servant power check | guild=%s servant=%s target=%s error=%s",
                        self.guild.id, servant.user_id, target_player.user_id, str(e), exc_info=True)


    async def _handle_seer(self, seer: PlayerState) -> None:
        options = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != seer.user_id}
        if not options:
            logger.info("Seer has no targets | guild=%s seer=%s night=%s", 
                        self.guild.id, seer.user_id, self.night_number)
            return
        
        choice = await self._prompt_dm_choice(
            seer,
            title="Tiên tri soi",
            description="Chọn một người để soi đêm nay.",
            options=options,
            allow_skip=True,
        )
        if choice is None:
            logger.info("Seer skipped peeking | guild=%s seer=%s night=%s", 
                        self.guild.id, seer.user_id, self.night_number)
            return
        
        target_id = choice
        target = self.players.get(target_id)
        if not target or not target.role:
            logger.warning("Seer target not found | guild=%s seer=%s target=%s", 
                           self.guild.id, seer.user_id, target_id)
            return
        
        # Check if target is Wolf Sister and Wolf Brother is still alive - hide her alignment
        is_hidden_wolf_sister = False
        if self._wolf_sister_id == target_id and self._wolf_brother_id:
            brother = self.players.get(self._wolf_brother_id)
            if brother and brother.alive:
                # Sister is hidden - report her as villager
                faction = Alignment.VILLAGE
                is_hidden_wolf_sister = True
                logger.info("Wolf Sister hidden from Seer | guild=%s seer=%s sister=%s brother_alive=true", 
                           self.guild.id, seer.user_id, target_id)
            else:
                # Brother is dead, report actual alignment (WEREWOLF)
                faction = target.role.alignment
        else:
            # Check if target is Avenger - use their chosen side (or NEUTRAL if not chosen yet)
            faction = target.role.alignment
            for role in target.roles:
                if hasattr(role, '__class__') and role.__class__.__name__ == 'Avenger':
                    if hasattr(role, 'chosen_side') and role.chosen_side:
                        faction = role.chosen_side
                        logger.info("Seer peeks Avenger as %s | guild=%s seer=%s avenger=%s", 
                                   faction.value, self.guild.id, seer.user_id, target_id)
                    break
        
        message = "Người đó thuộc phe Dân Làng." if faction == Alignment.VILLAGE else "Người đó thuộc phe Ma Sói." if faction == Alignment.WEREWOLF else "Người đó thuộc phe Trung Lập."
        
        logger.info("Seer peek | guild=%s seer=%s target=%s faction=%s night=%s hidden=%s", 
                    self.guild.id, seer.user_id, target_id, faction.value, self.night_number, is_hidden_wolf_sister)
        
        try:
            await seer.member.send(message)
        except discord.HTTPException:
            pass
        
        # Track seer wolf streak for achievement
        if faction == Alignment.WEREWOLF:
            seer.seer_wolf_streak += 1
        else:
            seer.seer_wolf_streak = 0
        
        logger.info("Seer peek | guild=%s seer=%s target=%s faction=%s streak=%s", self.guild.id, seer.user_id, target_id, faction, seer.seer_wolf_streak)

    async def _handle_witch(self, witch: PlayerState, killed_id: Optional[int]) -> Optional[int]:
        role = witch.role
        heal_available = getattr(role, "heal_available", True)
        kill_available = getattr(role, "kill_available", True)
        saved = False
        
        logger.info("Witch action start | guild=%s witch=%s night=%s heal_available=%s kill_available=%s killed_id=%s", 
                    self.guild.id, witch.user_id, self.night_number, heal_available, kill_available, killed_id)
        
        if killed_id and heal_available:
            logger.info("Witch asking to heal | guild=%s witch=%s killed_id=%s", 
                        self.guild.id, witch.user_id, killed_id)
            choice = await self._prompt_dm_choice(
                witch,
                title="Phù thủy",
                description="Một người vừa bị tấn công. Bạn có muốn cứu?",
                options={1: "Cứu"},
                allow_skip=True,
            )
            if choice == 1:
                saved = True
                role.heal_available = False  # type: ignore[attr-defined]
                witch.witch_used_save = True  # Track for achievement
                await witch.member.send("Bạn đã dùng bình hồi sinh.")
                logger.info("Witch used heal potion | guild=%s witch=%s target=%s night=%s", 
                            self.guild.id, witch.user_id, killed_id, self.night_number)
            else:
                logger.info("Witch skipped healing | guild=%s witch=%s night=%s", 
                            self.guild.id, witch.user_id, self.night_number)
        else:
            logger.info("Witch no heal needed | guild=%s witch=%s heal_available=%s killed_id=%s", 
                        self.guild.id, witch.user_id, heal_available, killed_id)
        
        kill_target = None
        if kill_available:
            logger.info("Witch asking to poison | guild=%s witch=%s night=%s", 
                        self.guild.id, witch.user_id, self.night_number)
            options = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != witch.user_id}
            logger.info("Witch poison options | guild=%s witch=%s options_count=%s", 
                        self.guild.id, witch.user_id, len(options))
            choice = await self._prompt_dm_choice(
                witch,
                title="Phù thủy",
                description="Bạn muốn sử dụng bình độc?",
                options=options,
                allow_skip=True,
            )
            logger.info("Witch poison choice | guild=%s witch=%s choice=%s", 
                        self.guild.id, witch.user_id, choice)
            if choice is not None and choice in options:
                if choice == witch.user_id and not witch.role.can_self_target():
                    logger.info("Witch tried self-target without permission | guild=%s witch=%s", 
                                self.guild.id, witch.user_id)
                    return None if saved else killed_id
                kill_target = choice
                role.kill_available = False  # type: ignore[attr-defined]
                witch.witch_used_kill = True  # Track for achievement
                if kill_target == witch.user_id:
                    witch.role.mark_self_target()
                    await witch.member.send("Bạn đã tự kết liễu chính mình.")
                    logger.info("Witch self-targeted with poison | guild=%s witch=%s night=%s", 
                                self.guild.id, witch.user_id, self.night_number)
                logger.info("Witch poison target chosen | guild=%s witch=%s target=%s night=%s", 
                            self.guild.id, witch.user_id, kill_target, self.night_number)
            else:
                logger.info("Witch skipped poison | guild=%s witch=%s night=%s", 
                            self.guild.id, witch.user_id, self.night_number)
        else:
            logger.info("Witch no poison available | guild=%s witch=%s night=%s", 
                        self.guild.id, witch.user_id, self.night_number)
        
        if kill_target:
            # Check if Pharmacist's antidote saves this target
            if kill_target == self._pharmacist_antidote_target:
                await self.channel.send(f"💊 Bình hồi phục của Dược Sĩ đã cứu sống <@{kill_target}> khỏi bình độc của Phù thủy!")
                logger.info("Pharmacist antidote saved target | guild=%s witch=%s target=%s pharmacist_antidote=%s", 
                            self.guild.id, witch.user_id, kill_target, self._pharmacist_antidote_target)
            else:
                self._pending_deaths.append((kill_target, "witch"))
                logger.info("Witch used poison | guild=%s witch=%s target=%s", self.guild.id, witch.user_id, kill_target)
        
        return None if saved else killed_id

    async def _handle_little_girl(self, little: PlayerState) -> Optional[bool]:
        """Handle little girl peeking. Returns True if discovered, False/None if not.
        
        From night 2, little girl can peek when wolves wake up.
        There's a small chance (20%) she's discovered if peeking.
        """
        # Can only peek from night 2 onwards
        if self.night_number < 2:
            return None
        
        wolves = [p for p in self.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        if not wolves:
            return None
        
        # Ask if she wants to peek
        can_peek = await self._prompt_dm_choice(
            little,
            title="Cô bé - Hé mắt nhìn",
            description="Bạn có muốn hé mắt nhìn khi các Ma Sói thức giấc không?",
            options={1: "Có, hé mắt", 0: "Không, ngủ tiếp"},
            allow_skip=False,
        )
        
        if not can_peek:
            logger.info("Little girl chose not to peek | guild=%s night=%s", self.guild.id, self.night_number)
            return None
        
        wolf_names = ", ".join(p.display_name() for p in wolves)
        message = "Bạn hé mắt và thấy: " + wolf_names
        with contextlib.suppress(discord.HTTPException):
            await little.member.send(message)
        
        # 20% chance of being discovered while peeking
        discovered = random.random() < 0.2
        
        if discovered:
            self._little_girl_peeking = little.user_id
            logger.info("Little girl discovered peeking | guild=%s night=%s chance=20%%", self.guild.id, self.night_number)
            # Notify wolves that they spotted someone peeking
            if self._wolf_thread:
                await self._wolf_thread.send(
                    "⚠️ **Cảnh báo:** Các bạn phát hiện có ai đó đang hé mắt nhìn các bạn! "
                    "Bạn muốn thay đổi mục tiêu và giết người đó thay thế không?"
                )
            return True
        else:
            logger.info("Little girl peeked undetected | guild=%s night=%s", self.guild.id, self.night_number)
            return False

    async def _handle_raven(self, raven: PlayerState) -> None:
        options = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != raven.user_id}
        if not options:
            return
        choice = await self._prompt_dm_choice(
            raven,
            title="Con quạ nguyền rủa",
            description="Chọn một người sẽ bị cộng thêm 2 phiếu vào sáng mai.",
            options=options,
            allow_skip=True,
        )
        if choice is None or choice not in options:
            return
        target = self.players.get(choice)
        if target:
            target.marked_by_raven = True
            with contextlib.suppress(discord.HTTPException):
                await raven.member.send(f"Bạn đã nguyền {target.display_name()}.")
            logger.info("Raven marked target | guild=%s raven=%s target=%s", self.guild.id, raven.user_id, target.user_id)

    async def _handle_piper(self, piper: PlayerState) -> None:
        self._piper_id = piper.user_id
        available = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != piper.user_id and p.user_id not in self._charmed}
        charmed_now: List[int] = []
        while available and len(charmed_now) < 2:
            choice = await self._prompt_dm_choice(
                piper,
                title="Thổi sáo",
                description="Chọn người để thôi miên.",
                options=available,
                allow_skip=True,
            )
            if choice is None or choice not in available:
                break
            self._charmed.add(choice)
            charmed_now.append(choice)
            available.pop(choice, None)
        for pid in charmed_now:
            target = self.players.get(pid)
            if target:
                with contextlib.suppress(discord.HTTPException):
                    await target.member.send("Bạn nghe tiếng sáo lạ và thấy mình như bị thôi miên.")
        if charmed_now:
            logger.info("Piper charmed | guild=%s piper=%s targets=%s", self.guild.id, piper.user_id, charmed_now)

    async def _handle_white_wolf(self, white_wolf: PlayerState) -> Optional[int]:
        if not white_wolf.alive:
            return None
        if (self.night_number % 2) != 0:
            return None
        options = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != white_wolf.user_id and any(r.alignment == Alignment.WEREWOLF for r in p.roles)}
        if not options:
            return None
        choice = await self._prompt_dm_choice(
            white_wolf,
            title="Sói trắng",
            description="Bạn có thể loại bỏ một đồng loại.",
            options=options,
            allow_skip=True,
        )
        if choice is None or choice not in options:
            return None
        if choice == white_wolf.user_id and not white_wolf.role.can_self_target():
            return None
        if choice == white_wolf.user_id:
            white_wolf.role.mark_self_target()
        logger.info("White wolf acted | guild=%s player=%s target=%s", self.guild.id, white_wolf.user_id, choice)
        return choice

    async def _handle_pyromaniac(self, pyro: PlayerState) -> None:
        role = pyro.role
        if not role or getattr(role, "ignited", False):
            return
        options = {p.user_id: p.display_name() for p in self.alive_players()}
        choice = await self._prompt_dm_choice(
            pyro,
            title="Kẻ phóng hỏa",
            description="Bạn muốn thiêu rụi ngôi nhà của ai? (chỉ một lần)",
            options=options,
            allow_skip=True,
        )
        if choice is None or choice not in options:
            return
        if choice == pyro.user_id and not pyro.role.can_self_target():
            return
        role.ignited = True  # type: ignore[attr-defined]
        if choice == pyro.user_id:
            pyro.role.mark_self_target()
            await pyro.member.send("Bạn đã đốt chính ngôi nhà của mình.")
        self._pending_deaths.append((choice, "pyro"))
        logger.info("Pyromaniac ignited | guild=%s pyro=%s target=%s", self.guild.id, pyro.user_id, choice)

    async def _handle_moon_maiden(self, moon_maiden: PlayerState) -> None:
        """Handle Moon Maiden's ability to disable a target's night abilities."""
        role = moon_maiden.role
        if not role:
            return
        
        # Get alive players, excluding self and last target
        alive = self.alive_players()
        options = {
            p.user_id: p.display_name() 
            for p in alive 
            if p.user_id != moon_maiden.user_id 
            and p.user_id != getattr(role, "last_target_id", None)
        }
        
        if not options:
            return
        
        choice = await self._prompt_dm_choice(
            moon_maiden,
            title="Nguyệt Nữ",
            description="Đêm nay, bạn muốn vô hiệu hóa kĩ năng ban đêm của ai?",
            options=options,
            allow_skip=True,
        )
        
        if choice is None or choice not in options:
            return
        
        role.last_target_id = choice  # type: ignore[attr-defined]
        self._moon_maiden_disabled = choice
        
        target = self.players.get(choice)
        if target:
            await self._safe_send_dm(
                target.member,
                f"Nguyệt Nữ đã chọn bạn làm mục tiêu. Kĩ năng ban đêm của bạn sẽ bị vô hiệu hóa!"
            )
        
        logger.info("Moon Maiden disabled | guild=%s maiden=%s target=%s", self.guild.id, moon_maiden.user_id, choice)

    async def _handle_hypnotist(self, hypnotist: PlayerState) -> None:
        """Handle Hypnotist's ability to charm a target. If Hypnotist dies, charmed target dies instead."""
        role = hypnotist.role
        if not role:
            return
        
        # Get alive players, excluding self and last target
        alive = self.alive_players()
        options = {
            p.user_id: p.display_name() 
            for p in alive 
            if p.user_id != hypnotist.user_id 
            and p.user_id != getattr(role, "last_target_id", None)
        }
        
        if not options:
            return
        
        choice = await self._prompt_dm_choice(
            hypnotist,
            title="Cổ Hoặc Sư",
            description="Hãy chọn 1 người để mê hoặc. Nếu bạn chết đêm nay, họ sẽ chết thay bạn.",
            options=options,
            allow_skip=True,
        )
        
        if choice is None or choice not in options:
            return
        
        role.last_target_id = choice  # type: ignore[attr-defined]
        role.charmed_target_id = choice  # type: ignore[attr-defined]
        self._hypnotist_charm_target = choice
        
        target = self.players.get(choice)
        if target:
            await self._safe_send_dm(
                hypnotist.member,
                f"Bạn đã mê hoặc {target.display_name()}. Nếu bạn chết đêm nay, họ sẽ chết thay bạn."
            )
            await self._safe_send_dm(
                target.member,
                "Bạn đã bị Cổ Hoặc Sư mê hoặc! Nếu Cổ Hoặc Sư chết đêm nay, bạn sẽ chết thay họ."
            )
        
        logger.info("Hypnotist charmed | guild=%s hypnotist=%s target=%s", self.guild.id, hypnotist.user_id, choice)

    def _handle_elder_resistance(self, target_id: int) -> bool:
        target = self.players.get(target_id)
        if not target:
            return False
        
        # Find Elder role
        elder_role = None
        for role in target.roles:
            if role.metadata.name == "Già Làng":
                elder_role = role
                break
        
        if not elder_role:
            return False
        
        remaining = getattr(elder_role, "wolf_hits", 0)
        if remaining >= 1:
            return False
        elder_role.wolf_hits = remaining + 1  # type: ignore[attr-defined]
        
        # Track elder bitten for achievement
        target.elder_bitten = True

        async def notify() -> None:
            with contextlib.suppress(discord.HTTPException):
                await target.member.send("Bạn bị ma sói tấn công nhưng vẫn sống.")

        asyncio.create_task(notify())
        logger.info("Elder resisted wolf attack | guild=%s elder=%s", self.guild.id, target.user_id)
        return True

    def _find_role_holder(self, role_name: str) -> Optional[PlayerState]:
        """Find role holder - includes dead players to show action for all roles."""
        for player in self.players.values():
            for role in player.roles:
                if role.metadata.name == role_name:
                    return player
        return None

    def _build_role_layout(self, player_count: int, has_thief: bool = False) -> List[type[Role]]:
        """Build role layout using RoleConfig's dynamic distribution."""
        # If thief is present, we need player_count + 2 roles (2 extra for thief to choose from)
        target_count = player_count + 2 if has_thief else player_count
        
        # Get role distribution from RoleConfig
        role_names = RoleConfig.get_role_list(player_count, self.settings.expansions)
        
        # Add extra cards for thief if needed
        if has_thief:
            villager_cls = get_role_class("Dân Làng")
            role_names.extend(["Dân Làng", "Dân Làng"])  # Add 2 extra villagers
        
        # Convert role names to role classes
        layout: List[type[Role]] = []
        for role_name in role_names[:target_count]:
            try:
                role_cls = get_role_class(role_name)
                layout.append(role_cls)
            except KeyError:
                logger.warning("Role not found in registry: %s", role_name)
                # Fallback to villager
                layout.append(get_role_class("Dân Làng"))
        
        # Log balance info
        balance = RoleConfig.get_balance_info(player_count, self.settings.expansions)
        logger.info(
            "Role layout | guild=%s player_count=%s werewolves=%s village=%s neutral=%s",
            self.guild.id,
            player_count,
            balance.get(Alignment.WEREWOLF, 0),
            balance.get(Alignment.VILLAGE, 0),
            balance.get(Alignment.NEUTRAL, 0),
        )
        
        return layout

    async def _prompt_dm_choice(
        self,
        player: PlayerState,
        *,
        title: str,
        description: str,
        options: Dict[int, str],
        allow_skip: bool,
        timeout: int = 30,
    ) -> Optional[int]:
        view = _ChoiceView(options, allow_skip)
        embed = discord.Embed(title=title, description=description)
        embed.colour = discord.Colour.blurple()
        embed.add_field(name="Lựa chọn", value="\n".join(f"{idx}. {label}" for idx, label in options.items()))
        try:
            dm = player.member.dm_channel or await player.member.create_dm()
            message = await dm.send(embed=embed, view=view)
        except discord.HTTPException:
            return None
        try:
            await asyncio.wait_for(view.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            view.stop()
        finally:
            with contextlib.suppress(discord.HTTPException):
                await message.edit(view=None)
        return view.selected

    def _check_win_condition(self) -> bool:
        # CRITICAL: Log entry point
        logger.info(">>> _check_win_condition called | guild=%s", self.guild.id)
        
        # Check if Angel won on Day 1 (voted out)
        if self._angel_won:
            logger.info("Win condition met: Angel wins | guild=%s", self.guild.id)
            return True
        
        villagers = self.alive_by_alignment(Alignment.VILLAGE)
        wolves = self.alive_by_alignment(Alignment.WEREWOLF)
        neutrals = self.alive_by_alignment(Alignment.NEUTRAL)
        
        # Debug: check for death_pending players not included
        all_alive = len(self.alive_players())
        pending_deaths = sum(1 for p in self.players.values() if p.death_pending and not p.alive)
        all_players_count = len([p for p in self.players.values() if not p.death_pending])
        
        logger.info(">>> Win condition check | guild=%s villagers=%s wolves=%s neutrals=%s alive=%s pending_deaths=%s", 
                     self.guild.id, len(villagers), len(wolves), len(neutrals), all_alive, pending_deaths)
        
        # Info: list all players and their status
        for player in self.players.values():
            logger.info("Player status | guild=%s player=%s alive=%s death_pending=%s roles=%s",
                        self.guild.id, player.user_id, player.alive, player.death_pending, 
                        ", ".join(r.metadata.name for r in player.roles) if player.roles else "None")
        
        if not wolves and villagers:
            self._winner = Alignment.VILLAGE
            logger.info("Win condition met: Village wins | guild=%s (no wolves left)", self.guild.id)
            return True
        
        # Wolves win if equal to or greater than villagers
        if len(wolves) >= len(villagers) and villagers:
            self._winner = Alignment.WEREWOLF
            logger.info("Win condition met: Werewolf wins | guild=%s (wolves=%s >= villagers=%s)", self.guild.id, len(wolves), len(villagers))
            return True
        
        # Special case: 1 wolf vs 1 elder - wolf wins if elder has been hit once already
        if len(wolves) == 1 and len(villagers) == 1 and not neutrals:
            elder_role = None
            for role in villagers[0].roles:
                if role.metadata.name == "Cụ Già":
                    elder_role = role
                    break
            
            if elder_role:
                wolf_hits = getattr(elder_role, "wolf_hits", 0)
                if wolf_hits >= 1:  # Elder has been hit once, will die next attack
                    self._winner = Alignment.WEREWOLF
                    logger.info("Win condition met: Werewolf wins | guild=%s (1v1 vs Elder already hit %s time)", self.guild.id, wolf_hits)
                    return True
        
        if not villagers and wolves:
            self._winner = Alignment.WEREWOLF
            logger.info("Win condition met: Werewolf wins | guild=%s (no villagers left)", self.guild.id)
            return True
        
        if len(self._lovers) == 2:
            alive_lovers = [pid for pid in self._lovers if self.players.get(pid, None) and self.players[pid].alive]
            if len(alive_lovers) == 2 and len(self.alive_players()) == 2:
                self._winner = Alignment.NEUTRAL
                logger.info("Win condition met: Lovers win | guild=%s lovers=%s", 
                            self.guild.id, alive_lovers)
                return True
        
        if self._piper_id:
            piper = self.players.get(self._piper_id)
            if piper and piper.alive:
                # Pied Piper wins if all other players are charmed (must have at least 1 charmed)
                others = {p.user_id for p in self.alive_players() if p.user_id != piper.user_id}
                if len(self._charmed) > 0 and others.issubset(self._charmed):
                    self._winner = Alignment.NEUTRAL
                    logger.info("Win condition met: Pied Piper wins | guild=%s piper=%s charmed=%s", 
                                self.guild.id, piper.user_id, len(self._charmed))
                    return True
                else:
                    logger.info(">>> Pied Piper not winning | guild=%s charmed=%s others=%s", 
                                 self.guild.id, len(self._charmed), len(others))
        
        # Check Elder Man win condition
        if self._elder_man_id and self._elder_man_group1 and self._elder_man_group2:
            elder_man = self.players.get(self._elder_man_id)
            if elder_man and elder_man.alive:
                # Find which group Elder Man is in
                if self._elder_man_id in self._elder_man_group1:
                    opposing_group = self._elder_man_group2
                else:
                    opposing_group = self._elder_man_group1
                
                # Check if all members of opposing group are dead
                opposing_alive = [pid for pid in opposing_group if self.players.get(pid) and self.players[pid].alive]
                if not opposing_alive:
                    self._winner = Alignment.NEUTRAL
                    logger.info("Win condition met: Elder Man wins | guild=%s elder_man=%s opposing_group_dead=%s", 
                                self.guild.id, self._elder_man_id, len(opposing_group))
                    return True
        
        logger.info(">>> No win condition met - returning False | guild=%s", self.guild.id)
        return False

    async def _force_unmute_all(self) -> None:
        """Force unmute all players in voice channel when game ends."""
        if not self.voice_channel_id:
            return
        try:
            voice_channel = self.bot.get_channel(self.voice_channel_id)
            if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
                return
            
            # Unmute all players currently in the voice channel
            unmuted_count = 0
            for member in voice_channel.members:
                try:
                    if member.voice and member.voice.mute:  # Only unmute if currently muted
                        await member.edit(mute=False, reason="Werewolf: Game ended - force unmute")
                        unmuted_count += 1
                except discord.HTTPException as e:
                    logger.warning("Failed to unmute member on game end | guild=%s member=%s error=%s", 
                                 self.guild.id, member.id, str(e))
            
            if unmuted_count > 0:
                logger.info("Force unmuted all players | guild=%s voice_channel=%s unmuted_count=%s", 
                           self.guild.id, self.voice_channel_id, unmuted_count)
        except Exception as e:
            logger.error("Failed to force unmute all players | guild=%s error=%s", self.guild.id, str(e), exc_info=True)

    async def _clear_channel_permissions(self) -> None:
        """Clear all individual player permissions in game channel when game ends."""
        try:
            # Get all permission overwrites in the channel
            overwrites = dict(self.channel.overwrites)
            
            cleared_count = 0
            for target, permission_overwrite in overwrites.items():
                # Skip if target is a role (we only want to clear player permissions)
                if isinstance(target, discord.Role):
                    continue
                
                try:
                    # Delete individual player's permission overwrite
                    await self.channel.set_permissions(target, overwrite=None, reason="Werewolf: Game ended - reset permissions")
                    cleared_count += 1
                except discord.HTTPException as e:
                    logger.warning("Failed to clear permissions for player in game channel | guild=%s player=%s error=%s",
                                 self.guild.id, target.id if hasattr(target, 'id') else target, str(e))
            
            if cleared_count > 0:
                logger.info("Cleared channel permissions for all players | guild=%s channel=%s cleared_count=%s",
                           self.guild.id, self.channel.id, cleared_count)
        except Exception as e:
            logger.error("Failed to clear channel permissions | guild=%s error=%s", self.guild.id, str(e), exc_info=True)



    async def _distribute_rewards(self) -> None:
        """Distribute seed rewards based on game outcome"""
        if self._winner is None:
            return
        
        try:
            # Import EconomyCog dynamically to avoid circular imports
            from cogs.economy import EconomyCog
            
            # Get bot instance
            bot = None
            for attr in dir(self):
                if hasattr(getattr(self, attr, None), 'get_cog'):
                    bot = getattr(self, attr)
                    break
            
            # Alternative: access bot through guild
            if not bot:
                # Try to get bot from first player
                for player in self.players.values():
                    if hasattr(player.member, '_state') and hasattr(player.member._state, '_get_client'):
                        bot = player.member._state._get_client()
                        break
            
            if not bot:
                logger.warning("Could not access bot for reward distribution")
                return
            
            economy_cog = bot.get_cog("EconomyCog")
            if not economy_cog:
                logger.warning("EconomyCog not found for reward distribution")
                return
            
            # Check if harvest buff is active
            is_buff_active = await economy_cog.is_harvest_buff_active(self.guild.id)
            buff_multiplier = 2 if is_buff_active else 1
            
            # Calculate rewards
            winner_reward = 15 * buff_multiplier
            loser_reward = 5 * buff_multiplier
            
            # Get winner and loser alignments
            winner_alignment = self._winner
            loser_alignment = None
            
            # Determine loser alignment
            all_alignments = set()
            for player in self.players.values():
                alignment = player.get_alignment_priority()
                all_alignments.add(alignment)
            
            for alignment in all_alignments:
                if alignment != winner_alignment:
                    loser_alignment = alignment
                    break
            
            # Distribute rewards
            winners_list = []
            losers_list = []
            
            for player in self.players.values():
                player_alignment = player.get_alignment_priority()
                if player_alignment == winner_alignment:
                    await economy_cog.add_seeds_local(player.user_id, winner_reward)
                    winners_list.append(player.display_name())
                else:
                    await economy_cog.add_seeds_local(player.user_id, loser_reward)
                    losers_list.append(player.display_name())
            
            # Create reward embed
            mapping = {
                Alignment.VILLAGE: "Dân Làng",
                Alignment.WEREWOLF: "Ma Sói",
                Alignment.NEUTRAL: "Tình Nhân",
            }
            
            winner_name = mapping.get(winner_alignment, "Unknown")
            loser_name = mapping.get(loser_alignment, "Unknown") if loser_alignment else None
            
            embed = discord.Embed(
                title="🎮 Phần Thưởng Ma Sói",
                description=f"Game kết thúc! Phần thưởng đã được phát cho {winner_name}.",
                colour=discord.Colour.gold()
            )
            
            # Winners info
            if winners_list:
                winners_display = ", ".join(winners_list)
                embed.add_field(
                    name=f"👑 {winner_name} Thắng",
                    value=f"{winners_display}\n+{winner_reward} 🌱 mỗi người",
                    inline=False
                )
            
            # Losers info (if any)
            if losers_list and loser_name:
                losers_display = ", ".join(losers_list)
                embed.add_field(
                    name=f"🤝 {loser_name}",
                    value=f"{losers_display}\n+{loser_reward} 🌱 mỗi người",
                    inline=False
                )
            
            # Buff info
            if is_buff_active:
                embed.add_field(
                    name="🔥 Cộng Hưởng Sinh Lực (Harvest Buff)",
                    value="Phần thưởng được nhân 2x!",
                    inline=False
                )
            
            try:
                await self.channel.send(embed=embed)
            except Exception as e:
                logger.error("Failed to send reward embed: %s", str(e))
        
        except Exception as e:
            logger.error("Error distributing rewards: %s", str(e), exc_info=True)

    async def _check_werewolf_achievements(self) -> None:
        """Check and unlock werewolf achievements based on game outcome."""
        try:
            # Import here to avoid circular imports
            from database_manager import increment_stat, get_stat
            from core.achievement_system import AchievementManager

            # Get achievement manager
            if not hasattr(self.bot, 'achievement_manager'):
                self.bot.achievement_manager = AchievementManager(self.bot)

            # Check achievements for all players
            for player in self.players.values():
                user_id = player.user_id

                # 1. Check win-based achievements
                if self._winner == Alignment.WEREWOLF:
                    # Check if player was White Wolf and won alone
                    if player.role.name == "Sói Trắng":
                        # Count alive wolves
                        alive_wolves = [p for p in self.alive_players() if p.get_alignment_priority() == Alignment.WEREWOLF]
                        if len(alive_wolves) == 1 and alive_wolves[0].user_id == user_id:
                            await increment_stat(user_id, "werewolf", "white_wolf_win", 1)
                            current = await get_stat(user_id, "werewolf", "white_wolf_win", 0)
                            await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "white_wolf_win", current, self.channel)

                elif self._winner == Alignment.NEUTRAL:
                    # Check if player was Pied Piper and charmed everyone
                    if player.role.name == "Thổi Sáo":
                        await increment_stat(user_id, "werewolf", "pied_piper_win", 1)
                        current = await get_stat(user_id, "werewolf", "pied_piper_win", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "pied_piper_win", current, self.channel)

                    # Check if player was part of winning couple
                    if user_id in getattr(self, '_lovers', set()):
                        await increment_stat(user_id, "werewolf", "couple_win", 1)
                        current = await get_stat(user_id, "werewolf", "couple_win", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "couple_win", current, self.channel)

                # 2. Check role-specific achievements
                # Perfect Witch: used both potions in one game
                if player.role.name == "Phù Thủy":
                    if player.witch_used_save and player.witch_used_kill:
                        await increment_stat(user_id, "werewolf", "witch_perfect_play", 1)
                        current = await get_stat(user_id, "werewolf", "witch_perfect_play", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "witch_perfect_play", current, self.channel)

                # Hunter kill wolf
                if player.role.name == "Hunter" and player.hunter_killed_wolf:
                    await increment_stat(user_id, "werewolf", "hunter_kill_wolf", 1)
                    current = await get_stat(user_id, "werewolf", "hunter_kill_wolf", 0)
                    await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "hunter_kill_wolf", current, self.channel)

                # Bodyguard save
                if player.role.name == "Bodyguard":
                    # Count successful saves during the game
                    save_count = player.bodyguard_saves
                    if save_count > 0:
                        await increment_stat(user_id, "werewolf", "bodyguard_save", save_count)
                        current = await get_stat(user_id, "werewolf", "bodyguard_save", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "bodyguard_save", current, self.channel)

                # Arsonist burn 3+ players
                if player.role.name == "Arsonist":
                    burn_count = player.arsonist_burns
                    if burn_count >= 3:
                        await increment_stat(user_id, "werewolf", "arsonist_burn", 1)
                        current = await get_stat(user_id, "werewolf", "arsonist_burn", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "arsonist_burn", current, self.channel)

                # Seer find wolf streak
                if player.role.name == "Seer":
                    streak = player.seer_wolf_streak
                    if streak >= 3:
                        await increment_stat(user_id, "werewolf", "seer_find_wolf_streak", 1)
                        current = await get_stat(user_id, "werewolf", "seer_find_wolf_streak", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "seer_find_wolf_streak", current, self.channel)

                # Fool hanged
                if player.fool_hanged:
                    await increment_stat(user_id, "werewolf", "fool_hanged", 1)
                    current = await get_stat(user_id, "werewolf", "fool_hanged", 0)
                    await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "fool_hanged", current, self.channel)

                # Die first night/day
                death_phase = None
                for pid, cause, phase in self._death_log:
                    if pid == user_id:
                        death_phase = phase
                        break

                if death_phase:
                    if "Night 1" in death_phase or "Day 1" in death_phase:
                        await increment_stat(user_id, "werewolf", "die_first_night", 1)
                        current = await get_stat(user_id, "werewolf", "die_first_night", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "die_first_night", current, self.channel)

                # Elder survive bite
                if player.role.name == "Elder" and player in self.alive_players():
                    # Check if elder was bitten but survived
                    if player.elder_bitten:
                        await increment_stat(user_id, "werewolf", "elder_survive_bite", 1)
                        current = await get_stat(user_id, "werewolf", "elder_survive_bite", 0)
                        await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "elder_survive_bite", current, self.channel)

                # Fire Wolf win alive
                if player.role.name == "Fire Wolf" and self._winner == Alignment.WEREWOLF and player in self.alive_players():
                    await increment_stat(user_id, "werewolf", "fire_wolf_win_alive", 1)
                    current = await get_stat(user_id, "werewolf", "fire_wolf_win_alive", 0)
                    await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "fire_wolf_win_alive", current, self.channel)

                # Assassin kill
                if player.assassin_killed:
                    await increment_stat(user_id, "werewolf", "assassin_kill", 1)
                    current = await get_stat(user_id, "werewolf", "assassin_kill", 0)
                    await self.bot.achievement_manager.check_unlock(user_id, "werewolf", "assassin_kill", current, self.channel)

        except Exception as e:
            logger.error("Error checking werewolf achievements: %s", str(e), exc_info=True)

        # Check werewolf achievements after game ends
        await self._check_werewolf_achievements()

    async def _announce_winner(self) -> None:
        if self._winner is None:
            embed = discord.Embed(
                title="⚠️ Kết Thúc Trận Đấu",
                description="Trận đấu kết thúc mà không xác định được phe thắng.",
                colour=discord.Colour.greyple(),
            )
            embed.set_image(url=CARD_BACK_URL)
            await self.channel.send(embed=embed)
            return
        
        # Distribute rewards first
        await self._distribute_rewards()
        
        # Then announce winner
        mapping = {
            Alignment.VILLAGE: ("Dân Làng", discord.Colour.green()),
            Alignment.WEREWOLF: ("Ma Sói", discord.Colour.red()),
            Alignment.NEUTRAL: ("Tình Nhân", discord.Colour.purple()),
        }
        faction_name, faction_colour = mapping[self._winner]
        
        # Compose detailed death summary grouped by phase
        survivors = ", ".join(p.display_name() for p in self.alive_players()) or "Không còn ai sống"
        
        # Group deaths by phase (preserves insertion order in Python 3.7+)
        deaths_by_phase: Dict[str, List[str]] = {}
        for pid, cause, phase in self._death_log:
            player = self.players.get(pid)
            name = player.display_name() if player else str(pid)
            text = name
            if cause == "wolves":
                text += " bị sói cắn"
            elif cause == "white_wolf":
                text += " bị sói trắng giết"
            elif cause == "witch":
                text += " bị phù thủy đầu độc"
            elif cause == "pyro":
                text += " bị kẻ phóng hỏa thiêu"
            elif cause == "lynch":
                text += " bị treo cổ"
            elif cause == "hunter":
                text = f"Thợ săn bắn hạ {name}"
            elif cause == "lover":
                text += " chết theo người yêu"
            elif cause == "scapegoat":
                text = f"Kẻ thế thân bị hiến tế ({name})"
            else:
                text += f" chết ({cause})"
            
            if phase not in deaths_by_phase:
                deaths_by_phase[phase] = []
            deaths_by_phase[phase].append(text)
        
        embed = discord.Embed(
            title="🏆 Trò Chơi Kết Thúc",
            description=f"Phe Chiến Thắng: **{faction_name}**",
            colour=faction_colour,
        )
        embed.add_field(name="Người Sống Sót", value=survivors, inline=False)
        
        # Add death summary for each phase in order
        for phase, deaths in deaths_by_phase.items():
            if deaths:
                embed.add_field(name=phase, value="; ".join(deaths), inline=False)
        embed.set_image(url=CARD_BACK_URL)
        await self.channel.send(embed=embed)

    async def _transform_wolf_sister(self, sister: PlayerState, dead_brother: PlayerState) -> None:
        """Transform Wolf Sister into full werewolf when her brother dies."""
        if not sister.roles:
            return
        
        # Get the sister's role
        from ..roles.werewolves.wolf_sister import WolfSister
        sister_role = sister.roles[0]
        
        if not isinstance(sister_role, WolfSister):
            return
        
        # Mark sister as transformed
        sister_role.is_transformed = True
        
        # Change alignment to werewolf
        sister_role.metadata.alignment = Alignment.WEREWOLF
        
        # Notify the sister
        try:
            await sister.member.send(
                f"🐺💢 **TỨC GIẬN!** Anh sói {dead_brother.display_name()} đã chết!\n"
                f"Bạn giận dữ gia nhập phe sói ngay lập tức. Bây giờ bạn sẽ dậy cùng phe sói mỗi đêm để giết người!"
            )
        except discord.HTTPException:
            pass
        
        # Notify all wolves about the new member
        wolves = [p for p in self.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        wolf_names = ", ".join(p.display_name() for p in wolves)
        
        if self._wolf_thread:
            try:
                await self._wolf_thread.send(
                    f"🐺💢 **Sói Em {sister.display_name()} tức giận gia nhập phe sói!**\n"
                    f"Đồng đội sói hiện tại: {wolf_names}"
                )
            except discord.HTTPException:
                pass
        
        logger.info(
            "Wolf Sister transformed to werewolf | guild=%s sister=%s brother=%s",
            self.guild.id,
            sister.user_id,
            dead_brother.user_id,
        )

    async def _restrict_dead_player(self, player: PlayerState) -> None:
        """Prevent dead player from unmuting, messaging in channels and threads."""
        if not player.member:
            return
        
        try:
            # 1. Mute dead player in voice channel
            if self.voice_channel_id:
                voice_channel = self.bot.get_channel(self.voice_channel_id)
                if voice_channel and isinstance(voice_channel, discord.VoiceChannel):
                    try:
                        if player.member.voice:
                            await player.member.edit(mute=True, reason="Werewolf: Player died - mute voice")
                    except discord.HTTPException:
                        pass
            
            # 2. Prevent dead player from messaging in main game channel
            if self._player_role:
                # Remove player role to revoke channel access
                try:
                    await player.member.remove_roles(self._player_role, reason="Werewolf: Player died - remove from game")
                except discord.HTTPException as e:
                    logger.warning("Failed to remove player role | guild=%s player=%s error=%s",
                                 self.guild.id, player.user_id, str(e))
            else:
                # Fallback: set individual permissions
                try:
                    await self.channel.set_permissions(
                        player.member,
                        send_messages=False,
                        reason="Werewolf: Player died - mute text chat"
                    )
                except discord.HTTPException as e:
                    logger.warning("Failed to restrict dead player in game channel | guild=%s player=%s error=%s", 
                                 self.guild.id, player.user_id, str(e))
            
            # 3. Prevent dead player from messaging in werewolf thread
            if self._wolf_thread:
                try:
                    await self._wolf_thread.set_permissions(
                        player.member,
                        send_messages=False,
                        reason="Werewolf: Player died - mute werewolf thread"
                    )
                except (discord.HTTPException, AttributeError):
                    pass
            
            # 4. Prevent dead player from messaging in sisters thread if it exists
            if self._sisters_thread:
                try:
                    await self._sisters_thread.set_permissions(
                        player.member,
                        send_messages=False,
                        reason="Werewolf: Player died - mute sisters thread"
                    )
                except (discord.HTTPException, AttributeError):
                    pass
        except Exception as e:
            logger.error("Failed to restrict dead player | guild=%s player=%s error=%s", 
                        self.guild.id, player.user_id, str(e), exc_info=True)

    async def _handle_mayor_succession(self, player: PlayerState) -> None:
        """Transfer Mayor status to another player if dying player is a Mayor."""
        if not player.mayor:
            return
        
        alive = [p for p in self.alive_players() if p.user_id != player.user_id]
        if not alive:
            return
        
        # Remove mayor status from dying player
        player.mayor = False
        player.vote_weight = 1
        
        options = {p.user_id: p.display_name() for p in alive}
        choice = await self._prompt_dm_choice(
            player,
            title="Trưởng Làng - Chọn người kế nhiệm",
            description="Bạn sắp chết. Hãy chọn người kế nhiệm chức Trưởng Làng.",
            options=options,
            allow_skip=False,
            timeout=30,
        )
        
        if choice and choice in options:
            successor = self.players.get(choice)
            if successor and successor.alive:
                successor.mayor = True
                successor.vote_weight = 2
                
                try:
                    await successor.member.send(f"Bạn đã được {player.display_name()} chỉ định làm Trưởng Làng kế nhiệm! Phiếu bạn tính x2 và bạn phá vỡ hòa phiếu.")
                    await self.channel.send(f"{successor.display_name()} đã trở thành Trưởng Làng mới!")
                except:
                    pass

    async def _handle_death(self, player: PlayerState, *, cause: str) -> None:
        """Handle player death: mark as dead, disable permissions, trigger role death effects."""
        # Check if Hypnotist has charmed someone - if so, swap deaths
        from ..roles.villagers.hypnotist import Hypnotist
        
        hypnotist_role = None
        for role in player.roles:
            if isinstance(role, Hypnotist):
                hypnotist_role = role
                break
        
        # If this Hypnotist has a charmed target, the charmed target dies instead
        if hypnotist_role and hasattr(hypnotist_role, 'charmed_target_id') and hypnotist_role.charmed_target_id:
            charmed_id = hypnotist_role.charmed_target_id
            charmed_player = self.players.get(charmed_id)
            
            # Only swap if charmed player is alive and not already dead
            if charmed_player and charmed_player.alive and not charmed_player.death_pending:
                # Kill the charmed player instead of the Hypnotist
                charmed_player.alive = False
                charmed_player.death_pending = True
                
                # Notify the Hypnotist that charm protected them
                await self._safe_send_dm(
                    player.member,
                    f"Nước cờ mê hoặc của bạn đã hoạt động! {charmed_player.display_name()} chết thay bạn."
                )
                
                # Trigger death effects for charmed player
                try:
                    await self._handle_death(charmed_player, cause="hypnotist_charm")
                except Exception as e:
                    logger.error(
                        "Error in charmed target death | guild=%s hypnotist=%s target=%s error=%s",
                        self.guild.id, player.user_id, charmed_id, str(e), exc_info=True
                    )
                
                # Hypnotist survives this death, return without marking them dead
                return
        
        # Record death for end-of-game summary with phase label and number
        if self.phase == Phase.NIGHT:
            phase_label = f"Đêm {self.night_number}"
        else:
            phase_label = f"Ngày {self.day_number}"
        self._death_log.append((player.user_id, cause, phase_label))
        
        # Mark player as dead
        player.alive = False
        
        # Track if a werewolf dies during the day (for Fire Wolf ability)
        if self.phase == Phase.DAY and any(r.alignment == Alignment.WEREWOLF for r in player.roles):
            self._wolves_died_today.append(player.user_id)
            logger.info("Wolf died during day | guild=%s player=%s day=%s total_wolves_today=%s", 
                       self.guild.id, player.user_id, self.day_number, len(self._wolves_died_today))
        
        # Disable dead player permissions immediately
        await self._restrict_dead_player(player)
        
        # Handle Mayor succession if player is a Mayor (must be before role on_death for prompt)
        if player.mayor:
            await self._handle_mayor_succession(player)
        
        # Trigger role death effects for all roles
        for role in player.roles:
            await role.on_death(self, player, cause)
        
        # If lover exists and is alive, they also die
        if player.lover_id:
            lover = self.players.get(player.lover_id)
            if lover and lover.alive:
                lover.alive = False
                lover.death_pending = True
                await self._handle_death(lover, cause="lover")
        
        # Check if Wolf Brother died - trigger Wolf Sister transformation if alive
        wolf_brother_role = None
        for role in player.roles:
            if hasattr(role, '__class__') and role.__class__.__name__ == 'WolfBrother':
                wolf_brother_role = role
                break
        
        if wolf_brother_role and self._wolf_sister_id:
            sister = self.players.get(self._wolf_sister_id)
            if sister and sister.alive:
                logger.info("Wolf Brother died, triggering sister transformation | guild=%s brother=%s sister=%s", 
                           self.guild.id, player.user_id, sister.user_id)
                await self._transform_wolf_sister(sister, player)
        
        logger.info("Player died | guild=%s player=%s cause=%s", self.guild.id, player.display_name(), cause)

    async def _run_countdown(self, channel: discord.abc.Messageable, label: str, seconds: int, step: int = 3) -> None:
        if seconds <= 0:
            return
        try:
            message = await channel.send(f"{label}: {seconds}s")
        except discord.HTTPException:
            return
        remaining = seconds
        try:
            while remaining > 0:
                await asyncio.sleep(min(step, remaining))
                remaining -= step
                if remaining < 0:
                    remaining = 0
                with contextlib.suppress(discord.HTTPException):
                    await message.edit(content=f"{label}: {remaining}s")
        except asyncio.CancelledError:
            return
        with contextlib.suppress(discord.HTTPException):
            await message.edit(content=f"{label}: hết giờ")

    async def _safe_send_dm(self, member: discord.Member, content: Optional[str] = None, embed: Optional[discord.Embed] = None, max_retries: int = 2) -> bool:
        """Send DM to player with retry logic and fallback notification. Returns True if sent successfully."""
        if not member:
            return False
        
        for attempt in range(max_retries):
            try:
                await member.send(content=content, embed=embed)
                return True
            except discord.Forbidden:
                # User has DMs disabled - notify in game channel if possible
                try:
                    fallback_msg = embed.title if embed else content
                    await self.channel.send(
                        f"⚠️ Không thể gửi DM cho {member.mention} - họ đã tắt DMs. "
                        f"Thông tin: {fallback_msg}"
                    )
                except discord.HTTPException:
                    pass
                logger.warning(
                    "User has DMs disabled | guild=%s member=%s",
                    self.guild.id, member.id
                )
                return False
            except discord.HTTPException as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Retry after 1 second
                    continue
                logger.error(
                    "Failed to send DM after %d attempts | guild=%s member=%s error=%s",
                    max_retries, self.guild.id, member.id, str(e)
                )
                return False
            except Exception as e:
                logger.error(
                    "Unexpected error sending DM | guild=%s member=%s error=%s",
                    self.guild.id, member.id, str(e), exc_info=True
                )
                return False
        return False


class _LobbyView(discord.ui.View):
    def __init__(self, game: WerewolfGame) -> None:
        super().__init__(timeout=None)
        self.game = game
        self.add_item(_JoinButton(game))
        self.add_item(_LeaveButton(game))
        self.add_item(_StartButton(game))
        self.add_item(_ToggleExpansionButton(game, Expansion.NEW_MOON))
        self.add_item(_ToggleExpansionButton(game, Expansion.THE_VILLAGE))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.guild_id == self.game.guild.id


class _JoinButton(discord.ui.Button):
    def __init__(self, game: WerewolfGame) -> None:
        super().__init__(label="Tham gia", style=discord.ButtonStyle.primary)
        self.game = game

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id in self.game.players:
            await interaction.response.send_message("Bạn đã ở trong bàn.", ephemeral=True)
            return
        await self.game.add_player(interaction.user)  # type: ignore[arg-type]
        await interaction.response.send_message("Đã tham gia.", ephemeral=True)


class _LeaveButton(discord.ui.Button):
    def __init__(self, game: WerewolfGame) -> None:
        super().__init__(label="Rời bàn", style=discord.ButtonStyle.secondary)
        self.game = game

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id not in self.game.players:
            await interaction.response.send_message("Bạn chưa tham gia.", ephemeral=True)
            return
        if interaction.user.id == self.game.host.id:
            await interaction.response.send_message("Chủ bàn không thể rời bàn. Hãy huỷ bàn nếu muốn dừng.", ephemeral=True)
            return
        await self.game.remove_player(interaction.user)  # type: ignore[arg-type]
        await interaction.response.send_message("Đã rời bàn.", ephemeral=True)


class _StartButton(discord.ui.Button):
    def __init__(self, game: WerewolfGame) -> None:
        super().__init__(label="Bắt đầu", style=discord.ButtonStyle.success)
        self.game = game

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.game.host.id:
            await interaction.response.send_message("Chỉ chủ bàn mới bắt đầu được.", ephemeral=True)
            return
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=False)
            await self.game.start()
            logger.info("Start button acknowledged | guild=%s host=%s", self.game.guild.id, self.game.host.id)
            if interaction.response.is_done():
                await interaction.followup.send("Đã bắt đầu trận đấu.", ephemeral=True)
            else:
                await interaction.response.send_message("Đã bắt đầu trận đấu.", ephemeral=True)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error when starting game via button | guild=%s host=%s", self.game.guild.id, self.game.host.id)
            if interaction.response.is_done():
                await interaction.followup.send(str(exc), ephemeral=True)
            else:
                await interaction.response.send_message(str(exc), ephemeral=True)


class _ToggleExpansionButton(discord.ui.Button):
    def __init__(self, game: WerewolfGame, expansion: Expansion) -> None:
        label = "Bật New Moon" if expansion == Expansion.NEW_MOON else "Bật The Village"
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.game = game
        self.expansion = expansion

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.game.host.id:
            await interaction.response.send_message("Chỉ chủ bàn được thay đổi mở rộng.", ephemeral=True)
            return
        await self.game.toggle_expansion(self.expansion)
        await interaction.response.send_message("Đã cập nhật bản mở rộng.", ephemeral=True)




class _DiscussionSkipVoteView(discord.ui.View):
    """Vote to skip discussion phase. No timeout - menu stays available."""
    
    def __init__(self, game: WerewolfGame, alive_players: List[PlayerState]) -> None:
        super().__init__(timeout=None)
        self.game = game
        self.alive_players = alive_players
        self.skip_votes: Set[int] = set()
        self.dont_skip_votes: Set[int] = set()
        self.message: Optional[discord.Message] = None
    
    def can_skip(self) -> bool:
        """Check if all alive players voted to skip."""
        alive_ids = {p.user_id for p in self.alive_players}
        return len(self.skip_votes) == len(alive_ids) and len(self.skip_votes) > 0
    
    @discord.ui.button(label="Bỏ Qua", style=discord.ButtonStyle.green, emoji="⏭️")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id not in {p.user_id for p in self.alive_players}:
            await interaction.response.send_message("Bạn không phải người chơi sống.", ephemeral=True)
            return
        
        # Record vote
        self.skip_votes.add(interaction.user.id)
        self.dont_skip_votes.discard(interaction.user.id)
        
        skip_count = len(self.skip_votes)
        total = len(self.alive_players)
        
        await interaction.response.send_message(
            f"Bạn chọn bỏ qua!\n{skip_count}/{total} người bỏ qua",
            ephemeral=True
        )
        
        logger.info("Discussion skip vote | guild=%s player=%s skip_count=%s total=%s", 
                   self.game.guild.id, interaction.user.id, skip_count, total)
    
    @discord.ui.button(label="Không Bỏ", style=discord.ButtonStyle.red, emoji="🛑")
    async def dont_skip_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id not in {p.user_id for p in self.alive_players}:
            await interaction.response.send_message("Bạn không phải người chơi sống.", ephemeral=True)
            return
        
        # Record vote
        self.dont_skip_votes.add(interaction.user.id)
        self.skip_votes.discard(interaction.user.id)
        
        skip_count = len(self.skip_votes)
        total = len(self.alive_players)
        
        await interaction.response.send_message(
            f"❌ Bạn chọn không bỏ qua!\n📊 {skip_count}/{total} người bỏ qua",
            ephemeral=True
        )
        
        logger.info("Discussion no-skip vote | guild=%s player=%s skip_count=%s total=%s", 
                   self.game.guild.id, interaction.user.id, skip_count, total)


class _ChoiceView(discord.ui.View):
    def __init__(self, choices: Dict[int, str], allow_skip: bool) -> None:
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=label, value=str(idx)) for idx, label in choices.items()]
        if allow_skip:
            options.append(discord.SelectOption(label="Bỏ qua", value="skip"))
        self.select = discord.ui.Select(placeholder="Chọn", min_values=1, max_values=1, options=options)
        self.select.callback = self._on_select  # type: ignore[assignment]
        self.add_item(self.select)
        self.selected: Optional[int] = None

    async def _on_select(self, interaction: discord.Interaction) -> None:
        value = self.select.values[0]
        if value == "skip":
            self.selected = None
        else:
            self.selected = int(value)
        await interaction.response.send_message("Ghi nhận.", ephemeral=True)
        self.stop()
