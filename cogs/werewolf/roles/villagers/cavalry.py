"""Cavalry role - can identify a werewolf during day phase."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_villagers_caval")


@register_role
class Cavalry(Role):
    metadata = RoleMetadata(
        name="Kỵ Sĩ",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Một lần vào ngày, trước khi treo cổ, bạn lật 1 lá bài lên và chọn một người. Quản trò thông báo đó có phải Ma Sói không. Nếu phải, sói đó chết và ngày kết thúc. Nếu không, bạn chết.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/cavalry.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.has_used_ability: bool = False  # Track if ability was used
        self.identified_target: Optional[int] = None  # Track who was identified

    async def on_day(self, game: WerewolfGame, player: PlayerState, day_number: int) -> None:
        """Handle Cavalry's day ability - identify a werewolf before lynch vote."""
        if not player.alive or self.has_used_ability:
            return

        logger.info(
            "Cavalry day ability available | guild=%s player=%s day=%s",
            game.guild.id,
            player.user_id,
            day_number,
        )

        # Get all alive players except the cavalry
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            logger.warning("No candidates for cavalry to identify | guild=%s", game.guild.id)
            return

        # Ask cavalry to choose a target
        target_options = {p.user_id: p.display_name() for p in candidates}
        choice = await game._prompt_dm_choice(
            player,
            title="Kỵ Sĩ - Lật Lá Bài & Xác Định",
            description=f"Ngày {day_number}: Chọn một người để lật lá bài của họ. Quản trò sẽ thông báo họ có phải Ma Sói không.",
            options=target_options,
            allow_skip=True,
            timeout=60,
        )

        if not choice or choice not in target_options:
            logger.info("Cavalry skipped ability | guild=%s player=%s", game.guild.id, player.user_id)
            return

        target = game.players.get(choice)
        if not target or not target.alive:
            logger.warning("Cavalry target invalid | guild=%s choice=%s", game.guild.id, choice)
            return

        # Mark ability as used
        self.has_used_ability = True
        self.identified_target = choice

        # Check if target is a werewolf
        is_werewolf = any(r.alignment == Alignment.WEREWOLF for r in target.roles)
        role_names = ", ".join(r.metadata.name for r in target.roles)

        # Announce the reveal
        announcement = f"🗡️ **Kỵ Sĩ lật lá bài của {target.display_name()}!**\n"
        if is_werewolf:
            announcement += f"❌ **{target.display_name()} là Ma Sói ({role_names})!** Sói đó chết, ngày kết thúc ngay lập tức."
            logger.info(
                "Cavalry identified werewolf | guild=%s cavalry=%s target=%s role=%s",
                game.guild.id,
                player.user_id,
                target.user_id,
                role_names,
            )
        else:
            announcement += f"✅ **{target.display_name()} không phải Ma Sói (là {role_names})!** Kỵ Sĩ chết, trò chơi tiếp tục."
            logger.info(
                "Cavalry identified villager | guild=%s cavalry=%s target=%s role=%s",
                game.guild.id,
                player.user_id,
                target.user_id,
                role_names,
            )

        await game.channel.send(announcement)

        # Handle the outcome
        if is_werewolf:
            # Werewolf dies and day ends
            target.alive = False
            await game._handle_death(target, cause="cavalry_identify")
            await game._resolve_pending_deaths("cavalry_identify")
            logger.info("Werewolf killed by cavalry | guild=%s target=%s", game.guild.id, target.user_id)
        else:
            # Cavalry dies and game continues
            player.alive = False
            await game._handle_death(player, cause="cavalry_ability")
            await game._resolve_pending_deaths("cavalry_ability")
            logger.info("Cavalry died from ability | guild=%s player=%s", game.guild.id, player.user_id)
