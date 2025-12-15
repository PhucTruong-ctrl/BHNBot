"""Bear Tamer role - detects werewolves among neighbors each morning."""

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
class BearTamer(Role):
    metadata = RoleMetadata(
        name="Thần Gấu",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi buổi sáng, nếu 2 người kế bên bạn (không tính người chết) có Ma Sói, quản trò sẽ thông báo cho mọi người biết.",
        night_order=None,  # Not a night role
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/bear-tamer.png",
    )

    async def on_day(self, game: WerewolfGame, player: PlayerState, day_number: int) -> None:  # type: ignore[override]
        """Each day morning, check if neighbors contain werewolves."""
        if not player.alive or not player.roles:
            return
        
        logger.info("BearTamer on_day start | guild=%s bear_tamer=%s day=%s", 
                   game.guild.id, player.user_id, day_number)
        
        try:
            # Get all alive players
            alive = game.alive_players()
            if len(alive) < 3:  # Need at least 3 players to have neighbors
                logger.info("BearTamer: Not enough alive players | guild=%s bear_tamer=%s alive=%s", 
                           game.guild.id, player.user_id, len(alive))
                return
            
            # Find Bear Tamer's position in alive players list
            bear_tamer_idx = None
            for idx, p in enumerate(alive):
                if p.user_id == player.user_id:
                    bear_tamer_idx = idx
                    break
            
            if bear_tamer_idx is None:
                logger.warning("BearTamer not found in alive list | guild=%s bear_tamer=%s", 
                             game.guild.id, player.user_id)
                return
            
            # Get left and right neighbors (circular)
            left_idx = (bear_tamer_idx - 1) % len(alive)
            right_idx = (bear_tamer_idx + 1) % len(alive)
            
            left_neighbor = alive[left_idx]
            right_neighbor = alive[right_idx]
            
            # Check if either neighbor is a werewolf
            left_is_werewolf = any(r.alignment == Alignment.WEREWOLF for r in left_neighbor.roles)
            right_is_werewolf = any(r.alignment == Alignment.WEREWOLF for r in right_neighbor.roles)
            
            has_werewolf = left_is_werewolf or right_is_werewolf
            
            logger.info("BearTamer check | guild=%s bear_tamer=%s day=%s left=%s(%s) right=%s(%s) has_werewolf=%s",
                       game.guild.id, player.user_id, day_number,
                       left_neighbor.user_id, left_neighbor.display_name(),
                       right_neighbor.user_id, right_neighbor.display_name(),
                       has_werewolf)
            
            if has_werewolf:
                # Build announcement message
                neighbors_info = []
                if left_is_werewolf:
                    neighbors_info.append(f"🐺 **{left_neighbor.display_name()}** (bên trái)")
                if right_is_werewolf:
                    neighbors_info.append(f"🐺 **{right_neighbor.display_name()}** (bên phải)")
                
                neighbors_text = " và ".join(neighbors_info)
                
                # Announce to the game channel
                import discord
                embed = discord.Embed(
                    title="🐻 **Thần Gấu - Phát Hiện Sói**",
                    description=f"Thần Gấu phát hiện có Ma Sói kế bên!",
                    colour=discord.Colour.brown(),
                )
                embed.add_field(
                    name="⚠️ **Cảnh Báo**",
                    value=f"Một trong 2 người kế bên Thần Gấu là Ma Sói:\n{neighbors_text}",
                    inline=False
                )
                embed.set_footer(text=f"Ngày {day_number}")
                
                await game.channel.send(embed=embed)
                
                logger.info("BearTamer announced werewolf neighbors | guild=%s bear_tamer=%s day=%s neighbors=%s",
                           game.guild.id, player.user_id, day_number, neighbors_info)
            else:
                logger.info("BearTamer found no werewolves | guild=%s bear_tamer=%s day=%s", 
                           game.guild.id, player.user_id, day_number)
        
        except Exception as e:
            logger.error("Error in BearTamer on_day | guild=%s bear_tamer=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)
