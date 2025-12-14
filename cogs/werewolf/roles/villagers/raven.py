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
        card_image_url="https://via.placeholder.com/250x350?text=Raven",
    )
