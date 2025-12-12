"""Witch role implementation."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Witch(Role):
    metadata = RoleMetadata(
        name="Phù Thủy",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Bạn sở hữu hai bình thuốc: một cứu sống và một giết người. Mỗi bình chỉ dùng một lần.",
        night_order=80,
        tags=("self_target",),
    )

    def __init__(self) -> None:
        super().__init__()
        self.heal_available = True
        self.kill_available = True
