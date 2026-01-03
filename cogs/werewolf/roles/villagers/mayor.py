"""Mayor role (The Captain)."""

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
class Mayor(Role):
    metadata = RoleMetadata(
        name="Trưởng Làng",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Lá phiếu của bạn được tính gấp đôi. Khi hòa phiếu, bạn quyết định. Khi chết, bạn chỉ định người kế nhiệm.",
        card_image_url="https://via.placeholder.com/250x350?text=Mayor",
    )

    async def on_assign(self, game: WerewolfGame, player: PlayerState) -> None:  # type: ignore[override]
        logger.info("Mayor role assigned | guild=%s mayor=%s", game.guild.id, player.user_id)
        player.mayor = True
        player.vote_weight = 2
    
    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Captain dies, they pass the role to someone else."""
        logger.info("Mayor on_death triggered | guild=%s mayor=%s cause=%s", game.guild.id, player.user_id, cause)
        alive = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not alive:
            logger.warning("No alive players to pass mayor role | guild=%s mayor=%s", game.guild.id, player.user_id)
            return
        
        options = {p.user_id: p.display_name() for p in alive}
        logger.info("Mayor requesting successor | guild=%s mayor=%s", game.guild.id, player.user_id)
        choice = await game._prompt_dm_choice(
            player,
            title="Trưởng Làng - Chọn người kế nhiệm",
            description="Bạn sắp chết. Hãy chọn người kế nhiệm chức Trưởng Làng.",
            options=options,
            allow_skip=False,
            timeout=30,
        )
        
        if choice and choice in options:
            successor = game.players.get(choice)
            logger.info("Mayor passing role to successor | guild=%s mayor=%s successor=%s", game.guild.id, player.user_id, choice)
            if successor and successor.alive:
                # Remove captain status from dying player
                player.mayor = False
                player.vote_weight = 1
                
                # Transfer to successor
                successor.mayor = True
                successor.vote_weight = 2
                
                try:
                    await successor.member.send(f"Bạn đã được {player.display_name()} chỉ định làm Trưởng Làng kế nhiệm! Phiếu bạn tính x2 và bạn phá vỡ hòa phiếu.")
                    await game.channel.send(f"{successor.display_name()} đã trở thành Trưởng Làng mới!")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
