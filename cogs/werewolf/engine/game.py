"""Core orchestration for The Werewolves of Miller's Hollow implementation."""

from __future__ import annotations

import asyncio
import contextlib
import random
from collections import Counter
from typing import Dict, List, Optional, Sequence, Set

import discord
from discord import abc as discord_abc

from ..roles import get_role_class, load_all_roles
from ..roles.base import Alignment, Expansion, Role
from .state import GameSettings, Phase, PlayerState
from .voting import VoteSession

CARD_BACK_URL = "https://upload.wikimedia.org/wikipedia/vi/5/59/Ma_soi_Werewolves.png"
MIN_PLAYERS = 6

load_all_roles()


class WerewolfGame:
    """Single running match of Werewolf."""

    def __init__(
        self,
        bot: discord.Client,
        guild: discord.Guild,
        channel: discord.TextChannel,
        host: discord.Member,
        expansions: Set[Expansion],
    ) -> None:
        self.bot = bot
        self.guild = guild
        self.channel = channel
        self.host = host
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
        self._pending_deaths: List[int] = []
        self._lovers: Set[int] = set()
        self._charmed: Set[int] = set()
        self._piper_id: Optional[int] = None
        self._stop_event = asyncio.Event()

    async def open_lobby(self) -> None:
        self._lobby_view = _LobbyView(self)
        embed = self._build_lobby_embed()
        self._lobby_message = await self.channel.send(embed=embed, view=self._lobby_view)

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
        return [p for p in self.alive_players() if p.role and p.role.alignment == alignment]

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

    async def remove_player(self, member: discord_abc.User) -> None:
        if self.phase != Phase.LOBBY:
            raise RuntimeError("Không thể rời bàn sau khi trận đấu đã bắt đầu")
        guild_member = member if isinstance(member, discord.Member) else self.guild.get_member(member.id)
        if guild_member is None:
            return
        self.players.pop(guild_member.id, None)
        await self._refresh_lobby()

    async def toggle_expansion(self, expansion: Expansion) -> None:
        if self.phase != Phase.LOBBY:
            return
        if expansion in self.settings.expansions:
            self.settings.expansions.remove(expansion)
        else:
            self.settings.expansions.add(expansion)
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
        if self._lobby_message:
            try:
                await self._lobby_message.edit(content="Trận đấu đã bắt đầu", view=None)
            except discord.HTTPException:
                pass
        self._loop_task = asyncio.create_task(self._game_loop())

    async def _game_loop(self) -> None:
        try:
            while not self.is_finished and not self._stop_event.is_set():
                await self._run_night()
                if self._check_win_condition():
                    break
                await self._run_day()
                if self._check_win_condition():
                    break
        finally:
            await self._announce_winner()
            self.is_finished = True
            if self._wolf_thread:
                with contextlib.suppress(discord.HTTPException):
                    await self._wolf_thread.delete()

    async def _run_night(self) -> None:
        self.phase = Phase.NIGHT
        for player in self.alive_players():
            player.reset_night_flags()
        await self.channel.send(f"Đêm {self.night_number} buông xuống. Tất cả đi ngủ.")

        await self._resolve_role_sequence(first_night=self.night_number == 1)
        await self._resolve_pending_deaths("night")
        self.night_number += 1

    async def _run_day(self) -> None:
        self.phase = Phase.DAY
        self.day_number += 1
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
        await self._run_day_vote()

    async def _resolve_pending_deaths(self, phase_label: str) -> None:
        if not self._pending_deaths:
            return
        unique = {pid for pid in self._pending_deaths}
        self._pending_deaths.clear()
        for pid in unique:
            player = self.players.get(pid)
            if player and player.alive:
                player.alive = False
                player.death_pending = True
                await self._handle_death(player, cause=phase_label)

    async def _run_day_vote(self) -> None:
        alive = self.alive_players()
        if len(alive) <= 2:
            await self.channel.send("Không đủ người sống để bỏ phiếu ban ngày.")
            return
        eligible = [p.user_id for p in alive if not p.vote_disabled]
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
        for player in alive:
            if player.marked_by_raven:
                tally[player.user_id] += 2
        if not tally:
            await self.channel.send("Không có ai bị trưng cầu đủ phiếu.")
            return
        top = tally.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            scapegoat = self._find_role_holder("Kẻ Thế Thân")
            if scapegoat:
                await self.channel.send("Lá phiếu bế tắc. Kẻ thế thân phải ra đi thay làng.")
                scapegoat.alive = False
                await self._handle_death(scapegoat, cause="scapegoat")
                return
            await self.channel.send("Dân làng tranh cãi không dứt, chưa ai bị treo cổ.")
            return
        target_player = self.players.get(top[0][0])
        if not target_player:
            await self.channel.send("Không có kết quả rõ ràng.")
            return
        if target_player.role and target_player.role.metadata.name == "Thằng Ngốc" and not getattr(target_player.role, "revealed", False):
            target_player.role.revealed = True  # type: ignore[attr-defined]
            target_player.vote_disabled = True
            await self.channel.send("Thằng ngốc lộ diện và vẫn sống, nhưng mất quyền bỏ phiếu.")
            return
        await self.channel.send(f"{target_player.display_name()} bị dân làng treo cổ.")
        if target_player.alive:
            target_player.alive = False
            await self._handle_death(target_player, cause="lynch")

    async def _assign_roles(self) -> None:
        player_ids = list(self.players.keys())
        random.shuffle(player_ids)
        role_layout = self._build_role_layout(len(player_ids))
        random.shuffle(role_layout)
        extra_cards: List[Role] = []
        thief_id: Optional[int] = None
        for player_id, role_cls in zip(player_ids, role_layout):
            role = role_cls()
            if role.metadata.name == "Tên Trộm":
                thief_id = player_id
            self.players[player_id].role = role
        if thief_id is not None:
            thief = self.players[thief_id]
            extra_cards = self._generate_thief_cards()
            thief.role.extra_cards = extra_cards  # type: ignore[attr-defined]
        for player in self.players.values():
            if player.role:
                await player.role.on_assign(self, player)

    async def _notify_roles(self) -> None:
        wolf_players = [p for p in self.players.values() if p.role and p.role.alignment == Alignment.WEREWOLF]
        wolf_names = ", ".join(p.display_name() for p in wolf_players) or "Không có"
        for player in self.players.values():
            role = player.role
            if not role:
                continue
            embed = discord.Embed(title="Bạn được giao vai trò", description=role.format_private_information())
            embed.colour = discord.Colour.dark_gold()
            embed.add_field(name="Phe", value=player.faction_view())
            embed.add_field(name="Đồng đội", value=wolf_names if role.alignment == Alignment.WEREWOLF else "Ẩn danh")
            try:
                await player.member.send(embed=embed)
            except discord.HTTPException:
                await self.channel.send(f"Không thể gửi DM cho {player.display_name()}. Hãy bật DM để chơi.")

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

    async def _resolve_role_sequence(self, *, first_night: bool) -> None:
        thief = self._find_role_holder("Tên Trộm")
        if first_night and thief:
            await self._handle_thief(thief)
        cupid = self._find_role_holder("Thần Tình Yêu")
        if first_night and cupid:
            await self._handle_cupid(cupid)
        little_girl = self._find_role_holder("Cô Bé")
        target_id = await self._run_wolf_vote()
        if little_girl:
            await self._handle_little_girl(little_girl)
        guard = self._find_role_holder("Bảo Vệ")
        protected_id = await self._handle_guard(guard) if guard else None
        killed_id = target_id if target_id != protected_id else None
        if killed_id and self._handle_elder_resistance(killed_id):
            killed_id = None
        white_wolf = self._find_role_holder("Sói Trắng")
        betrayer_kill = await self._handle_white_wolf(white_wolf) if white_wolf else None
        seer = self._find_role_holder("Tiên Tri")
        if seer:
            await self._handle_seer(seer)
        witch = self._find_role_holder("Phù Thủy")
        if witch:
            killed_id = await self._handle_witch(witch, killed_id)
        raven = self._find_role_holder("Con Quạ")
        if raven:
            await self._handle_raven(raven)
        piper = self._find_role_holder("Thổi Sáo")
        if piper:
            await self._handle_piper(piper)
        pyro = self._find_role_holder("Kẻ Phóng Hỏa")
        if pyro:
            await self._handle_pyromaniac(pyro)
        if killed_id:
            self._pending_deaths.append(killed_id)
        if betrayer_kill:
            self._pending_deaths.append(betrayer_kill)

    async def _handle_thief(self, thief: PlayerState) -> None:
        role = thief.role
        extra_cards = getattr(role, "extra_cards", [])
        if not extra_cards:
            return
        options = {idx: card.metadata.name for idx, card in enumerate(extra_cards)}
        result = await self._prompt_dm_choice(
            thief,
            title="Tên trộm chọn vai mới",
            description="Chọn một trong hai lá bài bỏ dư.",
            options=options,
            allow_skip=False,
        )
        if result is None:
            return
        new_role = extra_cards[result]
        thief.role = new_role
        await new_role.on_assign(self, thief)
        try:
            await thief.member.send(f"Bạn đã chọn '{new_role.metadata.name}'.")
        except discord.HTTPException:
            pass

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
        return target_id

    async def _handle_seer(self, seer: PlayerState) -> None:
        options = {p.user_id: p.display_name() for p in self.alive_players() if p.user_id != seer.user_id}
        if not options:
            return
        choice = await self._prompt_dm_choice(
            seer,
            title="Tiên tri soi",
            description="Chọn một người để soi đêm nay.",
            options=options,
            allow_skip=True,
        )
        if choice is None:
            return
        target_id = choice
        target = self.players.get(target_id)
        if not target or not target.role:
            return
        faction = target.role.alignment
        message = "Người đó thuộc phe Dân Làng." if faction == Alignment.VILLAGE else "Người đó thuộc phe Ma Sói." if faction == Alignment.WEREWOLF else "Người đó thuộc phe Trung Lập."
        try:
            await seer.member.send(message)
        except discord.HTTPException:
            pass

    async def _handle_witch(self, witch: PlayerState, killed_id: Optional[int]) -> Optional[int]:
        role = witch.role
        heal_available = getattr(role, "heal_available", True)
        kill_available = getattr(role, "kill_available", True)
        saved = False
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
                    return None if saved else killed_id
                kill_target = choice
                role.kill_available = False  # type: ignore[attr-defined]
                if kill_target == witch.user_id:
                    witch.role.mark_self_target()
                    await witch.member.send("Bạn đã tự kết liễu chính mình.")
        if kill_target:
            self._pending_deaths.append(kill_target)
        return None if saved else killed_id

    async def _handle_little_girl(self, little: PlayerState) -> None:
        wolves = [p.display_name() for p in self.alive_players() if p.role and p.role.alignment == Alignment.WEREWOLF]
        if not wolves:
            return
        message = "Bạn hé mắt và thấy: " + ", ".join(wolves)
        with contextlib.suppress(discord.HTTPException):
            await little.member.send(message)

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
        self._pending_deaths.append(choice)

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
        return True

    def _find_role_holder(self, role_name: str) -> Optional[PlayerState]:
        for player in self.players.values():
            if player.alive and player.role and player.role.metadata.name == role_name:
                return player
        return None

    def _build_role_layout(self, player_count: int) -> List[type[Role]]:
        layout: List[type[Role]] = []
        wolves = max(1, player_count // 4)
        wolf_cls = get_role_class("Ma Sói")
        for _ in range(wolves):
            layout.append(wolf_cls)
        essentials = [
            "Tiên Tri",
            "Phù Thủy",
            "Thợ Săn",
            "Thần Tình Yêu",
        ]
        optional = ["Cô Bé", "Tên Trộm", "Trưởng Làng"]
        for name in essentials:
            cls = get_role_class(name)
            layout.append(cls)
        for name in optional:
            if len(layout) < player_count:
                layout.append(get_role_class(name))
        if Expansion.NEW_MOON in self.settings.expansions:
            for name in ["Thằng Ngốc", "Già Làng", "Kẻ Thế Thân", "Bảo Vệ", "Thổi Sáo"]:
                if len(layout) < player_count:
                    layout.append(get_role_class(name))
        if Expansion.THE_VILLAGE in self.settings.expansions:
            for name in ["Sói Trắng", "Con Quạ", "Kẻ Phóng Hỏa"]:
                if len(layout) < player_count:
                    layout.append(get_role_class(name))
        villager_cls = get_role_class("Dân Làng")
        while len(layout) < player_count:
            layout.append(villager_cls)
        return layout[:player_count]

    def _generate_thief_cards(self) -> List[Role]:
        villager_cls = get_role_class("Dân Làng")
        wolf_cls = get_role_class("Ma Sói")
        return [villager_cls(), wolf_cls()]

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
        villagers = self.alive_by_alignment(Alignment.VILLAGE)
        wolves = self.alive_by_alignment(Alignment.WEREWOLF)
        neutrals = self.alive_by_alignment(Alignment.NEUTRAL)
        if not wolves and villagers:
            self._winner = Alignment.VILLAGE
            return True
        if not villagers and wolves:
            self._winner = Alignment.WEREWOLF
            return True
        if len(self._lovers) == 2:
            alive_lovers = [pid for pid in self._lovers if self.players.get(pid, None) and self.players[pid].alive]
            if len(alive_lovers) == 2 and len(self.alive_players()) == 2:
                self._winner = Alignment.NEUTRAL
                return True
        if self._piper_id:
            piper = self.players.get(self._piper_id)
            if piper and piper.alive:
                others = {p.user_id for p in self.alive_players() if p.user_id != piper.user_id}
                if not others or others.issubset(self._charmed):
                    self._winner = Alignment.NEUTRAL
                    return True
        return False

    async def _announce_winner(self) -> None:
        if self._winner is None:
            await self.channel.send("Trận đấu kết thúc mà không xác định được phe thắng.")
            return
        mapping = {
            Alignment.VILLAGE: "Dân làng",
            Alignment.WEREWOLF: "Ma Sói",
            Alignment.NEUTRAL: "Tình nhân",
        }
        await self.channel.send(f"Trò chơi kết thúc. Phe chiến thắng: {mapping[self._winner]}.")

    async def _handle_death(self, player: PlayerState, *, cause: str) -> None:
        await player.role.on_death(self, player, cause)  # type: ignore[union-attr]
        if player.lover_id:
            lover = self.players.get(player.lover_id)
            if lover and lover.alive:
                lover.alive = False
                lover.death_pending = True
                await self._handle_death(lover, cause="lover")


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
            await self.game.start()
        except Exception as exc:  # pylint: disable=broad-except
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message("Đã bắt đầu trận đấu.", ephemeral=True)


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
