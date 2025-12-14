"""Mayor role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Mayor(Role):
    metadata = RoleMetadata(
        name="Trưởng Làng",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Lá phiếu của bạn được tính gấp đôi khi treo cổ.",
        card_image_url="https://via.placeholder.com/250x350?text=Mayor",
    )

    async def on_assign(self, game, player) -> None:  # type: ignore[override]
        player.mayor = True
        player.vote_weight = 2
