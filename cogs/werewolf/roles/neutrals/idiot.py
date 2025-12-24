"""Idiot role from New Moon."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState


@register_role
class Idiot(Role):
    metadata = RoleMetadata(
        name="Thằng Ngốc",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.NEW_MOON,
        description="Nếu bị dân làng treo cổ, bạn lộ bài và sống sót, thắng cuộc. (Ngoại lệ: Nếu bạn là người cuối cùng sống, Dân vẫn thắng).",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/neutral/idiot.png",
    )

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """Idiot wins if lynched, unless they are the last player alive."""
        if cause == "lynch":
            # Check if idiot is the last player alive
            alive = game.alive_players()
            if len(alive) == 1 and alive[0].user_id == player.user_id:
                # Idiot is last alive - Village wins instead
                return
            
            # DRAMATIC FOOL REVEAL
            try:
                await game.text_channel.send(
                    f"🤡 **PLOT TWIST!!!**\\n\\n"
                    f"😂 **{player.display_name()} là HỀ (FOOL)!**\\n"
                    f"_Họ cười điên cuồng... Mọi người đã bị lừa! Hề đã THẮNG!_\\n\\n"
                    f"🎭 **GAME KẾT THÚC** - Fool chiến thắng!"
                )
            except Exception:
                pass
            
            # Idiot wins
            game._idiot_won = True  # pylint: disable=protected-access
