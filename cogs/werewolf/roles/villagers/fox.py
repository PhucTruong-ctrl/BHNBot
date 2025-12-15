"""Fox role - can designate a group of 3 neighbors to detect werewolves."""

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
class Fox(Role):
    metadata = RoleMetadata(
        name="Cáo",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi đêm bạn có thể chỉ định 1 nhóm 3 người kế cận (chỉ người ở giữa). Nếu có ít nhất 1 Ma Sói trong nhóm, bạn giữ quyền này. Nếu không có, bạn mất quyền nhưng biết được 3 người đó không có sói.",
        night_order=55,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/fox.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.has_power = True  # Can fox still use power?
        self.checked_players: set[int] = set()  # Track who has been checked

    async def on_assign(self, game: WerewolfGame, player: PlayerState) -> None:
        """Notify fox about their power on assignment."""
        try:
            embed = game._create_embed(
                title="🦊 Cáo - Hướng Dẫn",
                description=(
                    "Mỗi đêm, bạn có thể chỉ định 1 nhóm 3 người kế cận bằng cách chỉ vào người ở giữa.\n\n"
                    "Nếu nhóm đó có ít nhất 1 Ma Sói, bạn giữ quyền này và có thể kiểm tra lại vào đêm sau.\n"
                    "Nếu nhóm đó không có Ma Sói nào, bạn mất quyền nhưng biết được 3 người đó toàn là dân làng.\n\n"
                    "Bạn không bắt buộc phải dùng quyền mỗi đêm."
                ),
                color=0xFF8C00,
            )
            await player.user.send(embed=embed)
            logger.info(f"Fox {player.user.name} assigned and notified")
        except Exception as e:
            logger.error(f"Failed to notify Fox {player.user.name}: {e}")
