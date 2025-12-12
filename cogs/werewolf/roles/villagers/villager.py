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
    )
