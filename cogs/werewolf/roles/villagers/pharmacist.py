"""Pharmacist role - has sleeping potion and antidote."""

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
class Pharmacist(Role):
    metadata = RoleMetadata(
        name="Dược Sĩ",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Bạn có 2 bình: Bình thuốc mê (mất quyền biểu quyết & nói chuyện trong 1 ngày) và Bình hồi phục (cứu người bị Phù thủy giết). Mỗi bình dùng 1 lần.",
        night_order=77,  # Before Witch (80) to have effect before witch poison resolves
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/pharmacist.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.antidote_available = True
        self.sleeping_potion_available = True
        self.last_slept_target: int | None = None
        self.last_antidote_target: int | None = None

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, Pharmacist chooses which potion to use."""
        logger.info(
            "Pharmacist on_night start | guild=%s pharmacist=%s night=%s antidote=%s sleeping=%s",
            game.guild.id, player.user_id, night_number, self.antidote_available, self.sleeping_potion_available
        )
        
        if not self.antidote_available and not self.sleeping_potion_available:
            logger.info("Pharmacist has no potions left | guild=%s pharmacist=%s", game.guild.id, player.user_id)
            return
        
        # First, ask which potion to use
        potion_choices = {}
        if self.antidote_available:
            potion_choices[1] = "🩺 Bình Hồi Phục (cứu người bị Phù thủy giết)"
        if self.sleeping_potion_available:
            potion_choices[2] = "💤 Bình Thuốc Mê (mất quyền biểu quyết & nói chuyện 1 ngày)"
        
        if not potion_choices:
            return
        
        potion_choice = await game._prompt_dm_choice(
            player.member,
            title="Dược Sĩ - Chọn Bình Thuốc",
            description="Chọn bình thuốc nào để sử dụng đêm nay?",
            options=potion_choices,
            allow_skip=True,
            timeout=120,
        )
        
        if potion_choice not in potion_choices:
            logger.info("Pharmacist skipped potion choice | guild=%s pharmacist=%s", game.guild.id, player.user_id)
            return
        
        # Get all alive players as targets
        targets = {
            p.user_id: p.display_name()
            for p in game.alive_players()
            if p.user_id != player.user_id
        }
        
        if not targets:
            logger.warning("No valid targets for Pharmacist | guild=%s pharmacist=%s", game.guild.id, player.user_id)
            return
        
        if potion_choice == 1:
            # Antidote
            logger.info("Pharmacist using antidote | guild=%s pharmacist=%s", game.guild.id, player.user_id)
            target_id = await game._prompt_dm_choice(
                player.member,
                title="Dược Sĩ - Chọn Mục Tiêu Hồi Phục",
                description="Chọn 1 người để sử dụng Bình Hồi Phục. Nếu họ bị Phù thủy giết đêm nay, họ sẽ được cứu.",
                options=targets,
                allow_skip=False,
                timeout=120,
            )
            
            if target_id and target_id in targets:
                self.antidote_available = False
                self.last_antidote_target = target_id
                game._pharmacist_antidote_target = target_id  # pylint: disable=protected-access
                logger.info("Pharmacist set antidote target | guild=%s pharmacist=%s target=%s", game.guild.id, player.user_id, target_id)
                
                target = game.players.get(target_id)
                if target:
                    await game._safe_send_dm(
                        player.member,
                        content=f"Bạn đã chọn {target.display_name()} làm mục tiêu cho Bình Hồi Phục. Nếu họ bị Phù thủy giết đêm nay, họ sẽ sống sót."
                    )
                    await game._safe_send_dm(
                        target.member,
                        content="Dược Sĩ đã tập trung Bình Hồi Phục lên bạn. Nếu bị Phù thủy giết đêm nay, bạn sẽ được cứu!"
                    )
        
        elif potion_choice == 2:
            # Sleeping Potion
            logger.info("Pharmacist using sleeping potion | guild=%s pharmacist=%s", game.guild.id, player.user_id)
            target_id = await game._prompt_dm_choice(
                player.member,
                title="Dược Sĩ - Chọn Mục Tiêu Thuốc Mê",
                description="Chọn 1 người để sử dụng Bình Thuốc Mê. Họ sẽ mất quyền biểu quyết và không được nói chuyện ngày mai.",
                options=targets,
                allow_skip=False,
                timeout=120,
            )
            
            if target_id and target_id in targets:
                self.sleeping_potion_available = False
                self.last_slept_target = target_id
                game._pharmacist_slept_target = target_id  # pylint: disable=protected-access
                logger.info("Pharmacist set sleeping target | guild=%s pharmacist=%s target=%s", game.guild.id, player.user_id, target_id)
                
                target = game.players.get(target_id)
                if target:
                    # Disable their voting ability
                    target.vote_disabled = True
                    
                    await game._safe_send_dm(
                        player.member,
                        content=f"Bạn đã chọn {target.display_name()} làm mục tiêu cho Bình Thuốc Mê. Họ sẽ mất quyền biểu quyết và không thể nói chuyện ngày mai."
                    )
                    await game._safe_send_dm(
                        target.member,
                        content="💤 Bạn đã bị Dược Sĩ làm cho mê ngủ! Bạn sẽ mất quyền biểu quyết và không được nói chuyện suốt ngày mai."
                    )
