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
        description=(
            "Khi ai đó bị dân làng treo cổ, trước khi lộ bài, bạn có thể tự lộ diện. "
            "Nếu vậy, bạn mất lá bài của mình và nhận lá bài của người bị treo cổ (bí mật) cho đến hết trò chơi. "
            "⚠️ Nếu bạn là tình nhân hoặc có các vai trò đặc biệt khác, áp dụng quy tắc đặc biệt."
        ),
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/devoted-servant.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.has_used_power: bool = False  # Track if power has been used
        self.was_lover: bool = False  # Track if servant was a lover before stealing
        self.was_sheriff: bool = False  # Track if servant was a sheriff
        self.was_town_crier: bool = False  # Track if servant was a town crier
        self.was_charmed: bool = False  # Track if servant was charmed/infected
        self.stolen_role: Optional[Role] = None  # Store the role the servant stole

    async def on_assign(self, game: WerewolfGame, player: PlayerState) -> None:
        """Notify Devoted Servant about their power on assignment."""
        try:
            embed = game._create_embed(
                title="🤝 Người Tôi Tớ Trung Thành - Hướng Dẫn",
                description=(
                    "Mỗi khi ai đó bị dân làng treo cổ (trước khi lộ bài), bạn có thể chọn lộ diện.\n\n"
                    "📜 **Quy tắc khi nhận vai trò mới:**\n"
                    "• Nếu bạn là **tình nhân**: Bạn KHÔNG thể dùng kỹ năng này\n"
                    "• Nếu bạn bị **mê hoặc/nhiễm**: Trạng thái được giữ nguyên\n"
                    "• Nếu bạn là **Sheriff/Town Crier**: Xem quy tắc đặc biệt\n\n"
                    "Nếu bạn đồng ý nhận vai trò mới:\n"
                    "- Vai trò của bạn sẽ bị lộ diện cho mọi người\n"
                    "- Bạn sẽ bí mật nhận lấy vai trò của người vừa bị treo\n"
                    "- Bạn chỉ có thể dùng kỹ năng này 1 lần"
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
        # If we've stolen a role, return its alignment
        if self.stolen_role:
            return self.stolen_role.alignment
        logger.debug("Devoted Servant alignment check | has_used_power=%s has_stolen=%s", 
                    self.has_used_power, bool(self.stolen_role))
        return self.metadata.alignment

    async def handle_stolen_role_assignment(self, game: WerewolfGame, player: PlayerState, stolen_role: Role) -> None:
        """
        Handle special cases when Devoted Servant steals a role.
        
        Implements the official rulebook edge cases:
        - Lover: ex-Servant doesn't become Lover, but old lover dies
        - Sheriff: special succession rules apply
        - Town Crier: special succession rules apply
        - Charmed/Infected: status is preserved
        """
        try:
            target_role_name = stolen_role.metadata.name
            logger.info(
                "Devoted Servant STEALING role | guild=%s servant=%s target_role=%s",
                game.guild.id, player.user_id, target_role_name
            )
            
            # Store state before transition
            self.stolen_role = stolen_role
            self.was_lover = player.user_id in game._lovers
            self.was_charmed = player.user_id in game._charmed
            
            # CASE 1: Stolen role is Lover
            if target_role_name == "Thần Tình Yêu" or "Lover" in stolen_role.__class__.__name__:
                logger.info(
                    "SERVANT stealing LOVER role | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Ex-Servant does NOT become a lover
                # But the old lover dies of sorrow
                game._lovers.discard(player.user_id)
                # Find the other lover and eliminate them
                for lover_id in game._lovers:
                    lover = game.players.get(lover_id)
                    if lover and lover.alive:
                        lover.alive = False
                        await game.channel.send(
                            f"💔 **{lover.display_name()}** (Tình Nhân) chết vì đau buồn sau khi mất người yêu!"
                        )
                        logger.info("LOVER died of sorrow | guild=%s lover=%s", game.guild.id, lover_id)
                        break
                game._lovers.clear()
                return
            
            # CASE 2: Stolen role is Sheriff
            if target_role_name == "Trưởng Làng" or "Sheriff" in stolen_role.__class__.__name__:
                logger.info(
                    "SERVANT stealing SHERIFF role | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Ex-Servant does NOT become Sheriff
                # Former Sheriff chooses successor
                # TODO: Implement Sheriff succession logic
                return
            
            # CASE 3: Stolen role is Town Crier
            if "Town Crier" in target_role_name or "Town Crier" in stolen_role.__class__.__name__:
                logger.info(
                    "SERVANT stealing TOWN_CRIER role | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Ex-Servant does NOT become Town Crier
                # Sheriff chooses new Town Crier (could be ex-Servant)
                # TODO: Implement Town Crier succession logic
                return
            
            # CASE 4: Stolen role is Charmed/Infected
            if self.was_charmed:
                logger.info(
                    "SERVANT was CHARMED, status PRESERVED | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Ex-Servant remains charmed
                game._charmed.add(player.user_id)
                return
            
            # Default: Servant takes the stolen role
            logger.info(
                "Devoted Servant SUCCESSFULLY stole role | guild=%s servant=%s stolen_role=%s",
                game.guild.id, player.user_id, target_role_name
            )
        
        except Exception as e:
            logger.error(
                "ERROR in handle_stolen_role_assignment | guild=%s servant=%s error=%s",
                game.guild.id, player.user_id, str(e), exc_info=True
            )

    async def handle_servant_elimination(self, game: WerewolfGame, player: PlayerState) -> None:
        """
        Handle edge cases when Devoted Servant themselves is eliminated.
        
        Different rules apply depending on what role they had before elimination:
        - Lover: Cannot use Servant power
        - Sheriff: Loses position, chooses successor
        - Town Crier: Retains position
        - Charmed/Infected: Status is preserved
        """
        try:
            logger.info(
                "Devoted Servant ELIMINATED | guild=%s servant=%s",
                game.guild.id, player.user_id
            )
            
            # If servant was a lover when they were eliminated
            if self.was_lover:
                logger.info(
                    "SERVANT was LOVER when eliminated | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Cannot use Servant power
                self.has_used_power = True
                return
            
            # If servant was Sheriff when eliminated
            if self.was_sheriff:
                logger.info(
                    "SERVANT was SHERIFF when eliminated | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Ex-Servant no longer Sheriff, chooses successor
                # TODO: Implement Sheriff succession logic
                return
            
            # If servant was Town Crier when eliminated
            if self.was_town_crier:
                logger.info(
                    "SERVANT was TOWN_CRIER when eliminated | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Ex-Servant RETAINS Town Crier status
                # New cards not dealt
                return
            
            # If servant was charmed/infected when eliminated
            if self.was_charmed:
                logger.info(
                    "SERVANT was CHARMED when eliminated | guild=%s servant=%s",
                    game.guild.id, player.user_id
                )
                # Ex-Servant remains charmed/infected
                game._charmed.add(player.user_id)
                return
        
        except Exception as e:
            logger.error(
                "ERROR in handle_servant_elimination | guild=%s servant=%s error=%s",
                game.guild.id, player.user_id, str(e), exc_info=True
            )
