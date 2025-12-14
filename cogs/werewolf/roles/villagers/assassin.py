"""Assassin role - acts silently every other day when receiving 4+ votes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")


@register_role
class Assassin(Role):
    metadata = RoleMetadata(
        name="Thích Khách",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi ngày khi bạn nhận được ít nhất 4 phiếu bỏ phiếu, bạn có thể lặng lẽ chọn 1 người để giết vào buổi tối (hành động riêng, không announce).",
        night_order=10,  # Early night - execute silently before other roles
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/assassin.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.votes_day1 = 0  # Votes received on first day of cycle
        self.votes_day2 = 0  # Votes received on second day of cycle
        self.can_act_this_night = False

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Assassin silently acts if they received 4+ votes over 2 days."""
        total_votes = self.votes_day1 + self.votes_day2
        logger.info(
            "Assassin on_night start | guild=%s assassin=%s night=%s votes_day1=%s votes_day2=%s total=%s can_act=%s",
            game.guild.id, player.user_id, night_number, self.votes_day1, self.votes_day2, total_votes, self.can_act_this_night
        )

        # Only act if we can and have enough votes
        if not self.can_act_this_night or total_votes < 4:
            logger.info(
                "Assassin cannot act | guild=%s assassin=%s night=%s can_act=%s total_votes=%s",
                game.guild.id, player.user_id, night_number, self.can_act_this_night, total_votes
            )
            return

        # Get alive targets (everyone except self)
        targets = {
            p.user_id: p.display_name()
            for p in game.alive_players()
            if p.user_id != player.user_id
        }

        if not targets:
            logger.warning("No valid targets for Assassin | guild=%s assassin=%s", game.guild.id, player.user_id)
            return

        logger.info(
            "Assassin asking for target | guild=%s assassin=%s night=%s targets=%s",
            game.guild.id, player.user_id, night_number, list(targets.keys())
        )

        # Silent action - DM directly without announcement
        target_id = await game._prompt_dm_choice(
            player.member,
            title="🗡️ Thích Khách - Chọn Mục Tiêu",
            description=f"Bạn nhận được {total_votes} phiếu trong 2 ngày. Chọn 1 người để lặng lẽ tiêu diệt.",
            options=targets,
            allow_skip=False,
            timeout=120,
        )

        if target_id and target_id in targets:
            # Silently execute the target
            game._pending_deaths.append((target_id, "assassin"))
            logger.info(
                "Assassin executed target | guild=%s assassin=%s target=%s night=%s",
                game.guild.id, player.user_id, target_id, night_number
            )

            # Notify Assassin (silent, no public announcement)
            await game._safe_send_dm(
                player.member,
                content=f"💀 Bạn đã lặng lẽ tiêu diệt {game.players[target_id].display_name()}."
            )

        # Reset for next 2-day cycle
        self.can_act_this_night = False
        self.votes_day1 = 0
        self.votes_day2 = 0
        logger.info(
            "Assassin action complete | guild=%s assassin=%s night=%s",
            game.guild.id, player.user_id, night_number
        )
