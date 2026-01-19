"""Avenger role - chooses side on first night and seeks revenge when killed."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_neutrals_avenge")


@register_role
class Avenger(Role):
    metadata = RoleMetadata(
        name="Kẻ Báo Thù",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm đầu tiên bạn chọn theo Phe Sói hoặc Dân Làng. Khi bạn chết, bạn được chọn một người để báo thù: nếu theo phe sói thì sẽ tìm Dân để giết, nếu theo phe dân thì sẽ tìm Sói để giết.",
        first_night_only=False,
        night_order=15,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/neutral/avenger.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.chosen_side: Optional[Alignment] = None  # WEREWOLF or VILLAGE
        self.revenge_target: Optional[int] = None

    async def on_first_night(self, game: WerewolfGame, player: PlayerState) -> None:  # type: ignore[override]
        """On first night, Avenger chooses which side to support."""
        logger.info("Avenger first-night start | guild=%s avenger=%s", game.guild.id, player.user_id)
        
        try:
            options = {
                1: "🐺 Phe Sói (bạn sẽ là Sói nhưng không cắn, không vào thread sói)",
                2: "🏘️ Phe Dân Làng (bạn bình thường)"
            }
            
            choice = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="Kẻ Báo Thù - Chọn Phe",
                description="Chọn phe nào để ủng hộ. Khi bạn chết, bạn sẽ báo thù phe đối thủ.",
                options=options,
                allow_skip=False,
            )
            
            if choice == 1:
                # Choose werewolf side - will show as werewolf to seer/hunter/fox
                self.chosen_side = Alignment.WEREWOLF
                await game._safe_send_dm(player.member, "✅ Bạn đã chọn theo Phe Sói! Khi chết, bạn sẽ báo thù lên Dân Làng.")
                logger.info("Avenger chose werewolf side | guild=%s avenger=%s", game.guild.id, player.user_id)
            else:
                # Choose village side
                self.chosen_side = Alignment.VILLAGE
                await game._safe_send_dm(player.member, "✅ Bạn đã chọn theo Phe Dân Làng! Khi chết, bạn sẽ báo thù lên Ma Sói.")
                logger.info("Avenger chose village side | guild=%s avenger=%s", game.guild.id, player.user_id)
        
        except Exception as e:
            logger.error("Error in Avenger first-night | guild=%s avenger=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)

    @property
    def alignment(self) -> Alignment:
        """Return alignment based on chosen side, or NEUTRAL if not yet chosen."""
        if self.chosen_side:
            return self.chosen_side
        return Alignment.NEUTRAL

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Avenger dies, they get to choose revenge based on their side."""
        logger.info("Avenger on_death triggered | guild=%s avenger=%s cause=%s chosen_side=%s", 
                   game.guild.id, player.user_id, cause, self.chosen_side)
        
        if not self.chosen_side:
            logger.warning("Avenger died before choosing a side | guild=%s avenger=%s", 
                          game.guild.id, player.user_id)
            return
        
        try:
            # Prepare revenge target options based on chosen side
            if self.chosen_side == Alignment.WEREWOLF:
                # Avenger chose werewolf side - seek revenge on villagers
                target_options = {
                    p.user_id: p.display_name() 
                    for p in game.alive_players() 
                    if p.user_id != player.user_id and all(r.alignment == Alignment.VILLAGE for r in p.roles)
                }
                choice_description = "Chọn một Dân Làng để báo thù (nếu đúng sẽ chết ngay):"
                revenge_type = "villager"
            else:
                # Avenger chose village side - seek revenge on werewolves
                target_options = {
                    p.user_id: p.display_name() 
                    for p in game.alive_players() 
                    if p.user_id != player.user_id and any(r.alignment == Alignment.WEREWOLF for r in p.roles)
                }
                choice_description = "Chọn một Ma Sói để báo thù (nếu đúng sẽ chết ngay):"
                revenge_type = "werewolf"
            
            if not target_options:
                logger.info("Avenger has no valid revenge targets | guild=%s avenger=%s side=%s", 
                           game.guild.id, player.user_id, self.chosen_side)
                return
            
            # Check if player is dead before prompting
            if not player.alive:
                logger.warning("Avenger is dead, skipping revenge DM | guild=%s avenger=%s", 
                              game.guild.id, player.user_id)
                return
            
            revenge_target = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="Kẻ Báo Thù - Báo Thù",
                description=choice_description,
                options=target_options,
                allow_skip=True,
            )
            
            if revenge_target and revenge_target in target_options:
                target_player = game.players.get(revenge_target)
                
                # Verify target alignment
                target_is_werewolf = any(r.alignment == Alignment.WEREWOLF for r in target_player.roles)
                target_is_villager = all(r.alignment == Alignment.VILLAGE for r in target_player.roles)
                
                revenge_success = False
                if self.chosen_side == Alignment.WEREWOLF and target_is_villager:
                    # Avenger is werewolf side, target is villager - SUCCESS
                    revenge_success = True
                elif self.chosen_side == Alignment.VILLAGE and target_is_werewolf:
                    # Avenger is village side, target is werewolf - SUCCESS
                    revenge_success = True
                
                if revenge_success:
                    logger.info("Avenger revenge SUCCESS | guild=%s avenger=%s target=%s side=%s", 
                               game.guild.id, player.user_id, revenge_target, self.chosen_side)
                    game._pending_deaths.append((revenge_target, "avenger"))  # pylint: disable=protected-access
                    
                    # Notify the Avenger of success
                    await game._safe_send_dm(player.member, 
                        f"💀 Báo thù thành công! {target_player.display_name()} sẽ chết!")
                else:
                    logger.info("Avenger revenge FAILED | guild=%s avenger=%s target=%s side=%s", 
                               game.guild.id, player.user_id, revenge_target, self.chosen_side)
                    # Notify the Avenger of failure
                    await game._safe_send_dm(player.member, 
                        f"❌ Báo thù thất bại! {target_player.display_name()} không phải mục tiêu của bạn.")
            else:
                logger.info("Avenger skipped revenge | guild=%s avenger=%s", 
                           game.guild.id, player.user_id)
        
        except Exception as e:
            logger.error("Error in Avenger revenge | guild=%s avenger=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)
