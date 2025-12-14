"""Raven role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Raven(Role):
    metadata = RoleMetadata(
        name="Con Quạ",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi đêm bạn nguyền rủa một người, khiến họ mặc nhiên chịu thêm hai phiếu treo cổ vào sáng hôm sau.",
        night_order=130,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/raven.png",
    )
