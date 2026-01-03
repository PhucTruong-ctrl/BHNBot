"""Pyromaniac role."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")


@register_role
class Pyromaniac(Role):
    metadata = RoleMetadata(
        name="Kẻ Phóng Hỏa",
        alignment=Alignment.NEUTRAL,
        expansion=Expansion.THE_VILLAGE,
        description="Mỗi đêm bạn có thể tưới dầu cho tới 2 người chơi, hoặc đốt tất cả những người đã bị tưới dầu. Người chơi sẽ biết nếu họ bị tưới dầu. Tối đa 6 người có thể bị tưới dầu.",
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/neutral/pyro.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.oil_targets_tonight: list[int] = []  # Players targeted for oiling tonight

    async def on_assign(self, game: WerewolfGame, player: PlayerState) -> None:
        """Register pyromaniac in game state."""
        game._pyro_id = player.user_id
        await player.send_dm(
            embed=discord.Embed(
                title="🔥 Kẻ Phóng Hỏa",
                description=self.metadata.description,
                color=discord.Color.orange(),
            )
        )

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Allow pyromaniac to soak or ignite on each night."""
        if not player.alive:
            return

        # Reset tonight's targets
        self.oil_targets_tonight = []

        # Show current soaked players only to pyromaniac
        soaked_text = (
            f"Hiện tại đã tưới dầu: {len(game._pyro_soaked)}/6\n"
            f"Người: {', '.join(p.display_name() for p in game.alive_players() if p.user_id in game._pyro_soaked)}"
            if game._pyro_soaked
            else "Hiện tại chưa ai bị tưới dầu"
        )

        options = {
            1: "🛢️ Tưới dầu (tối đa 2 người)",
            2: "🔥 Đốt tất cả người đã tưới" if game._pyro_soaked else "❌ Đốt (không ai bị tưới)",
        }

        choice = await game._prompt_dm_choice(
            player,
            title="Kẻ Phóng Hỏa",
            description="Chọn hành động cho đêm nay",
            options=options,
            allow_skip=True,
            timeout=60,
        )

        if choice == 1:
            await self._soak_oil(game, player)
        elif choice == 2 and game._pyro_soaked:
            await self._ignite_all(game, player)
        else:
            await player.send_dm("Bạn quyết định không làm gì đêm nay.")

    async def _soak_oil(self, game: WerewolfGame, player: PlayerState) -> None:
        """Allow pyromaniac to soak up to 2 players in oil."""
        if len(game._pyro_soaked) >= 6:
            await player.send_dm("⚠️ Đã đạt tối đa 6 người bị tưới dầu. Bạn phải đốt trước khi tưới thêm.")
            return

        alive_players = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not alive_players:
            await player.send_dm("Không còn ai để tưới dầu.")
            return

        options = {p.user_id: p.display_name() for p in alive_players}

        # First soak
        target1_id = await game._prompt_dm_choice(
            player,
            title="🛢️ Tưới dầu - Người thứ nhất",
            description="Chọn người thứ nhất để tưới dầu",
            options=options,
            allow_skip=True,
            timeout=45,
        )

        if not target1_id:
            await player.send_dm("Bạn quyết định không tưới dầu đêm nay.")
            return

        self.oil_targets_tonight.append(target1_id)

        # Optional second soak
        remaining = [p for p in alive_players if p.user_id != target1_id]
        if remaining:
            options2 = {p.user_id: p.display_name() for p in remaining}

            target2_id = await game._prompt_dm_choice(
                player,
                title="🛢️ Tưới dầu - Người thứ hai (tùy chọn)",
                description="Chọn người thứ hai để tưới dầu, hoặc bỏ qua",
                options=options2,
                allow_skip=True,
                timeout=45,
            )

            if target2_id:
                self.oil_targets_tonight.append(target2_id)

        # Add to soaked set (max 6 total)
        new_soaked = set(self.oil_targets_tonight)
        game._pyro_soaked.update(new_soaked)
        game._pyro_soaked = set(list(game._pyro_soaked)[:6])  # Cap at 6

        # Notify soaked players (they can see they're soaked, but not others)
        for target_id in self.oil_targets_tonight:
            target = game.players[target_id]
            if target.alive:
                await target.send_dm(
                    embed=discord.Embed(
                        title="⚠️ Bạn bị tưới dầu!",
                        description="Một người nào đó đã tưới dầu cho bạn. Nếu họ quyết định đốt, bạn sẽ chết.",
                        color=discord.Color.red(),
                    )
                )

        embed = discord.Embed(
            title="✅ Tưới dầu hoàn tất",
            description=f"Bạn đã tưới dầu cho: {', '.join(game.players[tid].display_name() for tid in self.oil_targets_tonight)}",
            color=discord.Color.orange(),
        )
        await player.send_dm(embed=embed)

        logger.info(
            "Pyromaniac soaked | guild=%s players=%s total_soaked=%s",
            game.guild.id,
            [game.players[tid].user_id for tid in self.oil_targets_tonight],
            len(game._pyro_soaked),
        )

    async def _ignite_all(self, game: WerewolfGame, player: PlayerState) -> None:
        """Ignite all soaked players."""
        if not game._pyro_soaked:
            await player.send_dm("Không có ai bị tưới dầu để đốt.")
            return

        # Confirm ignition
        soaked_names = ", ".join(game.players[pid].display_name() for pid in game._pyro_soaked if pid in game.players)

        confirm = await game._prompt_dm_choice(
            player,
            title="🔥 Xác nhận",
            description=f"Bạn sẽ đốt {len(game._pyro_soaked)} người: {soaked_names}. Xác nhận?",
            options={1: "✅ Đốt", 2: "❌ Hủy bỏ"},
            allow_skip=False,
            timeout=30,
        )

        if confirm != 1:
            await player.send_dm("Bạn quyết định không đốt đêm nay.")
            return

        # Kill all soaked players
        for target_id in game._pyro_soaked:
            if target_id in game.players and game.players[target_id].alive:
                game._pending_deaths.append((target_id, "pyro"))

        killed_count = len(game._pyro_soaked)
        game._pyro_soaked.clear()

        # Track arsonist burns for achievement
        player.arsonist_burns = max(player.arsonist_burns, killed_count)

        embed = discord.Embed(
            title="🔥 Đốt hoàn tất",
            description=f"Bạn đã đốt {killed_count} người.",
            color=discord.Color.red(),
        )
        await player.send_dm(embed=embed)

        logger.info(
            "Pyromaniac ignited | guild=%s killed=%s",
            game.guild.id,
            killed_count,
        )
