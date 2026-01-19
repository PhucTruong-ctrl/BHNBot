"""Demon Wolf role - can curse a victim to become a werewolf instead of dying."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_werewolves_demo")


@register_role
class DemonWolf(Role):
    metadata = RoleMetadata(
        name="Sói Quỷ",
        alignment=Alignment.WEREWOLF,
        expansion=Expansion.THE_VILLAGE,
        description="Bạn là Sói Quỷ. Mỗi đêm hãy phối hợp cùng đồng bọn để chọn con mồi. Một lần trong trò chơi, bạn có thể nguyền rủa nạn nhân, biến họ thành Ma Sói thay vì chết (họ vẫn giữ vai trò cũ).",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/werewolf/wolf-father.png",
        night_order=95,
    )

    def __init__(self) -> None:
        super().__init__()
        self.curse_used = False  # Track if curse has been used

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, offer Demon Wolf the option to curse a victim."""
        if self.curse_used:
            # Curse already used, no action needed
            return

        # Check if there are pending wolf kills
        if not game._pending_deaths:
            return

        # Find if there's a kill from wolves tonight
        wolf_kill = None
        for target_id, cause in game._pending_deaths:
            if cause == "killed":
                wolf_kill = target_id
                break

        if not wolf_kill:
            return

        # Ask Demon Wolf if they want to use their curse
        target_player = game.players.get(wolf_kill)
        if not target_player or not target_player.alive:
            return

        from ...engine.voting import VoteSession

        options = {
            1: f"Có, nguyền rủa {target_player.display_name()} thành sói",
            0: "Không, để họ chết bình thường",
        }

        vote = VoteSession(
            game.bot,
            game.channel,
            title="Sói Quỷ - Nguyền Rủa",
            description=f"Bạn có muốn biến {target_player.display_name()} thành sói thay vì giết họ? (Chỉ có 1 lần trong game)",
            options=options,
            eligible_voters=[player.user_id],
            duration=20,
            allow_skip=False,
        )
        result = await vote.start()

        if result.winning_target_id == 1:
            # Curse the victim - remove from pending deaths and mark for transformation
            game._pending_deaths.remove((wolf_kill, "killed"))
            
            # Mark for transformation
            game._demon_wolf_curse_target = wolf_kill
            
            self.curse_used = True
            
            await player.member.send(
                f"✓ Bạn đã sử dụng nguyền rủa trên {target_player.display_name()}! Họ sẽ trở thành Ma Sói thay vì chết."
            )
            
            await game.channel.send(
                f"🌙 Sói Quỷ đã nguyền rủa nạn nhân... {target_player.display_name()} sẽ trở thành sói!"
            )
