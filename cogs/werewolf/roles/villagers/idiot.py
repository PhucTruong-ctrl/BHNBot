"""Idiot role from New Moon."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Idiot(Role):
    metadata = RoleMetadata(
        name="Thằng Ngốc",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.NEW_MOON,
        description="Nếu bị dân làng treo cổ, bạn lộ bài và sống sót nhưng mất quyền bỏ phiếu.",
    )

    def __init__(self) -> None:
        super().__init__()
        self.revealed = False
