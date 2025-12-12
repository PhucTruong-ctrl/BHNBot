"""Pyromaniac role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Pyromaniac(Role):
    metadata = RoleMetadata(
        name="Kẻ Phóng Hỏa",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.THE_VILLAGE,
        description="Một lần trong ván chơi bạn có thể thiêu rụi một ngôi nhà, hạ gục chủ nhân của nó.",
        tags=("self_target",),
    )

    def __init__(self) -> None:
        super().__init__()
        self.ignited = False
