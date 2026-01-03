"""Seer role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Seer(Role):
    metadata = RoleMetadata(
        name="Tiên Tri",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Mỗi đêm bạn có thể soi danh tính của một người chơi.",
        night_order=20,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/seer.png",
    )
