"""Protector role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Guard(Role):
    metadata = RoleMetadata(
        name="Bảo Vệ",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.NEW_MOON,
        description="Mỗi đêm bạn chọn một người để bảo vệ khỏi Ma Sói. Không được bảo vệ cùng một người hai đêm liên tiếp.",
        card_image_url="https://via.placeholder.com/250x350?text=Guard",
        tags=("self_target",),
    )

    def __init__(self) -> None:
        super().__init__()
        self.last_protected: int | None = None
