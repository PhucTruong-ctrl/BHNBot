"""Two Sisters role."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState


@register_role
class TwoSisters(Role):
    metadata = RoleMetadata(
        name="Hai Chị Em",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Bạn biết chị/em của mình từ đêm đầu. Mỗi đêm chẵn, bạn sẽ thức dậy và có thể bàn luận cùng nhau.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/twosister.png",
    )

    async def on_assign(self, game: WerewolfGame, player: PlayerState) -> None:  # type: ignore[override]
        """Mark player as a sister; notification sent after both are assigned."""
        player.is_sister = True  # type: ignore[attr-defined]
