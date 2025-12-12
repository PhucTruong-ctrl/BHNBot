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
        tags=("self_target",),
    )
