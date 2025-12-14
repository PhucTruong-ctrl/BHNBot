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
from ..roles import get_role_class, load_all_roles
from ..roles.base import Alignment, Expansion, Role
from .state import GameSettings, Phase, PlayerState
from .voting import VoteSession

CARD_BACK_URL = "https://upload.wikimedia.org/wikipedia/vi/b/bf/Logo_The_Werewolves_of_Millers_Hollow.png"
# Lowered to 4 for easier local testing; raise back to 6 for production balance
MIN_PLAYERS = 4

load_all_roles()

logger = logging.getLogger("werewolf")


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
        expansions = ", ".join(expansion_labels[exp] for exp in self.settings.expansions) if self.settings.expansions else "Chỉ bản cơ bản"
        embed = discord.Embed(
            title="Ma Sói – Thiercelieux",
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

    def list_players(self) -> Sequence[PlayerState]:
        return list(self.players.values())

    def alive_players(self) -> List[PlayerState]:
        return [p for p in self.players.values() if p.alive and not p.death_pending]

    def alive_by_alignment(self, alignment: Alignment) -> List[PlayerState]:
        result = [p for p in self.alive_players() if p.role and p.role.alignment == alignment]
        logger.info(">>> alive_by_alignment | guild=%s alignment=%s count=%s", 
                     self.guild.id, alignment.value, len(result))
        return result

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
        finally:
            # Unmute all players before announcing winner
            await self._force_unmute_all()
            await self._announce_winner()
            self.is_finished = True
            if self._wolf_thread:
                with contextlib.suppress(discord.HTTPException):
                    await self._wolf_thread.delete()
            if self._sisters_thread:
                with contextlib.suppress(discord.HTTPException):
                    await self._sisters_thread.delete()

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
        
        # Mute voice channel for night phase (only in voice mode)
        if self.game_mode == "voice":
            await self._mute_voice()
        
        # Wake Two Sisters on even nights (2, 4, 6...) for coordination
        if self.night_number % 2 == 0 and len(self._sisters_ids) == 2:
            await self._wake_sisters()

        await self._resolve_role_sequence(first_night=self.night_number == 1)
        await self._resolve_pending_deaths("night")
        self.night_number += 1

    async def _run_day(self) -> None:
        self.phase = Phase.DAY
        self.day_number += 1
        
        # Unmute voice channel for day phase (only in voice mode)
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
        await self._run_countdown(self.channel, f"Thảo luận ngày {self.day_number}", self.settings.day_discussion_duration)
        await self._run_day_vote()
        logger.info("Day start | guild=%s channel=%s day=%s deaths=%s", self.guild.id, self.channel.id, self.day_number, [p.user_id for p in new_deaths])

    async def _resolve_pending_deaths(self, phase_label: str) -> None:
        if not self._pending_deaths:
            return
        # Deduplicate by player id while keeping first cause
        unique: Dict[int, str] = {}
        for pid, cause in self._pending_deaths:
            if pid not in unique:
                unique[pid] = cause
        self._pending_deaths.clear()
        for pid, cause in unique.items():
            player = self.players.get(pid)
            if player and player.alive:
                player.alive = False
                player.death_pending = True
                await self._handle_death(player, cause=cause)

    async def _run_day_vote(self) -> None:
        alive = self.alive_players()
        eligible: List[int] = []
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
                scapegoat = self._find_role_holder("Kẻ Thế Thân")
                if scapegoat:
                    await self.channel.send("Lá phiếu bế tắc. Kẻ thế thân phải ra đi thay làng.")
                    scapegoat.alive = False
                    await self._handle_death(scapegoat, cause="scapegoat")
                    logger.info("Scapegoat executed due to tie | guild=%s player=%s", self.guild.id, scapegoat.user_id)
                    return
                await self.channel.send("Dân làng tranh cãi không dứt, chưa ai bị treo cổ.")
                logger.info("Day vote tie no execution | guild=%s day=%s", self.guild.id, self.day_number)
                return
        target_player = self.players.get(top[0][0])
        if not target_player:
            await self.channel.send("Không có kết quả rõ ràng.")
            return
        if target_player.role and target_player.role.metadata.name == "Thằng Ngốc" and not getattr(target_player.role, "revealed", False):
            target_player.role.revealed = True  # type: ignore[attr-defined]
            target_player.vote_disabled = True
            await self.channel.send("Thằng ngốc lộ diện và vẫn sống, nhưng mất quyền bỏ phiếu.")
            logger.info("Idiot revealed survives lynch | guild=%s player=%s", self.guild.id, target_player.user_id)
            return
        await self.channel.send(f"{target_player.display_name()} bị dân làng treo cổ.")
        if target_player.alive:
            target_player.alive = False
            await self._handle_death(target_player, cause="lynch")
            # Resolve any immediate retaliations (e.g., Hunter) during the day
            await self._resolve_pending_deaths("hunter")
            logger.info("Player lynched | guild=%s player=%s", self.guild.id, target_player.display_name())

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
            self.players[player_id].role = role
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
            if player.role:
                await player.role.on_assign(self, player)
        
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

    async def _notify_roles(self) -> None:
        wolf_players = [p for p in self.players.values() if p.role and p.role.alignment == Alignment.WEREWOLF]
        wolf_names = ", ".join(p.display_name() for p in wolf_players) or "Không có"
        for player in self.players.values():
            role = player.role
            if not role:
                continue
            embed = discord.Embed(
                title=f"🃏 Vai của bạn: {role.metadata.name}",
                description=role.format_private_information(),
                colour=discord.Colour.dark_gold(),
            )
            embed.add_field(name="Phe", value=player.faction_view(), inline=True)
            embed.add_field(name="Đồng đội", value=wolf_names if role.alignment == Alignment.WEREWOLF else "Ẩn danh", inline=True)
            embed.set_thumbnail(url=role.metadata.card_image_url)
            try:
                await player.member.send(embed=embed)
            except discord.HTTPException:
                await self.channel.send(f"Không thể gửi DM cho {player.display_name()}. Hãy bật DM để chơi.")

    async def _announce_role_composition(self) -> None:
        """Announce all roles in the game at the start."""
        from collections import Counter
        role_counts = Counter(p.role.metadata.name for p in self.players.values() if p.role)
        
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

    async def _announce_role_action(self, role: Role) -> None:
        """Announce a specific role is taking action."""
        embed = discord.Embed(
            title=f"{role.metadata.name}",
            description="Đang hành động...",
            colour=discord.Colour.purple(),
        )
        embed.set_thumbnail(url=role.metadata.card_image_url)
        await self.channel.send(embed=embed)

    async def _create_wolf_thread(self) -> None:
        wolves = [p for p in self.players.values() if p.role and p.role.alignment == Alignment.WEREWOLF]
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
        """Mute all players in voice channel during night phase."""
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

    async def _unmute_voice(self) -> None:
        """Unmute all players in voice channel during day phase."""
        if not self.voice_channel_id:
            return
        try:
            voice_channel = self.bot.get_channel(self.voice_channel_id)
            if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
                logger.warning("Voice channel not found or invalid | guild=%s channel_id=%s", self.guild.id, self.voice_channel_id)
                return
            
            # Unmute all players currently in the voice channel
            unmuted_count = 0
            for member in voice_channel.members:
                try:
                    await member.edit(mute=False, reason="Werewolf: Day phase - unmute")
                    unmuted_count += 1
                except discord.HTTPException as e:
                    logger.warning("Failed to unmute member | guild=%s member=%s error=%s", 
                                 self.guild.id, member.id, str(e))
            
            logger.info("Voice unmuted | guild=%s voice_channel=%s unmuted_count=%s", 
                       self.guild.id, self.voice_channel_id, unmuted_count)
        except Exception as e:
            logger.error("Failed to unmute voice channel | guild=%s error=%s", self.guild.id, str(e), exc_info=True)

    async def _run_wolf_vote(self) -> Optional[int]:
        wolves = [p for p in self.alive_players() if p.role and p.role.alignment == Alignment.WEREWOLF]
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
        wolves = [p for p in self.alive_players() if p.role and p.role.alignment == Alignment.WEREWOLF]
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
        return max(duration, 30)  # Minimum 30s

    async def _resolve_role_sequence(self, *, first_night: bool) -> None:
        thief = self._find_role_holder("Tên Trộm")
        if first_night and thief:
            await self._announce_role_action(thief.role)
            await self._handle_thief(thief)
            logger.info("Thief resolved | guild=%s player=%s", self.guild.id, thief.user_id)
        cupid = self._find_role_holder("Thần Tình Yêu")
        if first_night and cupid:
            await self._announce_role_action(cupid.role)
            await self._handle_cupid(cupid)
            logger.info("Cupid resolved | guild=%s player=%s", self.guild.id, cupid.user_id)
        
        wolves = [p for p in self.alive_players() if p.role and p.role.alignment == Alignment.WEREWOLF]
        if wolves:
            await self._announce_role_action(wolves[0].role)
        
        # Handle little girl peeking before wolf vote (so wolves can see the discovery message)
        little_girl = self._find_role_holder("Cô Bé")
        if little_girl:
            await self._handle_little_girl(little_girl)
        
        # Run wolf vote - if little girl was discovered, wolves can choose to kill her instead
        target_id = await self._run_wolf_vote()
        logger.info("Wolf vote target | guild=%s night=%s target=%s", self.guild.id, self.night_number, target_id)
        
        # If little girl was discovered, ask wolves quickly if they want to switch kill to her
        if self._little_girl_peeking:
            try:
                # Run a quick yes/no vote in wolf thread
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
        if guard:
            await self._announce_role_action(guard.role)
        protected_id = await self._handle_guard(guard) if guard else None
        logger.info("Guard protected | guild=%s night=%s target=%s", self.guild.id, self.night_number, protected_id)
        killed_id = target_id if target_id != protected_id else None
        if killed_id and self._handle_elder_resistance(killed_id):
            killed_id = None
        
        white_wolf = self._find_role_holder("Sói Trắng")
        if white_wolf and self.night_number % 2 == 0:
            await self._announce_role_action(white_wolf.role)
        betrayer_kill = await self._handle_white_wolf(white_wolf) if white_wolf else None
        
        seer = self._find_role_holder("Tiên Tri")
        if seer:
            await self._announce_role_action(seer.role)
            await self._handle_seer(seer)
        
        witch = self._find_role_holder("Phù Thủy")
        if witch:
            await self._announce_role_action(witch.role)
            killed_id = await self._handle_witch(witch, killed_id)
        
        raven = self._find_role_holder("Con Quạ")
        if raven:
            await self._announce_role_action(raven.role)
            await self._handle_raven(raven)
        
        piper = self._find_role_holder("Thổi Sáo")
        if piper:
            await self._announce_role_action(piper.role)
            await self._handle_piper(piper)
        
        pyro = self._find_role_holder("Kẻ Phóng Hỏa")
        if pyro and not getattr(pyro.role, "ignited", False):
            await self._announce_role_action(pyro.role)
            await self._handle_pyromaniac(pyro)
        
        if killed_id:
            self._pending_deaths.append((killed_id, "wolves"))
        if betrayer_kill:
            self._pending_deaths.append((betrayer_kill, "white_wolf"))
        logger.info("Night resolution | guild=%s night=%s killed=%s extra=%s", self.guild.id, self.night_number, killed_id, betrayer_kill)

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
                               if p.alive and p.role and p.role.alignment == Alignment.WEREWOLF and p.user_id != thief.user_id]
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

    async def _handle_guard(self, guard: PlayerState) -> Optional[int]:
        options = {p.user_id: p.display_name() for p in self.alive_players()}
        choice = await self._prompt_dm_choice(
            guard,
            title="Bảo vệ thức giấc",
            description="Chọn người cần bảo vệ đêm nay.",
            options=options,
            allow_skip=True,
        )
        if choice is None:
            return None
        target_id = choice
        target = self.players.get(target_id)
        if target:
            if target_id == guard.user_id and not guard.role.can_self_target():
                await guard.member.send("Bạn không thể tiếp tục tự bảo vệ.")
                return None
            last_target = getattr(guard.role, "last_protected", None)
            if last_target == target_id:
                await guard.member.send("Bạn không thể bảo vệ cùng một người hai đêm liên tiếp.")
                return None
            target.protected_last_night = True
            if target_id == guard.user_id:
                guard.role.mark_self_target()
                await guard.member.send("Bạn đã chọn bảo vệ chính mình đêm nay. Bạn sẽ không thể tự bảo vệ nữa.")
            guard.role.last_protected = target_id
            logger.info("Guard protected | guild=%s player=%s target=%s", self.guild.id, guard.user_id, target_id)
        return target_id

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
        
        faction = target.role.alignment
        message = "Người đó thuộc phe Dân Làng." if faction == Alignment.VILLAGE else "Người đó thuộc phe Ma Sói." if faction == Alignment.WEREWOLF else "Người đó thuộc phe Trung Lập."
        
        logger.info("Seer peek | guild=%s seer=%s target=%s faction=%s night=%s", 
                    self.guild.id, seer.user_id, target_id, faction.value, self.night_number)
        
        try:
            await seer.member.send(message)
        except discord.HTTPException:
            pass
        logger.info("Seer peek | guild=%s seer=%s target=%s faction=%s", self.guild.id, seer.user_id, target_id, faction)

    async def _handle_witch(self, witch: PlayerState, killed_id: Optional[int]) -> Optional[int]:
        role = witch.role
        heal_available = getattr(role, "heal_available", True)
        kill_available = getattr(role, "kill_available", True)
        saved = False
        
        logger.info("Witch action start | guild=%s witch=%s night=%s heal_available=%s kill_available=%s killed_id=%s", 
                    self.guild.id, witch.user_id, self.night_number, heal_available, kill_available, killed_id)
        
        if killed_id and heal_available:
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
            options = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != witch.user_id}
            choice = await self._prompt_dm_choice(
                witch,
                title="Phù thủy",
                description="Bạn muốn sử dụng bình độc?",
                options=options,
                allow_skip=True,
            )
            if choice is not None and choice in options:
                if choice == witch.user_id and not witch.role.can_self_target():
                    logger.info("Witch tried self-target without permission | guild=%s witch=%s", 
                                self.guild.id, witch.user_id)
                    return None if saved else killed_id
                kill_target = choice
                role.kill_available = False  # type: ignore[attr-defined]
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
        
        wolves = [p for p in self.alive_players() if p.role and p.role.alignment == Alignment.WEREWOLF]
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
        options = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != white_wolf.user_id and p.role and p.role.alignment == Alignment.WEREWOLF}
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

    def _handle_elder_resistance(self, target_id: int) -> bool:
        target = self.players.get(target_id)
        if not target or not target.role or target.role.metadata.name != "Già Làng":
            return False
        remaining = getattr(target.role, "wolf_hits", 0)
        if remaining >= 1:
            return False
        target.role.wolf_hits = remaining + 1  # type: ignore[attr-defined]

        async def notify() -> None:
            with contextlib.suppress(discord.HTTPException):
                await target.member.send("Bạn bị ma sói tấn công nhưng vẫn sống.")

        asyncio.create_task(notify())
        logger.info("Elder resisted wolf attack | guild=%s elder=%s", self.guild.id, target.user_id)
        return True

    def _find_role_holder(self, role_name: str) -> Optional[PlayerState]:
        for player in self.players.values():
            if player.alive and player.role and player.role.metadata.name == role_name:
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
        timeout: int = 60,
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
            logger.info(">>> Player status | guild=%s player=%s alive=%s death_pending=%s role=%s alignment=%s",
                        self.guild.id, player.user_id, player.alive, player.death_pending, 
                        player.role.metadata.name if player.role else None,
                        player.role.alignment.value if player.role else None)
        
        if not wolves and villagers:
            self._winner = Alignment.VILLAGE
            logger.info("Win condition met: Village wins | guild=%s (no wolves left)", self.guild.id)
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
            description=f"**Phe Chiến Thắng:** {faction_name}",
            colour=faction_colour,
        )
        embed.add_field(name="Người Sống Sót", value=survivors, inline=False)
        
        # Add death summary for each phase in order
        for phase, deaths in deaths_by_phase.items():
            if deaths:
                embed.add_field(name=phase, value="; ".join(deaths), inline=False)
        embed.set_image(url=CARD_BACK_URL)
        await self.channel.send(embed=embed)

    async def _handle_death(self, player: PlayerState, *, cause: str) -> None:
        # Record death for end-of-game summary with phase label and number
        if self.phase == Phase.NIGHT:
            phase_label = f"Đêm {self.night_number}"
        else:
            phase_label = f"Ngày {self.day_number}"
        self._death_log.append((player.user_id, cause, phase_label))
        await player.role.on_death(self, player, cause)  # type: ignore[union-attr]
        if player.lover_id:
            lover = self.players.get(player.lover_id)
            if lover and lover.alive:
                lover.alive = False
                lover.death_pending = True
                await self._handle_death(lover, cause="lover")
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
