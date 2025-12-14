"""Hunter role implementation."""

from __future__ import annotations

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata


@register_role
class Hunter(Role):
    metadata = RoleMetadata(
        name="Thợ Săn",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Nếu bạn chết, bạn được quyền kéo theo một người khác cùng chết.",
        card_image_url="https://static.wikia.nocookie.net/allthetropes/images/5/5c/Chasseur_1773.jpg/revision/latest?cb=20240925085527",
    )

    async def on_death(self, game, player, cause: str) -> None:  # type: ignore[override]
        choices = {p.user_id: p.display_name() for p in game.alive_players() if p.user_id != player.user_id}
        if not choices:
            return
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Thợ săn trả thù",
            description="Chọn một người để bắn trước khi gục ngã.",
            options=choices,
            allow_skip=True,
        )
        if target_id and target_id in choices:
            game._pending_deaths.append((target_id, "hunter"))  # pylint: disable=protected-access
