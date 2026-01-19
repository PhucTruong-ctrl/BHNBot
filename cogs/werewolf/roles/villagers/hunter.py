"""Hunter role implementation."""

from __future__ import annotations

from core.logging import get_logger
from typing import TYPE_CHECKING

from .. import register_role
from ..base import Alignment, Expansion, Role, RoleMetadata

if TYPE_CHECKING:
    from ...engine.game import WerewolfGame
    from ...engine.state import PlayerState

logger = get_logger("werewolf_roles_villagers_hunte")


@register_role
class Hunter(Role):
    """Hunter role - Takes someone with them when they die."""
    
    metadata = RoleMetadata(
        name="Thợ Săn",
        alignment=Alignment.VILLAGE,
        expansion=Expansion.BASIC,
        description="Mỗi đêm chọn 1 người. Nếu bị giết, người đó chết theo. Nếu bị treo cổ, chọn 1 người để bắn.",
        night_order=75,
        card_image_url="https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/werewolf-game/role-pics/villager/hunter.png",
    )

    def __init__(self) -> None:
        super().__init__()
        self.marked_target: int | None = None

    async def on_night(self, game: WerewolfGame, player: PlayerState, night_number: int) -> None:  # type: ignore[override]
        """Each night, Hunter chooses someone to mark."""
        logger.info("Hunter on_night start | guild=%s hunter=%s night=%s", game.guild.id, player.user_id, night_number)
        choices = {p.user_id: p.display_name() for p in game.alive_players() if p.user_id != player.user_id}
        if not choices:
            logger.warning("No valid targets for Hunter | guild=%s hunter=%s", game.guild.id, player.user_id)
            return
        
        target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
            player,
            title="Thợ Săn - Đánh Dấu Mục Tiêu",
            description="Chọn 1 người để đánh dấu. Nếu bạn chết đêm nay, người này sẽ chết theo.",
            options=choices,
            allow_skip=False,
        )
        if target_id and target_id in choices:
            self.marked_target = target_id
            logger.info("Hunter marked target | guild=%s hunter=%s target=%s", game.guild.id, player.user_id, target_id)
        else:
            logger.warning("Hunter failed to mark or skipped | guild=%s hunter=%s", game.guild.id, player.user_id)

    async def on_death(self, game: WerewolfGame, player: PlayerState, cause: str) -> None:  # type: ignore[override]
        """When Hunter dies, take someone with them - DRAMATIC!
        
        NOTE: player.alive is already False when this is called (set before _handle_death).
        Do NOT check player.alive here - that was a bug causing Hunter to never trigger!
        """
        logger.info("Hunter on_death triggered | guild=%s hunter=%s cause=%s marked=%s", 
                   game.guild.id, player.user_id, cause, self.marked_target)
        
        if cause == "lynch":
            # === DRAMATIC ANNOUNCEMENT: HUNTER REVEALS (gửi vào diễn-biến) ===
            try:
                await game.text_channel.send(
                    f"🔫 **{player.display_name()} là một THỢ SĂN!**\n"
                    f"💥 *Họ rút súng Shotgun ra, tay run rẩy tìm mục tiêu cuối cùng...*\n"
                    f"⏳ _{player.display_name()} có 30 giây để chọn ai sẽ chết cùng mình..._"
                )
            except Exception as e:
                logger.error("Failed to send Hunter reveal | error=%s", e)
            
            # Voted out - choose who to shoot (exclude self)
            choices = {p.user_id: p.display_name() for p in game.alive_players() if p.user_id != player.user_id}
            if not choices:
                logger.warning("No valid targets for Hunter revenge | guild=%s hunter=%s", game.guild.id, player.user_id)
                return
            
            # DM prompt to choose target
            target_id = await game._prompt_dm_choice(  # pylint: disable=protected-access
                player,
                title="🔫 Thợ Săn - Báo Thù Cuối Cùng",
                description=(
                    "**BẠN BỊ TREO CỔ!**\n\n"
                    "💀 Trước khi chết, bạn có thể bắn một người!\n"
                    "⏰ 30 giây để chọn..."
                ),
                options=choices,
                allow_skip=True,
                timeout=30,
            )
            
            if target_id and target_id in choices:
                target_player = game.players.get(target_id)
                
                # === DRAMATIC SHOOTING ANNOUNCEMENT (gửi vào diễn-biến) ===
                try:
                    await game.text_channel.send(
                        f"💥💥💥 **BANG!!!** 💥💥💥\n\n"
                        f"🔫 {player.display_name()} đã BẮN CHẾT {target_player.display_name()}!\n"
                        f"💀 ...rồi quay súng tự sát.\n\n"
                        f"_Hai thi thể nằm gục, máu chảy trên nền đất..._"
                    )
                except Exception as e:
                    logger.error("Failed to send shooting announcement | error=%s", e)
                
                logger.info("Hunter lynch revenge kill queued | guild=%s hunter=%s victim=%s", 
                           game.guild.id, player.user_id, target_id)
                game._pending_deaths.append((target_id, "hunter"))  # pylint: disable=protected-access
                
                # Check for achievement: Hunter kill wolf
                if target_player and target_player.get_alignment_priority() == Alignment.WEREWOLF:
                    player.hunter_killed_wolf = True
            else:
                # === NO SHOT ANNOUNCEMENT ===
                try:
                    await game.text_channel.send(
                        f"🔫 {player.display_name()} run tay... không bắn được ai...\n"
                        f"💀 _Họ gục xuống trong tuyệt vọng._"
                    )
                except Exception as e:
                    logger.error("Failed to send no-shot announcement | error=%s", e)
                logger.info("Hunter skipped revenge | guild=%s hunter=%s", game.guild.id, player.user_id)
        else:
            # Killed by other means (wolves, witch, etc) - use marked target
            logger.info("Hunter killed by %s, checking marked target | guild=%s hunter=%s marked=%s", 
                       cause, game.guild.id, player.user_id, self.marked_target)
            if self.marked_target and self.marked_target in game.players:
                target_player = game.players.get(self.marked_target)
                if target_player and target_player.alive:
                    # Announce in diễn-biến
                    try:
                        await game.text_channel.send(
                            f"🔫 **{player.display_name()} (Thợ Săn) đã kéo theo {target_player.display_name()} trước khi chết!**"
                        )
                    except Exception:
                        pass
                    
                    logger.info("Hunter mark revenge kill queued | guild=%s hunter=%s victim=%s", 
                               game.guild.id, player.user_id, self.marked_target)
                    game._pending_deaths.append((self.marked_target, "hunter"))  # pylint: disable=protected-access
                    
                    # Check for achievement
                    if target_player.get_alignment_priority() == Alignment.WEREWOLF:
                        player.hunter_killed_wolf = True
                else:
                    logger.info("Hunter marked target already dead | guild=%s hunter=%s target=%s", 
                               game.guild.id, player.user_id, self.marked_target)
            else:
                logger.debug("Hunter has no marked target | guild=%s hunter=%s", game.guild.id, player.user_id)
