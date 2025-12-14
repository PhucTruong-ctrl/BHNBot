"""Angel of Death role - inherits target's role when they die."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState


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
        if night_number != 1 or self.target_id is not None:
            return
        
        # Get all other alive players as options
        options = {
            p.user_id: p.display_name()
            for p in game.alive_players()
            if p.user_id != player.user_id
        }
        
        if not options:
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
            target = game.players.get(choice)
            if target:
                await game._safe_send_dm(
                    player.member,
                    content=f"Bạn đã chọn {target.display_name()} làm mục tiêu. Khi họ chết, bạn sẽ kế thừa vai trò của họ."
                )

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When target dies, Angel of Death inherits their role."""
        if not self.target_id:
            return
        
        target = game.players.get(self.target_id)
        if not target or target.alive:
            # Target is still alive, nothing happens
            return
        
        # Target is dead - Angel inherits their roles
        if target.roles:
            # CRITICAL FIX: Use deep copy to avoid sharing mutable state
            import copy
            
            # Copy all roles from target to Angel
            for target_role in target.roles:
                # Deep copy the role to avoid shared mutable state (sets, lists, etc)
                try:
                    role_copy = copy.deepcopy(target_role)
                except Exception:
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
            
            # Update player's alignment to match target's primary alignment
            if target.roles:
                player_alignment = target.roles[0].alignment
                game_logger = __import__('logging').getLogger('werewolf')
                game_logger.info(
                    "Angel of Death inherited role | guild=%s angel=%s target=%s inherited_role=%s",
                    game.guild.id, player.user_id, self.target_id,
                    ", ".join(r.metadata.name for r in target.roles)
                )
                
                # Notify Angel and other players if needed
                await game._safe_send_dm(
                    player.member,
                    content=f"Mục tiêu của bạn đã chết! Bạn đã kế thừa vai trò: {', '.join(r.metadata.name for r in target.roles)}"
                )
                
                # If Angel became a werewolf, add them to wolf thread
                if any(r.alignment == game.players[self.target_id].roles[0].alignment == Alignment.WEREWOLF for r in target.roles):
                    if game._wolf_thread:
                        try:
                            await game._add_to_wolf_thread(player)
                        except Exception as e:
                            game_logger.error(
                                "Failed to add Angel to wolf thread | guild=%s angel=%s error=%s",
                                game.guild.id, player.user_id, str(e)
                            )
