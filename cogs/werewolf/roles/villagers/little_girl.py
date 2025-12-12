"""Little girl role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class LittleGirl(Role):
    metadata = RoleMetadata(
        name="Cô Bé",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Bạn có thể hé mắt khi ma sói thức dậy để đoán ra danh tính của chúng.",
        night_order=30,
    )
