"""Scapegoat role."""

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
class Scapegoat(Role):
    metadata = RoleMetadata(
        name="Oan Nhân",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.NEW_MOON,
        description="Nếu buổi sáng bị hòa phiếu, bạn sẽ chết ngay lập tức. Sau đó bạn chọn 1 người sẽ bị treo vào ngày hôm sau.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/scapegoat.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.target_for_next_day: int | None = None

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Scapegoat dies from tie, choose who to lynch tomorrow."""
        logger.info("Scapegoat on_death triggered | guild=%s scapegoat=%s cause=%s alive=%s", game.guild.id, player.user_id, cause, player.alive)
        if cause != "tie":
            logger.debug("Scapegoat died not from tie | guild=%s scapegoat=%s cause=%s", game.guild.id, player.user_id, cause)
            return
        
        # Scapegoat chooses who will be lynched tomorrow
        choices = {p.user_id: p.display_name() for p in game.alive_players() if p.user_id != player.user_id}
        if not choices:
            logger.warning("No valid targets for Scapegoat selection | guild=%s scapegoat=%s", game.guild.id, player.user_id)
            return
        
        # CRITICAL FIX: Verify alive before prompting dead player
        if not player.alive:
            logger.warning("Scapegoat is dead, skipping selection prompt | guild=%s scapegoat=%s", game.guild.id, player.user_id)
            return
        
        logger.info("Scapegoat requesting next day lynch target | guild=%s scapegoat=%s", game.guild.id, player.user_id)
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Oan Nhân - Chọn Nạn Nhân",
            description="Người sẽ bị treo cổ vào ngày hôm sau là ai?",
            options=choices,
            allow_skip=False,
        )
        if target_id and target_id in choices:
            self.target_for_next_day = target_id
            game._scapegoat_target = target_id  # pylint: disable=protected-access
            logger.info("Scapegoat selected next day lynch target | guild=%s scapegoat=%s target=%s", game.guild.id, player.user_id, target_id)
            await player.member.send(f"Bạn đã chọn {game.players[target_id].display_name()} sẽ bị treo ngày hôm sau.")
        else:
            logger.info("Scapegoat skipped selection | guild=%s scapegoat=%s", game.guild.id, player.user_id)
