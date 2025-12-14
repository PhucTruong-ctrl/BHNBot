"""White werewolf role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class WhiteWerewolf(Role):
    metadata = RoleMetadata(
        name="Sói Trắng",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.THE_VILLAGE,
        description="Cứ hai đêm một lần, bạn có thể giết một Ma Sói khác để trở thành kẻ sống sót cuối cùng.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/werewolf/white-wolf.png",
        tags=("self_target",),
    )
