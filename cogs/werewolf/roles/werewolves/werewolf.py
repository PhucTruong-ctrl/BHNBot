"""Standard werewolf role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Werewolf(Role):
    metadata = RoleMetadata(
        name="Ma Sói",
        alignment=Alignment.WEREWOLF,
        expansion=Expansion.BASIC,
        description="Bạn là Ma Sói. Mỗi đêm hãy phối hợp cùng đồng bọn để chọn con mồi.",
        card_image_url="https://i.pinimg.com/736x/4c/a3/4d/4ca34d7887dd3760afb4342d0c8eb6c2.jpg",
        tags=("self_target",),
    )
