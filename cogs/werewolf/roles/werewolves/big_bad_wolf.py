"""The Big Bad Wolf role - has an extra kill if certain roles haven't been eliminated."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger(__name__)


@register_role
class BigBadWolf(Role):
    """
    The Big Bad Wolf acts with other werewolves during night.
    If no Werewolf, Wild Child, or Wolf Hound has been eliminated,
    the Big Bad Wolf wakes up a second time alone and devours another victim.
    Cannot devour other werewolves.
    """

    metadata = RoleMetadata(
        name="Sói To Xấu Xa",
        alignment=Alignment.WEREWOLF,
        expansion=Expansion.THE_VILLAGE,
        description="Bạn là Sói To Xấu Xa. Mỗi đêm hãy phối hợp cùng đồng bọn để chọn con mồi. Nếu chưa có Sói nào bị loại, bạn sẽ thức dậy lần thứ 2 một mình để ăn một nạn nhân khác.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/werewolf/bigwolf.png",
        night_order=125,
        tags=("self_target",),
    )

    async def on_night(
        self,
        game: "WerewolfGame",
        player: "PlayerState",
        night_number: int,
    ) -> None:
        """Big Bad Wolf can make an extra kill if conditions are met."""
        # Check if any Werewolf, Wild Child, or Wolf Hound has been eliminated
        has_threat_died = self._has_threat_been_eliminated(game)

        if has_threat_died:
            # Cannot act alone if a threat has been eliminated
            logger.info(
                "Big Bad Wolf cannot act alone | guild=%s bbw=%s night=%s (threat eliminated)",
                game.guild.id,
                player.user_id,
                night_number,
            )
            return

        # Big Bad Wolf can make a second solo kill
        await self._make_solo_kill(game, player, night_number)

    def _has_threat_been_eliminated(self, game: "WerewolfGame") -> bool:
        """Check if any Werewolf, Wild Child, or Wolf Hound has been eliminated."""
        threat_roles = {"Ma Sói", "Tắc Kè Hoa", "Chó Sói"}

        # Check death log for any threat roles
        for player_id, cause, phase in game._death_log:
            player = game.players.get(player_id)
            if player and player.role and player.role.metadata.name in threat_roles:
                logger.info(
                    "Big Bad Wolf threat found | guild=%s threat=%s",
                    game.guild.id,
                    player.role.metadata.name,
                )
                return True

        return False

    async def _make_solo_kill(
        self,
        game: "WerewolfGame",
        player: "PlayerState",
        night_number: int,
    ) -> None:
        """Big Bad Wolf makes a solo kill."""
        # Get valid targets (alive, not werewolves)
        valid_targets = [
            p
            for p in game.alive_players()
            if p.user_id != player.user_id
            and p.roles
            and not any(r.alignment == Alignment.WEREWOLF for r in p.roles)
        ]

        if not valid_targets:
            logger.info(
                "Big Bad Wolf has no valid targets | guild=%s night=%s",
                game.guild.id,
                night_number,
            )
            return

        # Offer Big Bad Wolf a choice of targets
        options = {p.user_id: p.display_name() for p in valid_targets}

        from ...engine.voting import VoteSession

        vote = VoteSession(
            game.bot,
            game.channel,
            title=f"Sói To Xấu Xa - Nạn Nhân Thứ Hai (Đêm {night_number})",
            description="Chọn một nạn nhân khác (không phải Ma Sói).",
            options=options,
            eligible_voters=[player.user_id],
            duration=30,
            allow_skip=True,
        )
        result = await vote.start()

        if result.winning_target_id is None or result.is_tie:
            logger.info(
                "Big Bad Wolf skipped solo kill | guild=%s night=%s",
                game.guild.id,
                night_number,
            )
            return

        target_id = result.winning_target_id
        target = game.players.get(target_id)

        if not target or not target.alive:
            logger.warning(
                "Big Bad Wolf target invalid | guild=%s night=%s target=%s",
                game.guild.id,
                night_number,
                target_id,
            )
            return

        # Add to pending deaths with "big_bad_wolf" cause
        game._pending_deaths.append((target_id, "big_bad_wolf"))
        logger.info(
            "Big Bad Wolf solo kill | guild=%s night=%s target=%s",
            game.guild.id,
            night_number,
            target_id,
        )

        # Notify Big Bad Wolf
        try:
            await player.member.send(
                f"Bạn đã lựa chọn {target.display_name()} làm nạn nhân thứ hai của mình vào đêm {night_number}."
            )
        except Exception as e:
            logger.warning(
                "Failed to notify Big Bad Wolf | guild=%s bbw=%s error=%s",
                game.guild.id,
                player.user_id,
                str(e),
            )

    async def nightly_targets(
        self,
        game: "WerewolfGame",
        player: "PlayerState",
    ) -> Iterable["PlayerState"]:
        """Return valid targets for Big Bad Wolf's solo kill."""
        if self._has_threat_been_eliminated(game):
            return []

        # Valid targets: alive, not werewolves, not self
        return [
            p
            for p in game.alive_players()
            if p.user_id != player.user_id
            and p.roles
            and not any(r.alignment == Alignment.WEREWOLF for r in p.roles)
        ]
