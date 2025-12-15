"""Actor role - randomly uses one of 3 randomly selected abilities each night."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")

# Available abilities the actor can randomly select from
ACTOR_ABILITIES = {
    1: {
        "name": "Tiên Tri",
        "description": "Xem danh tính của 1 người",
        "emoji": "🔮",
    },
    2: {
        "name": "Bảo Vệ",
        "description": "Bảo vệ 1 người khỏi Ma Sói",
        "emoji": "🛡️",
    },
    3: {
        "name": "Phù Thủy Chữa",
        "description": "Cứu sống 1 người bị Ma Sói cắn",
        "emoji": "🧪",
    },
    4: {
        "name": "Phù Thủy Giết",
        "description": "Giết 1 người",
        "emoji": "💀",
    },
    5: {
        "name": "Thợ Săn",
        "description": "Chọn mục tiêu để bắn nếu bị giết",
        "emoji": "🏹",
    },
    6: {
        "name": "Con Quạ",
        "description": "Nguyền rủa 1 người (cộng +2 phiếu treo cổ)",
        "emoji": "🐦",
    },
    7: {
        "name": "Thần Tình Yêu",
        "description": "Tạo cặp tình nhân",
        "emoji": "💕",
    },
    8: {
        "name": "Cổ Hoặc Sư",
        "description": "Mê hoặc 1 người (chết thay nếu bạn chết)",
        "emoji": "🎭",
    },
}


@register_role
class Actor(Role):
    metadata = RoleMetadata(
        name="Diễn Viên",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm đầu tiên, quản trò chọn ngẫu nhiên 3 lá chức năng. Mỗi đêm bạn có thể chọn ngẫu nhiên 1 lá để thực hiện chức năng đó. Mỗi lá chỉ được dùng 1 lần.",
        night_order=90,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/actor.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.available_abilities: list[int] = []  # 3 randomly selected ability IDs
        self.used_abilities: set[int] = set()  # Track which abilities have been used
        self.last_night_action: Optional[int] = None  # Track last night's action

    async def on_first_night(self, game: WerewolfGame, player: PlayerState) -> None:  # type: ignore[override]
        """On first night, randomly select 3 abilities for this actor."""
        logger.info("Actor first-night start | guild=%s actor=%s", game.guild.id, player.user_id)
        
        try:
            # Randomly select 3 unique abilities from the pool
            all_ability_ids = list(ACTOR_ABILITIES.keys())
            self.available_abilities = random.sample(all_ability_ids, 3)
            
            ability_descriptions = []
            for ability_id in self.available_abilities:
                ability = ACTOR_ABILITIES[ability_id]
                ability_descriptions.append(
                    f"{ability['emoji']} **{ability['name']}** - {ability['description']}"
                )
            
            abilities_text = "\n".join(ability_descriptions)
            
            await game._safe_send_dm(player.member,
                f"🎭 **Diễn Viên - Các Lá Chức Năng**\n\n"
                f"Đêm đầu tiên, quản trò đã chọn ngẫu nhiên 3 lá chức năng cho bạn:\n\n"
                f"{abilities_text}\n\n"
                f"Mỗi đêm, bạn có thể chọn ngẫu nhiên 1 lá để thực hiện. Mỗi lá chỉ được dùng 1 lần trong trò chơi.\n"
                f"Khi thực hiện, bạn sẽ được hỏi chọn mục tiêu cho chức năng đó.")
            
            logger.info("Actor abilities selected | guild=%s actor=%s abilities=%s", 
                       game.guild.id, player.user_id, self.available_abilities)
        
        except Exception as e:
            logger.error("Error in Actor first-night | guild=%s actor=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, actor can choose one of their 3 abilities to use."""
        if not player.alive or not self._is_player_eligible_for_action(game, player):
            return
        
        # Get remaining available abilities (not yet used)
        remaining = [aid for aid in self.available_abilities if aid not in self.used_abilities]
        
        if not remaining:
            logger.info("Actor has no remaining abilities | guild=%s actor=%s night=%s", 
                       game.guild.id, player.user_id, night_number)
            return
        
        logger.info("Actor on_night | guild=%s actor=%s night=%s remaining=%s", 
                   game.guild.id, player.user_id, night_number, remaining)
        
        try:
            # Build options for remaining abilities
            options = {}
            for idx, ability_id in enumerate(remaining, 1):
                ability = ACTOR_ABILITIES[ability_id]
                options[ability_id] = f"{ability['emoji']} {ability['name']} - {ability['description']}"
            
            # Add skip option
            options[0] = "⏭️ Không sử dụng đêm nay"
            
            chosen_ability = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="Diễn Viên - Chọn Chức Năng",
                description=f"Đêm {night_number}: Chọn 1 trong {len(remaining)} lá chức năng còn lại để thực hiện.",
                options=options,
                allow_skip=True,
            )
            
            if chosen_ability == 0 or chosen_ability not in remaining:
                logger.info("Actor chose to skip | guild=%s actor=%s night=%s", 
                           game.guild.id, player.user_id, night_number)
                return
            
            # Execute the chosen ability
            self.used_abilities.add(chosen_ability)
            await self._execute_ability(game, player, chosen_ability, night_number)
            
            logger.info("Actor used ability | guild=%s actor=%s night=%s ability=%s", 
                       game.guild.id, player.user_id, night_number, chosen_ability)
        
        except Exception as e:
            logger.error("Error in Actor on_night | guild=%s actor=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)

    async def _execute_ability(
        self, 
        game: WerewolfGame, 
        player: PlayerState, 
        ability_id: int, 
        night_number: int
    ) -> None:
        """Execute the chosen ability."""
        ability = ACTOR_ABILITIES[ability_id]
        
        if ability_id == 1:  # Tiên Tri (Seer)
            await self._ability_seer(game, player, night_number)
        elif ability_id == 2:  # Bảo Vệ (Guard)
            await self._ability_guard(game, player, night_number)
        elif ability_id == 3:  # Phù Thủy Chữa (Witch Heal)
            await self._ability_witch_heal(game, player, night_number)
        elif ability_id == 4:  # Phù Thủy Giết (Witch Kill)
            await self._ability_witch_kill(game, player, night_number)
        elif ability_id == 5:  # Thợ Săn (Hunter)
            await self._ability_hunter(game, player, night_number)
        elif ability_id == 6:  # Con Quạ (Raven)
            await self._ability_raven(game, player, night_number)
        elif ability_id == 7:  # Thần Tình Yêu (Cupid)
            await self._ability_cupid(game, player, night_number)
        elif ability_id == 8:  # Cổ Hoặc Sư (Hypnotist)
            await self._ability_hypnotist(game, player, night_number)

    async def _ability_seer(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Seer ability - identify someone."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Tiên Tri",
            description="Chọn 1 người để xem danh tính của họ.",
            options=options,
            allow_skip=False,
        )
        
        if target_id and target_id in options:
            target = game.players.get(target_id)
            if target and target.roles:
                role_name = target.roles[0].metadata.name
                await game._safe_send_dm(player.member, f"👁️ {target.display_name()} là **{role_name}**")

    async def _ability_guard(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Guard ability - protect someone."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Bảo Vệ",
            description="Chọn 1 người để bảo vệ khỏi Ma Sói đêm nay.",
            options=options,
            allow_skip=False,
        )
        
        if target_id and target_id in options:
            target = game.players.get(target_id)
            if target:
                # Store protected target (game will check this during night kill resolution)
                game._actor_protected_target = target_id  # pylint: disable=protected-access
                await game._safe_send_dm(player.member, f"🛡️ Bạn đã bảo vệ {target.display_name()}")

    async def _ability_witch_heal(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Witch heal ability - save someone."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Phù Thủy Chữa",
            description="Chọn 1 người để cứu sống nếu họ bị Ma Sói cắn đêm nay.",
            options=options,
            allow_skip=False,
        )
        
        if target_id and target_id in options:
            target = game.players.get(target_id)
            if target:
                game._actor_heal_target = target_id  # pylint: disable=protected-access
                await game._safe_send_dm(player.member, f"🧪 Bạn đã chuẩn bị chữa cho {target.display_name()}")

    async def _ability_witch_kill(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Witch kill ability - poison someone."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Phù Thủy Giết",
            description="Chọn 1 người để giết.",
            options=options,
            allow_skip=False,
        )
        
        if target_id and target_id in options:
            game._pending_deaths.append((target_id, "actor_witch"))
            target = game.players.get(target_id)
            if target:
                await game._safe_send_dm(player.member, f"💀 Bạn đã độc {target.display_name()}")

    async def _ability_hunter(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Hunter ability - choose shoot target."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Thợ Săn",
            description="Chọn 1 người. Nếu bạn bị Ma Sói cắn, bạn sẽ bắn người này.",
            options=options,
            allow_skip=False,
        )
        
        if target_id and target_id in options:
            game._actor_hunt_target = target_id  # pylint: disable=protected-access
            target = game.players.get(target_id)
            if target:
                await game._safe_send_dm(player.member, f"🏹 Bạn sẽ bắn {target.display_name()} nếu bị giết")

    async def _ability_raven(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Raven ability - curse someone for +2 votes."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Con Quạ",
            description="Chọn 1 người để nguyền rủa. Họ sẽ nhận +2 phiếu treo cổ sáng mai.",
            options=options,
            allow_skip=False,
        )
        
        if target_id and target_id in options:
            game._actor_raven_target = target_id  # pylint: disable=protected-access
            target = game.players.get(target_id)
            if target:
                await game._safe_send_dm(player.member, f"🐦 Bạn đã nguyền rủa {target.display_name()}")

    async def _ability_cupid(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Cupid ability - create lovers."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if len(candidates) < 2:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        lover1_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Thần Tình Yêu (Người 1)",
            description="Chọn người tình thứ nhất.",
            options=options,
            allow_skip=False,
        )
        
        if not lover1_id or lover1_id not in options:
            return
        
        # Remove first lover from options for second choice
        options2 = {uid: name for uid, name in options.items() if uid != lover1_id}
        lover2_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Thần Tình Yêu (Người 2)",
            description="Chọn người tình thứ hai.",
            options=options2,
            allow_skip=False,
        )
        
        if lover2_id and lover2_id in options2:
            game._lovers.add(lover1_id)
            game._lovers.add(lover2_id)
            lover1 = game.players.get(lover1_id)
            lover2 = game.players.get(lover2_id)
            if lover1 and lover2:
                await game._safe_send_dm(player.member, 
                    f"💕 Bạn đã tạo cặp tình nhân:\n{lover1.display_name()} 💕 {lover2.display_name()}")

    async def _ability_hypnotist(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:
        """Hypnotist ability - charm someone."""
        candidates = [p for p in game.alive_players() if p.user_id != player.user_id]
        if not candidates:
            return
        
        options = {p.user_id: p.display_name() for p in candidates}
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Diễn Viên - Cổ Hoặc Sư",
            description="Chọn 1 người để mê hoặc. Nếu bạn bị giết đêm nay, họ sẽ chết thay.",
            options=options,
            allow_skip=False,
        )
        
        if target_id and target_id in options:
            game._charmed.add(target_id)
            target = game.players.get(target_id)
            if target:
                await game._safe_send_dm(player.member, f"🎭 Bạn đã mê hoặc {target.display_name()}")

    def _is_player_eligible_for_action(self, game: WerewolfGame, player: PlayerState) -> bool:
        """Check if player can act."""
        return player.alive and not player.death_pending and not player.skills_disabled
