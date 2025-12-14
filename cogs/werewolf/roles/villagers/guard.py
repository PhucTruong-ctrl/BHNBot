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
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/savior.png",
        tags=("self_target",),
    )

    def __init__(self) -> None:
        super().__init__()
        self.last_protected: int | None = None
