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
        night_order=50,
    )
