"""Pied Piper role - charms players each night to win when all are charmed."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING, Optional, Set

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_neutrals_pied_p")


@register_role
class PiedPiper(Role):
    metadata = RoleMetadata(
        name="Thổi Sáo",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.NEW_MOON,
        description="Mỗi đêm bạn có thể mê hoặc tối đa 2 người chơi mới (không kể bản thân). Những người bị mê hoặc sẽ thức dậy để nhận diện lẫn nhau. Bạn thắng nếu tất cả người chơi còn sống đều bị mê hoặc.",
        night_order=100,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/neutral/piedpier.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.charmed_players: Set[int] = set()  # Set of user IDs of charmed players

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, Pied Piper can charm up to 2 new players."""
        logger.info(
            "Pied Piper on_night START | guild=%s pied_piper=%s night=%d charmed_count=%d",
            game.guild.id,
            player.user_id,
            night_number,
            len(self.charmed_players),
        )

        # Get all alive players except Pied Piper
        alive_players = [p for p in game.alive_players() if p.user_id != player.user_id]
        
        # Get players not yet charmed
        available_to_charm = [p for p in alive_players if p.user_id not in self.charmed_players]

        if not available_to_charm:
            logger.info(
                "Pied Piper on_night END | all_alive_charmed=true | guild=%s pied_piper=%s",
                game.guild.id,
                player.user_id,
            )
            return

        # Ask Pied Piper to choose up to 2 players to charm
        try:
            from ...engine.voting import VoteSession

            view = VoteSession(
                title="🎺 Thổi Sáo - Chọn người để mê hoặc",
                description=f"Chọn tối đa 2 người mới để mê hoặc (hiện có {len(self.charmed_players)} người mê hoặc).",
                options=[p.user for p in available_to_charm],
                max_selections=min(2, len(available_to_charm)),
                timeout=45,
            )

            selected_users = await view.wait_for_result()
            
            if not selected_users:
                logger.info(
                    "Pied Piper on_night | no_selection | guild=%s pied_piper=%s",
                    game.guild.id,
                    player.user_id,
                )
                return

            # Add newly charmed players
            new_charmed_ids = [u.id for u in selected_users]
            self.charmed_players.update(new_charmed_ids)

            logger.info(
                "Pied Piper on_night | charmed_new | guild=%s pied_piper=%s charmed_ids=%s total_charmed=%d",
                game.guild.id,
                player.user_id,
                new_charmed_ids,
                len(self.charmed_players),
            )

            # Wake up all charmed players to see each other
            charmed_player_objs = [p for p in game.alive_players() if p.user_id in self.charmed_players]
            
            if charmed_player_objs:
                charmed_users = [p.user for p in charmed_player_objs]
                charmed_names = ", ".join([p.user.mention for p in charmed_player_objs])
                
                message = (
                    "🎺 **Bạn đã bị mê hoặc bởi Thổi Sáo!**\n\n"
                    f"Những người bị mê hoặc cùng với bạn: {charmed_names}\n\n"
                    "Hãy ghi nhớ danh tính của nhau. Thổi Sáo sẽ thắng nếu tất cả người chơi còn sống đều bị mê hoặc."
                )
                
                for user in charmed_users:
                    try:
                        await user.send(message)
                        logger.debug(
                            "Pied Piper notification sent | guild=%s user=%s",
                            game.guild.id,
                            user.id,
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to send Pied Piper notification | guild=%s user=%s error=%s",
                            game.guild.id,
                            user.id,
                            str(e),
                            exc_info=True,
                        )

        except Exception as e:
            logger.error(
                "Pied Piper on_night error | guild=%s pied_piper=%s error=%s",
                game.guild.id,
                player.user_id,
                str(e),
                exc_info=True,
            )

    async def check_win_condition(self, game: WerewolfGame, player: PlayerState) -> Optional[str]:  # type: ignore[override]
        """Check if Pied Piper wins - all alive players are charmed."""
        alive_players = game.alive_players()
        
        # Count alive players that are NOT Pied Piper
        other_alive = [p for p in alive_players if p.user_id != player.user_id]
        
        if not other_alive:
            # Only Pied Piper is alive - they can't win (need to charm others)
            logger.info(
                "Pied Piper check_win | pied_piper_alone | guild=%s pied_piper=%s",
                game.guild.id,
                player.user_id,
            )
            return None
        
        # Check if all other alive players are charmed
        all_charmed = all(p.user_id in self.charmed_players for p in other_alive)
        
        if all_charmed:
            charmed_count = len(self.charmed_players)
            logger.info(
                "Pied Piper WIN CONDITION MET | guild=%s pied_piper=%s charmed_count=%d",
                game.guild.id,
                player.user_id,
                charmed_count,
            )
            return f"🎺 **Thổi Sáo thắng!** Tất cả {charmed_count} người chơi còn sống đều bị mê hoặc!"
        
        logger.debug(
            "Pied Piper check_win | not_all_charmed | guild=%s pied_piper=%s charmed=%d other_alive=%d",
            game.guild.id,
            player.user_id,
            len(self.charmed_players),
            len(other_alive),
        )
        return None

