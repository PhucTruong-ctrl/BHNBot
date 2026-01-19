"""Wolf Sister role - hidden wolf activated when brother dies."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_werewolves_wolf")


@register_role
class WolfSister(Role):
    metadata = RoleMetadata(
        name="Sói Em",
        alignment=Alignment.VILLAGE,  # Hidden until transformation
        expansion=Expansion.THE_VILLAGE,
        description="Đêm thứ nhất, bạn nhận biết anh sói của mình. Bạn bị ẩn từ Tiên Tri/Cáo/Gấu cho đến khi anh sói chết. Khi anh sói chết, bạn tức giận và gia nhập phe sói.",
        night_order=6,  # Slightly after brother
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/werewolf/wolf-sister.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.brother_id: Optional[int] = None  # ID of Wolf Brother
        self.is_transformed: bool = False  # Becomes True when brother dies

    async def on_first_night(self, game: WerewolfGame, player: PlayerState) -> None:
        """On first night, Wolf Sister meets her brother."""
        if self.brother_id:
            brother = game.players.get(self.brother_id)
            if brother:
                # Notification already sent by brother's on_first_night
                # Just acknowledge here
                logger.info(
                    "Wolf Sister recognized brother | guild=%s sister=%s brother=%s",
                    game.guild.id,
                    player.user_id,
                    self.brother_id,
                )
