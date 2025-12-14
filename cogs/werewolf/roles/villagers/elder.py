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
        card_image_url="https://via.placeholder.com/250x350?text=Elder",
    )

    def __init__(self) -> None:
        super().__init__()
        self.wolf_hits = 0
