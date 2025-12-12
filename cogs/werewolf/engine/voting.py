"""Generic voting helpers for Werewolf phases."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import discord


@dataclass(slots=True)
class VoteResult:
    """Outcome of a voting session."""

    winning_target_id: Optional[int]
    tally: Counter
    is_tie: bool


class VoteSession:
    """Handle a generic vote using a Discord view with a select menu."""

    def __init__(
        self,
        bot: discord.Client,
        channel: discord.abc.Messageable,
        *,
        title: str,
        description: str,
        options: Dict[int, str],
        eligible_voters: Iterable[int],
        duration: int,
        allow_skip: bool = True,
        vote_weights: Optional[Dict[int, int]] = None,
    ) -> None:
        self.bot = bot
        self.channel = channel
        self.title = title
        self.description = description
        self.options = options
        self.eligible_voters = set(eligible_voters)
        self.duration = duration
        self.allow_skip = allow_skip

        self._votes: Dict[int, Optional[int]] = {voter: None for voter in self.eligible_voters}
        self.vote_weights = vote_weights or {}
        self._message: Optional[discord.Message] = None
        self._finished = asyncio.Event()
        self._timeout_task: Optional[asyncio.Task] = None

    async def start(self) -> VoteResult:
        """Start the vote and wait for the result."""

        view = _VoteView(self)
        embed = self._build_embed()
        self._message = await self.channel.send(embed=embed, view=view)
        self._timeout_task = asyncio.create_task(self._auto_finish())
        await self._finished.wait()
        if self._timeout_task:
            self._timeout_task.cancel()
        view.stop()
        if self._message:
            try:
                await self._message.edit(view=None)
            except discord.HTTPException:
                pass
        return self._compute_result()

    async def _auto_finish(self) -> None:
        try:
            await asyncio.sleep(self.duration)
        except asyncio.CancelledError:
            return
        self.end()

    def end(self) -> None:
        if not self._finished.is_set():
            self._finished.set()

    async def handle_vote(self, voter_id: int, target_id: Optional[int]) -> None:
        if voter_id not in self._votes:
            return
        self._votes[voter_id] = target_id
        await self._refresh_message()
        if all(choice is not None for choice in self._votes.values()):
            self.end()

    async def _refresh_message(self) -> None:
        if not self._message:
            return
        embed = self._build_embed()
        try:
            await self._message.edit(embed=embed)
        except discord.HTTPException:
            pass

    def _build_embed(self) -> discord.Embed:
        embed = discord.Embed(title=self.title, description=self.description)
        embed.colour = discord.Colour.dark_teal()
        counts: Counter[int] = Counter()
        for voter, target in self._votes.items():
            if target is None:
                continue
            weight = self.vote_weights.get(voter, 1)
            counts[target] += weight
        total = sum(counts.values())
        details = []
        for target_id, label in self.options.items():
            vote_count = counts.get(target_id, 0)
            details.append(f"{label}: {vote_count} phiếu")
        if self.allow_skip:
            skipped = len([v for v in self._votes.values() if v is None])
            details.append(f"Bỏ phiếu: {skipped} chưa chọn")
        embed.add_field(name="Kết quả tạm thời", value="\n".join(details) or "Chưa có phiếu", inline=False)
        embed.set_footer(text=f"Số phiếu đã ghi nhận: {total}/{len(self._votes)}")
        return embed

    def _compute_result(self) -> VoteResult:
        counts: Counter[int] = Counter()
        for voter, target in self._votes.items():
            if target is None:
                continue
            weight = self.vote_weights.get(voter, 1)
            counts[target] += weight
        if not counts:
            return VoteResult(winning_target_id=None, tally=counts, is_tie=True)
        top = counts.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            return VoteResult(winning_target_id=None, tally=counts, is_tie=True)
        return VoteResult(winning_target_id=top[0][0], tally=counts, is_tie=False)


class _VoteView(discord.ui.View):
    def __init__(self, session: VoteSession) -> None:
        super().__init__(timeout=session.duration)
        self.session = session
        options = [discord.SelectOption(label=label, value=str(target_id)) for target_id, label in session.options.items()]
        if session.allow_skip:
            options.append(discord.SelectOption(label="Bỏ phiếu", value="skip"))
        self.add_item(_VoteSelect(options, session))

    async def on_timeout(self) -> None:
        self.session.end()


class _VoteSelect(discord.ui.Select):
    def __init__(self, options: Iterable[discord.SelectOption], session: VoteSession) -> None:
        super().__init__(placeholder="Chọn mục tiêu", min_values=1, max_values=1, options=list(options))
        self.session = session

    async def callback(self, interaction: discord.Interaction) -> None:
        voter_id = interaction.user.id
        if voter_id not in self.session.eligible_voters:
            await interaction.response.send_message("Bạn không được tham gia bỏ phiếu này.", ephemeral=True)
            return
        choice = self.values[0]
        target_id: Optional[int]
        if choice == "skip":
            target_id = None
        else:
            target_id = int(choice)
        await self.session.handle_vote(voter_id, target_id)
        await interaction.response.send_message("Ghi nhận lựa chọn của bạn.", ephemeral=True)
