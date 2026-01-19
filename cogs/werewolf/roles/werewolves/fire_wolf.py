"""Fire Wolf role - disables target's abilities when wolves die."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_werewolves_fire")


@register_role
class FireWolf(Role):
    metadata = RoleMetadata(
        name="Sói Lửa",
        alignment=Alignment.WEREWOLF,
        expansion=Expansion.THE_VILLAGE,
        description="Khi sói bị giết, vào ban đêm hôm sau bạn có thể chọn 1 người mất kỹ năng vĩnh viễn. Khi có ít nhất 2 sói chết cùng 1 ngày, bạn được dùng kỹ năng thêm 1 lần nữa.",
        night_order=85,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/werewolf/fire-wolf.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.has_used_ability_first: bool = False  # Lần 1: Khi sói chết
        self.has_used_ability_second: bool = False  # Lần 2: Khi 2+ sói chết cùng ngày
        self.targets_disabled: list[int] = []  # Track những người bị mất kỹ năng

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Fire Wolf's ability - disable target's skills."""
        # Check if ability should trigger
        should_use = False
        use_count = 0

        # Lần 1: Sói chết lần đầu (has_used_ability_first=False)
        if not self.has_used_ability_first and getattr(player, "_fire_wolf_trigger_first", False):
            should_use = True
            use_count = 1
            self.has_used_ability_first = True
            delattr(player, "_fire_wolf_trigger_first")
            logger.info(
                "Fire Wolf ability triggered (first wolf death) | guild=%s player=%s night=%s",
                game.guild.id,
                player.user_id,
                night_number,
            )

        # Lần 2: 2+ sói chết cùng ngày (can_use_again=True)
        if self.can_use_again and not self.has_used_ability_second:
            should_use = True
            use_count = 2
            self.has_used_ability_second = True
            self.can_use_again = False
            logger.info(
                "Fire Wolf ability triggered (2+ wolves died same day) | guild=%s player=%s night=%s",
                game.guild.id,
                player.user_id,
                night_number,
            )

        if not should_use or not player.alive:
            return

        # Get all alive villagers (not werewolves) as candidates
        candidates = [
            p for p in game.alive_players()
            if p.user_id != player.user_id
            and not any(r.alignment == Alignment.WEREWOLF for r in p.roles)
        ]

        if not candidates:
            logger.warning("No candidates for Fire Wolf to disable | guild=%s", game.guild.id)
            await player.member.send("❌ Không có mục tiêu nào để vô hiệu hóa kỹ năng.")
            return

        # Ask fire wolf to choose a target
        target_options = {p.user_id: p.display_name() for p in candidates}
        choice = await game._prompt_dm_choice(
            player,
            title="Sói Lửa - Vô Hiệu Hóa Kỹ Năng",
            description=f"Lần dùng thứ {use_count}: Chọn 1 người để vô hiệu hóa kỹ năng vĩnh viễn.",
            options=target_options,
            allow_skip=True,
            timeout=60,
        )

        if not choice or choice not in target_options:
            logger.info("Fire Wolf skipped ability | guild=%s player=%s night=%s", game.guild.id, player.user_id, night_number)
            await player.member.send("Bạn đã bỏ qua kỹ năng lần này.")
            return

        target = game.players.get(choice)
        if not target or not target.alive:
            logger.warning("Fire Wolf target invalid | guild=%s choice=%s", game.guild.id, choice)
            return

        # Mark target as skills disabled
        self.targets_disabled.append(choice)
        target.skills_disabled = True

        # Announce to wolves only (internal)
        wolves = [p for p in game.alive_players() if any(r.alignment == Alignment.WEREWOLF for r in p.roles)]
        target_name = target.display_name()
        role_names = ", ".join(r.metadata.name for r in target.roles)

        announcement = f"🔥 **Sói Lửa vô hiệu hóa kỹ năng của {target_name} ({role_names}) vĩnh viễn!**"
        if hasattr(game, "_wolf_thread") and game._wolf_thread:
            await game._wolf_thread.send(announcement)
        else:
            await game.channel.send(announcement)

        logger.info(
            "Fire Wolf disabled target's skills | guild=%s fire_wolf=%s target=%s role=%s",
            game.guild.id,
            player.user_id,
            target.user_id,
            role_names,
        )
