"""Scapegoat role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Scapegoat(Role):
    metadata = RoleMetadata(
        name="Kẻ Thế Thân",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.NEW_MOON,
        description="Nếu dân làng hòa phiếu, bạn sẽ bị xử tử thay. Bạn có thể quyết định ai được bỏ phiếu vào sáng hôm sau (chức năng giản lược).",
    )
