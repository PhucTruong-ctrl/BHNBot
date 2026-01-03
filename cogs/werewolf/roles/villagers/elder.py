"""Elder role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Elder(Role):
    metadata = RoleMetadata(
        name="Già Làng",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.NEW_MOON,
        description="Bạn chịu được một lần cắn của Ma Sói. Sau lần thứ hai bạn sẽ chết.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/elder.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.wolf_hits = 0
