"""Standard werewolf role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Werewolf(Role):
    metadata = RoleMetadata(
        name="Ma Sói",
        alignment=Alignment.WEREWOLF,
        expansion=Expansion.BASIC,
        description="Bạn là Ma Sói. Mỗi đêm hãy phối hợp cùng đồng bọn để chọn con mồi.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/werewolf/wolf.png",
        tags=("self_target",),
    )
