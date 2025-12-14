"""Villager role definition."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Villager(Role):
    metadata = RoleMetadata(
        name="Dân Làng",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Bạn là dân làng bình thường. Nhiệm vụ duy nhất là tìm ra Ma Sói và sống sót.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/village.png",
    )
