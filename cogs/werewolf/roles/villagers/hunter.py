"""Hunter role implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")


@register_role
class Hunter(Role):
    metadata = RoleMetadata(
        name="Thợ Săn",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Mỗi đêm chọn 1 người. Nếu bị giết, người đó chết theo. Nếu bị treo cổ, chọn 1 người để bắn.",
        night_order=75,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/hunter.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.marked_target: int | None = None

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, Hunter chooses someone to mark."""
        logger.info("Hunter on_night start | guild=%s hunter=%s night=%s", game.guild.id, player.user_id, night_number)
        choices = {p.user_id: p.display_name() for p in game.alive_players() if p.user_id != player.user_id}
        if not choices:
            logger.warning("No valid targets for Hunter | guild=%s hunter=%s", game.guild.id, player.user_id)
            return
        
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Thợ Săn - Đánh Dấu Mục Tiêu",
            description="Chọn 1 người để đánh dấu. Nếu bạn chết đêm nay, người này sẽ chết theo.",
            options=choices,
            allow_skip=False,
        )
        if target_id and target_id in choices:
            self.marked_target = target_id
            logger.info("Hunter marked target | guild=%s hunter=%s target=%s", game.guild.id, player.user_id, target_id)
        else:
            logger.warning("Hunter failed to mark or skipped | guild=%s hunter=%s", game.guild.id, player.user_id)

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Hunter dies, take someone with them."""
        logger.info("Hunter on_death triggered | guild=%s hunter=%s cause=%s alive=%s marked=%s", game.guild.id, player.user_id, cause, player.alive, self.marked_target)
        if cause == "lynch":
            # Voted out - choose who to shoot
            choices = {p.user_id: p.display_name() for p in game.alive_players() if p.user_id != player.user_id}
            if not choices:
                logger.warning("No valid targets for Hunter revenge | guild=%s hunter=%s", game.guild.id, player.user_id)
                return
            # CRITICAL FIX: Verify alive before prompting dead player
            if not player.alive:
                logger.warning("Hunter is dead, skipping revenge DM | guild=%s hunter=%s", game.guild.id, player.user_id)
                return
            target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="Thợ Săn Trả Thù",
                description="Bạn bị treo cổ! Chọn 1 người để bắn trước khi gục ngã.",
                options=choices,
                allow_skip=True,
            )
            if target_id and target_id in choices:
                logger.info("Hunter lynch revenge kill queued | guild=%s hunter=%s victim=%s", game.guild.id, player.user_id, target_id)
                game._pending_deaths.append((target_id, "hunter"))  # pylint: disable=protected-access
                # Check for achievement: Hunter kill wolf
                target_player = game.players.get(target_id)
                if target_player and target_player.get_alignment_priority() == Alignment.WEREWOLF:
                    player.hunter_killed_wolf = True
            else:
                logger.info("Hunter skipped revenge | guild=%s hunter=%s", game.guild.id, player.user_id)
        else:
            # Killed by other means (wolves, witch, etc) - use marked target
            logger.info("Hunter killed by %s, checking marked target | guild=%s hunter=%s marked=%s", cause, game.guild.id, player.user_id, self.marked_target)
            if self.marked_target and self.marked_target in game.players:
                target_player = game.players.get(self.marked_target)
                if target_player and target_player.alive:
                    logger.info("Hunter mark revenge kill queued | guild=%s hunter=%s victim=%s", game.guild.id, player.user_id, self.marked_target)
                    game._pending_deaths.append((self.marked_target, "hunter"))  # pylint: disable=protected-access
                    # Check for achievement: Hunter kill wolf
                    if target_player.get_alignment_priority() == Alignment.WEREWOLF:
                        player.hunter_killed_wolf = True
                else:
                    logger.info("Hunter marked target already dead | guild=%s hunter=%s target=%s", game.guild.id, player.user_id, self.marked_target)
            else:
                logger.debug("Hunter has no marked target | guild=%s hunter=%s", game.guild.id, player.user_id)
