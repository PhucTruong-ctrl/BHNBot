"""Knight role with lightning sword."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_villagers_knigh")


@register_role
class Knight(Role):
    metadata = RoleMetadata(
        name="Hiệp Sĩ",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Khi bị Ma Sói cắn chết, chiếc kiếm rĩ sét của bạn sẽ giết chết Ma Sói gần nhất (bên trái đầu tiên).",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/knight.png",
    )

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Knight is killed by wolves, the nearest wolf dies next night."""
        logger.info("Knight on_death triggered | guild=%s knight=%s cause=%s", game.guild.id, player.user_id, cause)
        if cause != "killed":
            logger.debug("Knight died not by wolves, no revenge | guild=%s knight=%s cause=%s", game.guild.id, player.user_id, cause)
            return
        
        # Find all alive werewolves
        wolves = [p for p in game.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        
        if not wolves:
            logger.warning("Knight died but no wolves alive | guild=%s knight=%s", game.guild.id, player.user_id)
            return
        
        # Mark the first wolf (leftmost) to die next night
        target_wolf = wolves[0]
        # CRITICAL FIX: Add wolf to pending deaths so they actually die
        logger.info("Knight revenge sword queued | guild=%s knight=%s target_wolf=%s", game.guild.id, player.user_id, target_wolf.user_id)
        game._pending_deaths.append((target_wolf.user_id, "knight"))
        
        # Notify the wolf that they will die
        try:
            await target_wolf.member.send(
                f"⚡ Thanh kiếm rĩ sét của {player.display_name()} đã đánh bạn! Bạn sẽ chết vào sáng mai."
            )
        except Exception as e:
            logger.warning("Failed to notify wolf of knight revenge | guild=%s wolf=%s error=%s", game.guild.id, target_wolf.user_id, str(e))
