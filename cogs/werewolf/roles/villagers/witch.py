"""Witch role implementation."""

from __future__ import annotations

import logging
from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

logger = logging.getLogger("werewolf")


@register_role
class Witch(Role):
    metadata = RoleMetadata(
        name="Phù Thủy",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Bạn sở hữu hai bình thuốc: một cứu sống và một giết người. Mỗi bình chỉ dùng một lần.",
        night_order=80,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/witch.png",
        tags=("self_target",),
    )

    def __init__(self) -> None:
        super().__init__()
        self.heal_available = True
        self.kill_available = True
