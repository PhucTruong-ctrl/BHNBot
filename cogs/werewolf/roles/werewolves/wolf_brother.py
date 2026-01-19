"""Wolf Brother role - the leading wolf in the sibling pair."""

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
class WolfBrother(Role):
    metadata = RoleMetadata(
        name="Sói Anh",
        alignment=Alignment.WEREWOLF,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm thứ nhất, bạn nhận biết cô/em gái sói của mình. Bạn là Sói Anh - tham gia phe sói. Khi bạn chết, em gái sói sẽ tức giận và gia nhập phe sói.",
        night_order=5,  # First night priority
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/werewolf/wolf-brother.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.sister_id: Optional[int] = None  # ID of Wolf Sister

    async def on_first_night(self, game: WerewolfGame, player: PlayerState) -> None:
        """On first night, Wolf Brother and Sister meet to recognize each other."""
        # This will be called from game.py's first night setup
        if self.sister_id:
            sister = game.players.get(self.sister_id)
            if sister:
                await player.member.send(
                    f"🐺 **BẠN LÀ SÓI ANH!**\n"
                    f"Đêm thứ nhất, bạn nhận biết cô/em gái sói của mình: {sister.display_name()}\n"
                    f"Bạn sẽ dậy cùng phe sói mỗi đêm để giết người.\n"
                    f"Khi bạn chết, em gái sói sẽ tức giận và gia nhập phe sói."
                )
                
                # Notify sister (but don't add her to wolves yet)
                await sister.member.send(
                    f"🐺 **BẠN LÀ SÓI EM!**\n"
                    f"Đêm thứ nhất, bạn nhận biết anh sói của mình: {player.display_name()}\n"
                    f"Hiện tại bạn chưa thức dậy cùng phe sói. "
                    f"Khi anh sói chết, bạn sẽ tức giận và gia nhập phe sói để tiếp tục giết người."
                )
                
                logger.info(
                    "Wolf siblings recognized | guild=%s brother=%s sister=%s",
                    game.guild.id,
                    player.user_id,
                    self.sister_id,
                )

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:
        """When Wolf Brother dies, trigger sister's transformation."""
        if self.sister_id:
            sister = game.players.get(self.sister_id)
            if sister and sister.alive:
                # Transform sister into full werewolf
                await game._transform_wolf_sister(sister, player)
                logger.info(
                    "Wolf Brother died - Sister transforming | guild=%s brother=%s sister=%s",
                    game.guild.id,
                    player.user_id,
                    self.sister_id,
                )
