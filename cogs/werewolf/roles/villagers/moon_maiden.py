"""Moon Maiden role - disables target's night abilities."""

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
class MoonMaiden(Role):
    metadata = RoleMetadata(
        name="Nguyệt Nữ",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi đêm bạn chọn 1 người chơi. Kĩ năng của họ sẽ bị vô hiệu hóa trong suốt đêm đó. Không vô hiệu hóa được Bảo Vệ và các kĩ năng ban ngày. Không được chọn cùng 1 người 2 đêm liên tiếp.",
        night_order=110,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/moon-maiden.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.last_target_id: int | None = None

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, Moon Maiden chooses someone to disable."""
        logger.info("Moon Maiden on_night start | guild=%s maiden=%s night=%s last_target=%s", game.guild.id, player.user_id, night_number, self.last_target_id)
        if night_number < 1:
            return
        
        # Get all alive players except self and last target
        alive = game.alive_players()
        options = {}
        for p in alive:
            if p.user_id != player.user_id and p.user_id != self.last_target_id:
                options[p.user_id] = p.display_name()
        
        if not options:
            logger.debug("No valid options for Moon Maiden | guild=%s maiden=%s", game.guild.id, player.user_id)
            # If only one person available (last target), can skip
            return
        
        choice = await game._prompt_dm_choice(
            player.member,
            title="Nguyệt Nữ - Chọn Mục Tiêu",
            description="Hãy chọn 1 người để vô hiệu hóa kĩ năng của họ trong đêm này. Không vô hiệu hóa được Bảo Vệ.",
            options=options,
            allow_skip=False,
            timeout=120,
        )
        
        if choice and choice in options:
            self.last_target_id = choice
            target = game.players.get(choice)
            logger.info("Moon Maiden disabled target | guild=%s maiden=%s target=%s", game.guild.id, player.user_id, choice)
            game._moon_maiden_disabled = choice
            if target:
                await game._safe_send_dm(
                    player.member,
                    content=f"Bạn đã vô hiệu hóa kĩ năng của {target.display_name()} trong đêm này."
                )
                await game._safe_send_dm(
                    target.member,
                    content="Nguyệt Nữ đã vô hiệu hóa kĩ năng của bạn trong đêm này!"
                )
        else:
            logger.debug("Moon Maiden skipped disable | guild=%s maiden=%s", game.guild.id, player.user_id)
            if target:
                # Store disabled player in game
                game._moon_maiden_disabled = choice
                await game._safe_send_dm(
                    player.member,
                    content=f"Bạn đã vô hiệu hóa kĩ năng của {target.display_name()} trong đêm này."
                )
