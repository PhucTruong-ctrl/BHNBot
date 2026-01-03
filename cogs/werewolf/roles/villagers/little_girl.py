"""Little girl role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class LittleGirl(Role):
    metadata = RoleMetadata(
        name="Cô Bé",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Từ đêm thứ 2, bạn có thể hé mắt nhìn khi ma sói thức giấc (20% bị phát hiện). Nếu bị phát hiện, sói có thể chọn giết bạn thay thế.",
        night_order=30,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/little-girl.png",
    )
