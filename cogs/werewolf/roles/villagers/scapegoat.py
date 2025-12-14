"""Scapegoat role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Scapegoat(Role):
    metadata = RoleMetadata(
        name="Kẻ Thế Thân",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.NEW_MOON,
        description="Nếu dân làng hòa phiếu, bạn sẽ bị xử tử thay. Bạn có thể quyết định ai được bỏ phiếu vào sáng hôm sau.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/scaperoat.png",
    )
