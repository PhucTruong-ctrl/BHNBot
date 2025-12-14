"""Hypnotist role - charms target to die instead if hypnotist dies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState


@register_role
class Hypnotist(Role):
    metadata = RoleMetadata(
        name="Cổ Hoặc Sư",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi đêm bạn chọn 1 người để mê hoặc. Nếu bạn chết đêm đó, người bị mê hoặc sẽ chết thay. Không được chọn cùng 1 người 2 đêm liên tiếp.",
        night_order=105,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/hypnotist.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.last_target_id: int | None = None
        self.charmed_target_id: int | None = None

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, Hypnotist chooses someone to charm."""
        if night_number < 1:
            return
        
        # Get all alive players except self and last target
        alive = game.alive_players()
        options = {}
        for p in alive:
            if p.user_id != player.user_id and p.user_id != self.last_target_id:
                options[p.user_id] = p.display_name()
        
        if not options:
            # If only one person available (last target), can skip
            return
        
        choice = await game._prompt_dm_choice(
            player.member,
            title="Cổ Hoặc Sư - Chọn Mục Tiêu",
            description="Hãy chọn 1 người để mê hoặc. Nếu bạn chết đêm nay, người đó sẽ chết thay bạn.",
            options=options,
            allow_skip=False,
            timeout=120,
        )
        
        if choice and choice in options:
            self.last_target_id = choice
            self.charmed_target_id = choice
            target = game.players.get(choice)
            if target:
                # Store charmed player in game
                game._hypnotist_charm_target = choice
                await game._safe_send_dm(
                    player.member,
                    content=f"Bạn đã mê hoặc {target.display_name()}. Nếu bạn chết đêm nay, họ sẽ chết thay bạn."
                )
                await game._safe_send_dm(
                    target.member,
                    content=f"Bạn đã bị Cổ Hoặc Sư mê hoặc! Nếu Cổ Hoặc Sư chết đêm nay, bạn sẽ chết thay họ."
                )
