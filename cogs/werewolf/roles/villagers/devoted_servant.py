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

    async def on_assign(self, game: WerewolfGame, player: PlayerState) -> None:
        """Notify Devoted Servant about their power on assignment."""
        try:
            embed = game._create_embed(
                title="🤝 Người Tôi Tớ Trung Thành - Hướng Dẫn",
                description=(
                    "Mỗi khi ai đó bị dân làng treo cổ (trước khi lộ bài), bạn có thể chọn lộ diện.\n\n"
                    "Nếu bạn đồng ý:\n"
                    "- Vai trò của bạn sẽ bị lộ diện cho mọi người\n"
                    "- Bạn sẽ bí mật nhận lấy vai trò của người vừa bị treo\n"
                    "- Bạn chỉ có thể dùng kỹ năng này 1 lần\n\n"
                    "⚠️ **Nếu bạn là tình nhân, bạn KHÔNG thể dùng kỹ năng này!**"
                ),
                color=0xFF69B4,
            )
            await player.user.send(embed=embed)
            logger.info("Devoted Servant assigned | guild=%s servant=%s", 
                       game.guild.id, player.user_id)
        except Exception as e:
            logger.error("Failed to notify Devoted Servant | guild=%s servant=%s error=%s",
                        game.guild.id, player.user_id, str(e))

    @property
    def alignment(self) -> str:  # type: ignore[override]
        """Return current alignment based on stolen role if any."""
        # If we've stolen a role, this is tracked separately in game state
        logger.debug("Devoted Servant alignment check | has_used_power=%s", self.has_used_power)
        return self.metadata.alignment
