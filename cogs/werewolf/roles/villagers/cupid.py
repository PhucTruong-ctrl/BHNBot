"""Cupid role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Cupid(Role):
    metadata = RoleMetadata(
        name="Thần Tình Yêu",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Đêm đầu tiên, bạn chọn hai người trở thành tình nhân. Nếu một người chết, người kia cũng ra đi.",
        first_night_only=True,
        night_order=20,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/cupid.png",
    )
