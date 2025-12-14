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
        description="Từ đêm thứ 2, bạn có thể hé mắt nhìn khi ma sói thức giấc (20% bị phát hiện). Nếu bị phát hiện, sói có thể chọn giết bạn thay thế.",
        night_order=30,
        card_image_url="https://static.wikia.nocookie.net/allthetropes/images/7/72/PetiteFille_2646.jpg/revision/latest?cb=20240927192722",
    )
