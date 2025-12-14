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
        card_image_url="https://static.wikia.nocookie.net/allthetropes/images/b/b6/Voleur_5192.jpg/revision/latest?cb=20240928215129",
    )

    def __init__(self) -> None:
        super().__init__()
        self.extra_cards = []
