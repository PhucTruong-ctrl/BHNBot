"""Pied Piper role."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class PiedPiper(Role):
    metadata = RoleMetadata(
        name="Thổi Sáo",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.NEW_MOON,
        description="Mỗi đêm bạn thôi miên tối đa hai người. Khi tất cả những người còn sống đều bị thôi miên, bạn thắng.",
        night_order=120,
    )
