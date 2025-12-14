"""Angel of Death role - inherits target's role when they die."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from ..base import Alignment
from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")


@register_role
class AngelOfDeath(Role):
    metadata = RoleMetadata(
        name="Ảnh Tử",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm đầu tiên bạn chọn 1 người. Khi người đó chết, bạn sẽ lấy lá bài của họ và kế thừa tất cả khả năng của họ.",
        first_night_only=True,
        night_order=25,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/angel-of-death.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.target_id: int | None = None
        self.inherited_role: Role | None = None

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """On first night, Angel of Death chooses their target."""
        logger.info("Angel of Death on_night start | guild=%s angel=%s night=%s target=%s", game.guild.id, player.user_id, night_number, self.target_id)
        if night_number != 1 or self.target_id is not None:
            return
        
        # Get all other alive players as options
        options = {
            p.user_id: p.display_name()
            for p in game.alive_players()
            if p.user_id != player.user_id
        }
        
        if not options:
            logger.warning("No valid targets for Angel of Death | guild=%s angel=%s", game.guild.id, player.user_id)
            return
        
        choice = await game._prompt_dm_choice(
            player.member,
            title="Ảnh Tử - Chọn Mục Tiêu",
            description="Hãy chọn 1 người. Khi họ chết, bạn sẽ lấy lá bài của họ.",
            options=options,
            allow_skip=False,
            timeout=120,
        )
        
        if choice and choice in options:
            self.target_id = choice
            logger.info("Angel of Death selected target | guild=%s angel=%s target=%s", game.guild.id, player.user_id, choice)
            target = game.players.get(choice)
            if target:
                await game._safe_send_dm(
                    player.member,
                    content=f"Bạn đã chọn {target.display_name()} làm mục tiêu. Khi họ chết, bạn sẽ kế thừa vai trò của họ."
                )
        else:
            logger.warning("Angel of Death failed to select or skipped | guild=%s angel=%s", game.guild.id, player.user_id)

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When target dies, Angel of Death inherits their role."""
        logger.info("Angel of Death on_death triggered | guild=%s angel=%s cause=%s target=%s", game.guild.id, player.user_id, cause, self.target_id)
        if not self.target_id:
            logger.debug("Angel of Death has no target | guild=%s angel=%s", game.guild.id, player.user_id)
            return
        
        target = game.players.get(self.target_id)
        if not target or target.alive:
            logger.debug("Angel target still alive or not found | guild=%s angel=%s target=%s alive=%s", game.guild.id, player.user_id, self.target_id, target.alive if target else None)
            # Target is still alive, nothing happens
            return
        
        # Target is dead - Angel inherits their roles
        if target.roles:
            logger.info("Angel of Death inheriting target roles | guild=%s angel=%s target=%s roles=%s", game.guild.id, player.user_id, self.target_id, len(target.roles))
            
            # Copy all roles from target to Angel
            inherited_names = []
            for target_role in target.roles:
                # Deep copy the role to avoid shared mutable state (sets, lists, etc)
                try:
                    role_copy = copy.deepcopy(target_role)
                    logger.debug("Angel inherited role deep copied | guild=%s angel=%s role=%s", game.guild.id, player.user_id, target_role.metadata.name)
                except Exception as e:
                    logger.warning("Angel deepcopy failed, using fallback | guild=%s angel=%s role=%s error=%s", game.guild.id, player.user_id, target_role.metadata.name, str(e))
                    # Fallback to manual copy if deepcopy fails
                    role_copy = target_role.__class__()
                    if hasattr(target_role, '__dict__'):
                        for attr, value in target_role.__dict__.items():
                            if not attr.startswith('_'):
                                # For mutable objects, attempt deep copy
                                if isinstance(value, (list, set, dict)):
                                    setattr(role_copy, attr, copy.deepcopy(value))
                                else:
                                    setattr(role_copy, attr, value)
                
                player.roles.append(role_copy)
                inherited_names.append(target_role.metadata.name)
            
            # Update player's alignment to match target's primary alignment
            if target.roles:
                logger.info("Angel of Death inherited roles completed | guild=%s angel=%s target=%s inherited=%s", game.guild.id, player.user_id, self.target_id, ", ".join(inherited_names))
                
                # Notify Angel
                await game._safe_send_dm(
                    player.member,
                    content=f"Mục tiêu của bạn đã chết! Bạn đã kế thừa vai trò: {', '.join(inherited_names)}"
                )
                
                # If Angel became a werewolf, add them to wolf thread
                if any(r.alignment == Alignment.WEREWOLF for r in target.roles):
                    logger.info("Angel became werewolf, adding to wolf thread | guild=%s angel=%s", game.guild.id, player.user_id)
                    if game._wolf_thread:
                        try:
                            await game._add_to_wolf_thread(player)
                        except Exception as e:
                            logger.error("Failed to add Angel to wolf thread | guild=%s angel=%s error=%s", game.guild.id, player.user_id, str(e))
