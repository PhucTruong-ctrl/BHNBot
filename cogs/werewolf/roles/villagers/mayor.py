"""Mayor role (The Captain)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState


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
        player.mayor = True
        player.vote_weight = 2
    
    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Captain dies, they pass the role to someone else."""
        alive = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not alive:
            return
        
        options = {p.user_id: p.display_name() for p in alive}
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
                except:
                    pass
