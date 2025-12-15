"""Judge role - makes secret signal to have 2 lynches instead of 1."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = logging.getLogger("werewolf")


@register_role
class Judge(Role):
    metadata = RoleMetadata(
        name="Thẩm Phán",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.THE_VILLAGE,
        description="Đêm đầu tiên, bạn chỉ cho quản trò ám hiệu đặc biệt của mình. Một lần trong trò chơi, khi bạn thực hiện ám hiệu, sáng đó sẽ có 2 người bị treo cổ thay vì 1.",
        first_night_only=False,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/judge.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.chosen_signal: Optional[str] = None
        self.has_used_signal: bool = False

    async def on_first_night(self, game: WerewolfGame, player: PlayerState) -> None:  # type: ignore[override]
        """On first night, Judge chooses their secret signal."""
        logger.info("Judge first-night start | guild=%s judge=%s", game.guild.id, player.user_id)
        
        try:
            options = {
                1: "👍 Ngón cái hướng lên (Thumbs Up)",
                2: "👎 Ngón cái hướng xuống (Thumbs Down)",
                3: "✌️ Chữ V (Peace Sign)",
                4: "👋 Vẫy tay (Wave)",
                5: "🤐 Hạ khẩu (Zip Mouth)",
                6: "😘 Hôn (Kiss)",
                7: "🙏 Cầu xin (Prayer)",
                8: "💪 Cơ bắp (Muscle)",
            }
            
            choice = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="Thẩm Phán - Chọn Ám Hiệu",
                description="Chọn ám hiệu đặc biệt của bạn. Sáng nào bạn thực hiện ám hiệu này, sẽ có 2 người bị treo cổ thay vì 1 (chỉ dùng được 1 lần).",
                options=options,
                allow_skip=False,
            )
            
            if choice in options:
                signal_names = {
                    1: "👍 Ngón cái hướng lên",
                    2: "👎 Ngón cái hướng xuống",
                    3: "✌️ Chữ V",
                    4: "👋 Vẫy tay",
                    5: "🤐 Hạ khẩu",
                    6: "😘 Hôn",
                    7: "🙏 Cầu xin",
                    8: "💪 Cơ bắp",
                }
                self.chosen_signal = signal_names.get(choice, "Unknown")
                
                await game._safe_send_dm(player.member,
                    f"✅ Ám hiệu của bạn là: **{self.chosen_signal}**\n\n"
                    f"Một lần trong trò chơi, khi bạn thực hiện ám hiệu này sáng, sẽ có 2 người bị treo cổ thay vì 1.\n"
                    f"Hãy nhớ thực hiện ám hiệu này rõ để quản trò nhận biết!")
                
                logger.info("Judge chose signal | guild=%s judge=%s signal=%s", 
                           game.guild.id, player.user_id, self.chosen_signal)
            else:
                logger.warning("Judge failed to choose signal | guild=%s judge=%s", 
                             game.guild.id, player.user_id)
        
        except Exception as e:
            logger.error("Error in Judge first-night | guild=%s judge=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)

    async def on_day(self, game: WerewolfGame, player: PlayerState, day_number: int) -> None:  # type: ignore[override]
        """On day phase, check if Judge uses their signal."""
        # Check if Judge has already used the signal
        if self.has_used_signal:
            return
        
        logger.info("Judge on_day check | guild=%s judge=%s day=%s signal=%s", 
                   game.guild.id, player.user_id, day_number, self.chosen_signal)
        
        try:
            # Prompt Judge to ask if they want to use signal today
            if not player.alive:
                logger.warning("Judge is dead, skipping signal prompt | guild=%s judge=%s", 
                             game.guild.id, player.user_id)
                return
            
            signal_options = {
                1: f"✅ Dùng ám hiệu hôm nay ({self.chosen_signal}) - Sẽ có 2 người bị treo cổ",
                2: "❌ Không dùng - Chờ ngày khác"
            }
            
            use_signal = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="Thẩm Phán - Sử Dụng Ám Hiệu",
                description=f"Hôm nay bạn có muốn dùng ám hiệu của mình không?\nÁm hiệu của bạn: {self.chosen_signal}",
                options=signal_options,
                allow_skip=True,
            )
            
            if use_signal == 1:
                # Judge wants to use the signal
                self.has_used_signal = True
                game._judge_activated_double_lynch = True  # pylint: disable=protected-access
                
                await game._safe_send_dm(player.member,
                    f"🎭 Bạn đã dùng ám hiệu của mình! Sáng nay sẽ có 2 người bị treo cổ!")
                
                logger.info("Judge activated double lynch | guild=%s judge=%s day=%s", 
                           game.guild.id, player.user_id, day_number)
            else:
                logger.info("Judge chose not to use signal | guild=%s judge=%s day=%s", 
                           game.guild.id, player.user_id, day_number)
        
        except Exception as e:
            logger.error("Error in Judge on_day | guild=%s judge=%s error=%s", 
                        game.guild.id, player.user_id, str(e), exc_info=True)
