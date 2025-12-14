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
        description="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/neutral/piedpier.png",
        night_order=120,
        card_image_url="https://via.placeholder.com/250x350?text=Piper",
    )
