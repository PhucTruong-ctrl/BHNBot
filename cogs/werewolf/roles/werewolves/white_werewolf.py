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
        card_image_url="https://via.placeholder.com/250x350?text=WhiteWolf",
        tags=("self_target",),
    )
