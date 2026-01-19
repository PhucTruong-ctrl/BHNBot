"""Wild Child role - starts as villager, becomes werewolf when chosen person dies."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_villagers_wild_")


@register_role
class WildChild(Role):
    metadata = RoleMetadata(
        name="Đứa Con Hoang",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm đầu tiên bạn chọn 1 người. Khi người đó chết, bạn sẽ hoá thành Ma Sói và dậy cùng bầy sói mỗi đêm.",
        first_night_only=True,
        night_order=70,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/wild-child.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.chosen_one_id: int | None = None
        self.transformed = False

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """On first night, Wild Child chooses someone to become their parent."""
        if night_number != 1 or self.chosen_one_id is not None:
            return

        # Present choice to player
        choices = {p.user_id: p.display_name() for p in game.alive_players() if p.user_id != player.user_id}
        if not choices:
            return

        result = await game._prompt_dm_choice(
            player,
            title="Đứa Con Hoang - Chọn Bố/Mẹ",
            description="Chọn 1 người để trở thành bố/mẹ của bạn. Khi người đó chết, bạn sẽ hoá sói.",
            options=choices,
            allow_skip=False,
        )

        if result is not None:
            self.chosen_one_id = result
            chosen_name = choices.get(result, "Không xác định")
            try:
                await player.member.send(f"Bạn đã chọn {chosen_name} làm bố/mẹ của mình.")
            except Exception:
                pass

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When chosen one dies, Wild Child transforms into a werewolf."""
        if self.transformed or self.chosen_one_id is None:
            return

        # Check if the chosen one is the one who died
        dead_player_id = player.user_id  # This is the wild child who is checking
        
        # We need to check if chosen_one died - this method is called for all players
        # So we need to listen for when chosen_one dies
        # Actually, this won't work this way...
        # We need a different approach - check in game loop when someone dies

    async def check_transformation(self, game: WerewolfGame, player: PlayerState, dead_player_id: int) -> None:
        """Called when checking if wild child should transform (someone died)."""
        if self.transformed or self.chosen_one_id is None or player.user_id != self.chosen_one_id:
            return
        if dead_player_id == self.chosen_one_id and player.alive:
            # The chosen one died, transform this wild child
            self.transformed = True

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
                        await game._wolf_thread.send(f"{wolf_mention} - {player.display_name()} đã trở thành Ma Sói! Bố/mẹ của bạn đã chết.")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")

            try:
                await player.member.send(f"Bố/mẹ của bạn đã chết. Bạn đã hoá thành Ma Sói!")
            except Exception:
                pass