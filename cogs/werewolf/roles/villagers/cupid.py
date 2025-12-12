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
        night_order=10,
    )
