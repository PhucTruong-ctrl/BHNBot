"""Elder Man role - divides village into 2 groups and wins when opposing group is eliminated."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")


@register_role
class ElderMan(Role):
    metadata = RoleMetadata(
        name="Bô Lão",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm đầu tiên, quản trò chia làng thành 2 nhóm bằng nhau và công bố bô lão ở nhóm nào. Bô lão thắng khi nhóm còn lại (không phải nhóm của bô lão) bị giết hết toàn bộ.",
        first_night_only=True,
        night_order=2,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/neutral/elder-man.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.group_number: Optional[int] = None  # 1 or 2

    async def on_assign(self, game: WerewolfGame, player: PlayerState) -> None:  # type: ignore[override]
        """On assign, divide village into 2 equal groups and announce."""
        logger.info("ElderMan assigned | guild=%s elder_man=%s", game.guild.id, player.user_id)
        
        try:
            # Store Elder Man ID in game state
            game._elder_man_id = player.user_id  # pylint: disable=protected-access
            
            # Get all players
            all_players = list(game.players.values())
            player_count = len(all_players)
            
            # Shuffle and split into 2 groups
            random.shuffle(all_players)
            mid = player_count // 2
            
            group1 = all_players[:mid]
            group2 = all_players[mid:]
            
            # Store groups in game state
            game._elder_man_group1 = [p.user_id for p in group1]  # pylint: disable=protected-access
            game._elder_man_group2 = [p.user_id for p in group2]  # pylint: disable=protected-access
            
            # Determine which group Elder Man is in
            if player.user_id in game._elder_man_group1:  # pylint: disable=protected-access
                self.group_number = 1
                opposing_group = 2
                opposing_players = group2
            else:
                self.group_number = 2
                opposing_group = 1
                opposing_players = group1
            
            # Build group display text
            group1_names = ", ".join(p.display_name() for p in group1)
            group2_names = ", ".join(p.display_name() for p in group2)
            
            logger.info("ElderMan groups divided | guild=%s elder_man=%s group1=%s group2=%s", 
                       game.guild.id, player.user_id, 
                       [p.user_id for p in group1], 
                       [p.user_id for p in group2])
            
            # Announce to the game channel
            import discord
            embed = discord.Embed(
                title="👴 **Bô Lão - Chia Nhóm**",
                description="Làng đã được chia thành 2 nhóm bằng nhau. Bô Lão ở một trong 2 nhóm này.",
                colour=discord.Colour.orange(),
            )
            embed.add_field(name="🟦 **Nhóm 1**", value=group1_names, inline=False)
            embed.add_field(name="🟥 **Nhóm 2**", value=group2_names, inline=False)
            embed.add_field(
                name="📢 **Công Bố**",
                value=f"Bô Lão ở **Nhóm {self.group_number}**\n\nBô Lão thắng khi nhóm còn lại (Nhóm {opposing_group}) bị giết hết toàn bộ.",
                inline=False
            )
            embed.set_footer(text="Mọi người có thể sử dụng thông tin này để đưa ra quyết định chiến lược.")
            
            await game.channel.send(embed=embed)
            
            # Notify Elder Man specifically
            await game._safe_send_dm(player.member,  # pylint: disable=protected-access
                f"👴 **Bô Lão - Thông Tin Nhóm**\n\n"
                f"Bạn ở **Nhóm {self.group_number}**\n\n"
                f"Các thành viên khác của bạn:\n"
                f"{', '.join(p.display_name() for p in (group1 if self.group_number == 1 else group2) if p.user_id != player.user_id)}\n\n"
                f"Để thắng, bạn cần làm cho tất cả các thành viên của **Nhóm {opposing_group}** bị chết.")
            
        except Exception as e:
            logger.error("Error in ElderMan on_assign | guild=%s elder_man=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """Elder Man death - check if win condition still possible."""
        logger.info("ElderMan died | guild=%s elder_man=%s cause=%s", 
                   game.guild.id, player.user_id, cause)
