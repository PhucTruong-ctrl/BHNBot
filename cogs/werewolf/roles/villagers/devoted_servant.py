"""Devoted Servant role - can steal eliminated player's role when voted out."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")


@register_role
class DevovedServant(Role):
    metadata = RoleMetadata(
        name="Người Tôi Tớ Trung Thành",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Khi ai đó bị dân làng treo cổ, trước khi lộ bài, bạn có thể tự lộ diện. Nếu vậy, bạn mất lá bài của mình và nhận lá bài của người bị treo cổ (bí mật) cho đến hết trò chơi. Nếu bạn là tình nhân, bạn không thể dùng kỹ năng này.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/devoted-servant.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.has_used_power: bool = False  # Track if power has been used

    @property
    def alignment(self) -> str:  # type: ignore[override]
        """Return current alignment based on stolen role if any."""
        # If we've stolen a role, this is tracked separately in game state
        return self.metadata.alignment
