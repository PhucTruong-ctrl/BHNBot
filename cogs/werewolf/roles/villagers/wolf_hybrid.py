"""Wolf Hybrid role - can choose to become werewolf or stay as villager."""

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
class WolfHybrid(Role):
    metadata = RoleMetadata(
        name="Sói Lai",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm đầu tiên bạn chọn trở thành Ma Sói hoặc ở lại làng. Nếu chọn trở thành sói, bạn sẽ gia nhập bầy sói.",
        first_night_only=True,
        night_order=3,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/wolf-hound.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.choice_made = False

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """On first night, Wolf Hybrid chooses to become werewolf or stay as villager."""
        if night_number != 1 or self.choice_made:
            return

        self.choice_made = True
        
        # Present choice to player
        options = {
            1: "Trở thành Ma Sói",
            2: "Ở lại làng",
        }
        
        result = await game._prompt_dm_choice(
            player,
            title="Sói Lai - Chọn Bên",
            description="Chọn bạn muốn trở thành Ma Sói hay ở lại làng?",
            options=options,
            allow_skip=False,
        )
        
        if result is None:
            return
        
        if result == 1:
            # Change to werewolf (add werewolf role alongside hybrid)
            from ..werewolves.werewolf import Werewolf
            
            werewolf_role = Werewolf()
            player.add_role(werewolf_role)
            await werewolf_role.on_assign(game, player)
            
            # Add to wolf thread if it exists
            if game._wolf_thread:
                try:
                    await game._wolf_thread.add_user(player.member)
                    # Notify other wolves
                    wolf_players = [p for p in game.players.values() 
                                   if p.alive and any(r.alignment == Alignment.WEREWOLF for r in p.roles) and p.user_id != player.user_id]
                    wolf_mention = " ".join(p.member.mention for p in wolf_players)
                    if wolf_mention:
                        await game._wolf_thread.send(f"{wolf_mention} - {player.display_name()} đã gia nhập bầy sói!")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
            
            try:
                await player.member.send(f"Bạn đã chọn trở thành Ma Sói!")
            except Exception:
                pass
        else:
            # Stay as villager (no change needed)
            try:
                await player.member.send(f"Bạn đã chọn ở lại làng!")
            except Exception:
                pass