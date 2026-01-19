"""Fox role - can designate a group of 3 neighbors to detect werewolves."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_villagers_fox")


@register_role
class Fox(Role):
    metadata = RoleMetadata(
        name="Cáo",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi đêm bạn có thể chỉ định 1 nhóm 3 người kế cận (chỉ người ở giữa). Nếu có ít nhất 1 Ma Sói trong nhóm, bạn giữ quyền này. Nếu không có, bạn mất quyền nhưng biết được 3 người đó không có sói.",
        night_order=30,
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
            logger.info("Fox assigned | guild=%s fox=%s", game.guild.id, player.user_id)
        except Exception as e:
            logger.error("Failed to notify Fox | guild=%s fox=%s error=%s", 
                        game.guild.id, player.user_id, str(e))

    async def on_night(self, game: WerewolfGame, player: PlayerState) -> None:  # type: ignore[override]
        """Fox checks for werewolves each night."""
        if not player.alive or not self.has_power:
            logger.debug("Fox on_night skipped | guild=%s fox=%s alive=%s has_power=%s",
                        game.guild.id, player.user_id, player.alive, self.has_power)
            return
        
        logger.info("Fox on_night START | guild=%s fox=%s night=%s", 
                   game.guild.id, player.user_id, game.night_number)
        
        try:
            # Get all alive players
            alive = game.alive_players()
            if len(alive) < 3:
                logger.warning("Fox: Not enough alive players to check | guild=%s fox=%s alive=%s",
                             game.guild.id, player.user_id, len(alive))
                return
            
            # Find Fox's position
            fox_idx = None
            for idx, p in enumerate(alive):
                if p.user_id == player.user_id:
                    fox_idx = idx
                    break
            
            if fox_idx is None:
                logger.error("Fox not found in alive list | guild=%s fox=%s", game.guild.id, player.user_id)
                return
            
            # Get left and right neighbors
            left_neighbor = alive[(fox_idx - 1) % len(alive)]
            right_neighbor = alive[(fox_idx + 1) % len(alive)]
            
            logger.info("Fox neighbors identified | guild=%s fox=%s left=%s right=%s",
                       game.guild.id, player.user_id, left_neighbor.user_id, right_neighbor.user_id)
            
            # Prompt Fox to choose center player
            options = {
                left_neighbor.user_id: f"👈 {left_neighbor.display_name()}",
                right_neighbor.user_id: f"👉 {right_neighbor.display_name()}",
                0: "⏭️ Bỏ qua (không kiểm tra đêm này)",
            }
            
            center_choice = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="🦊 Cáo - Kiểm Tra Hàng Xóm",
                description="Chọn 1 trong 2 hàng xóm làm trung tâm của nhóm kiểm tra. Nếu nhóm đó có Ma Sói, bạn giữ quyền. Nếu không, bạn mất quyền.",
                options=options,
                allow_skip=False,
            )
            
            if center_choice == 0:
                logger.info("Fox chose to skip checking | guild=%s fox=%s",
                           game.guild.id, player.user_id)
                return
            
            # Get the three players in the group
            center_player = game.players.get(center_choice)
            if not center_player:
                logger.error("Center player not found | guild=%s center_id=%s", game.guild.id, center_choice)
                return
            
            # The group is: left, center, right
            group = [left_neighbor, center_player, right_neighbor]
            group_names = [p.display_name() for p in group]
            
            # Check if any in group is werewolf
            has_werewolf = any(p.alignment == "werewolf" for p in group)
            
            logger.info("Fox check performed | guild=%s fox=%s group=%s has_werewolf=%s",
                       game.guild.id, player.user_id, [p.user_id for p in group], has_werewolf)
            
            # Notify Fox of result
            if has_werewolf:
                result_msg = f"✅ **Nhóm có Ma Sói!** Bạn giữ được quyền kiểm tra cho đêm tới.\n\nNhóm kiểm tra: {', '.join(group_names)}"
                logger.info("Fox detected werewolf | guild=%s fox=%s",
                           game.guild.id, player.user_id)
            else:
                result_msg = f"❌ **Nhóm không có Ma Sói!** Bạn mất quyền kiểm tra vĩnh viễn, nhưng biết được 3 người này toàn dân làng.\n\nNhóm kiểm tra: {', '.join(group_names)}"
                self.has_power = False  # Lose power
                logger.info("Fox found no werewolf, lost power | guild=%s fox=%s",
                           game.guild.id, player.user_id)
            
            await player.user.send(result_msg)
            self.checked_players.add(center_choice)
            
            logger.info("Fox on_night END | guild=%s fox=%s result=werewolf_found:%s", 
                       game.guild.id, player.user_id, has_werewolf)
        
        except Exception as e:
            logger.error("Error in Fox on_night | guild=%s fox=%s error=%s",
                        game.guild.id, player.user_id, str(e), exc_info=True)
