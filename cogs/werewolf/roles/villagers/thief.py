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
        night_order=10,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/thief.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.extra_cards = []
