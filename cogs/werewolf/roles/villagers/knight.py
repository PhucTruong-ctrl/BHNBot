"""Knight role with lightning sword."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState


@register_role
class Knight(Role):
    metadata = RoleMetadata(
        name="Hiệp Sĩ",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Khi bị Ma Sói cắn chết, chiếc kiếm rĩ sét của bạn sẽ giết chết Ma Sói gần nhất (bên trái đầu tiên).",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/knightWithRusticSword.png",
    )

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Knight is killed by wolves, the nearest wolf dies next night."""
        if cause != "killed":
            return
        
        # Find all alive werewolves
        wolves = [p for p in game.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        
        if not wolves:
            return
        
        # Mark the first wolf (leftmost) to die next night
        target_wolf = wolves[0]
        target_wolf.death_pending = True
        
        # Notify the wolf that they will die
        await target_wolf.member.send(
            f"⚡ Thanh kiếm rĩ sét của {player.display_name()} đã đánh bạn! Bạn sẽ chết vào sáng mai."
        )
