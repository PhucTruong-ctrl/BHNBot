"""Thief role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Thief(Role):
    metadata = RoleMetadata(
        name="Tên Trộm",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Đêm đầu tiên bạn chọn một trong hai lá bài thừa để thay thế vai trò hiện tại.",
        first_night_only=True,
        night_order=5,
    )

    def __init__(self) -> None:
        super().__init__()
        self.extra_cards = []
