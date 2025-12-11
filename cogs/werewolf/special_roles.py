"""
Werewolf Special Roles Logic
Xử lý các vai trò đặc biệt như Sói Pháp Sư, Thằng Ngố, etc.
"""
from typing import Dict, List, Optional
from .models import GameWerewolf, GamePlayer, Role, Faction, ROLE_METADATA


class SpecialRolesHandler:
    """Xử lý logic các vai trò đặc biệt"""
    
    @staticmethod
    def handle_wolf_shaman_disguise(game: GameWerewolf) -> Dict[str, int]:
        """
        Sói Pháp Sư yểm một người (Tiên Tri sẽ thấy aura Sói)
        Return: {player_id: disguised_as_role_id}
        """
        disguises = {}
        
        for player in game.get_players_by_faction(Faction.WOLF):
            if player.role == Role.WOLF_SHAMAN and player.night_target and player.is_alive:
                # Mark the target as disguised
                disguises[player.night_target] = player.user_id
        
        return disguises
    
    @staticmethod
    def handle_archer_shooting(game: GameWerewolf, channel) -> List[int]:
        """
        Xạ Thủ bắn vào ban ngày (2 viên đạn)
        Return: list player_ids bị bắn
        """
        killed = []
        
        for player in game.players.values():
            if player.role == Role.ARCHER and player.is_alive:
                # Archer dùng ammo trên ban ngày
                if player.ammo > 0 and player.night_target:
                    target_id = player.night_target
                    if target_id in game.players:
                        target = game.players[target_id]
                        target.is_alive = False
                        killed.append(target_id)
                        player.ammo -= 1
        
        return killed
    
    @staticmethod
    def handle_avenger_revenge(game: GameWerewolf, lynched_id: int) -> Optional[int]:
        """
        Kẻ Báo Thù - nếu bị giết, giết người được chọn
        Return: player_id bị báo thù
        """
        if lynched_id in game.players:
            lynched = game.players[lynched_id]
            if lynched.role == Role.AVENGER and lynched.avenge_target:
                avenge_target = lynched.avenge_target
                if avenge_target in game.players:
                    return avenge_target
        
        return None
    
    @staticmethod
    def handle_fool_win(game: GameWerewolf, lynched_id: int) -> bool:
        """
        Thằng Ngố - nếu bị treo cổ, thằng ngố thắng
        Return: True nếu thằng ngố thắng
        """
        if lynched_id in game.players:
            lynched = game.players[lynched_id]
            if lynched.role == Role.FOOL:
                return True
        
        return False
    
    @staticmethod
    def handle_hunter_win(game: GameWerewolf) -> Optional[int]:
        """
        Thợ Săn Người - check if target was killed
        Return: player_id của thợ săn nếu thắng, None otherwise
        """
        for player in game.players.values():
            if player.role == Role.HUNTER and player.hunter_target:
                target = game.players.get(player.hunter_target)
                if target and not target.is_alive:
                    # Target was killed by means other than Lynch
                    if player.hunter_target not in game.lynch_votes:
                        return player.user_id
        
        return None
    
    @staticmethod
    def handle_bomber_explosion(game: GameWerewolf, night_num: int) -> Optional[int]:
        """
        Kẻ Đặt Bom - bom nổ vào đêm tiếp theo
        Return: player_id bị nổ bom
        """
        for player in game.players.values():
            if player.role == Role.BOMBER and player.is_alive:
                # Check if bomb was set last night and should explode now
                if player.bomb_target_night and night_num > 1:  # Explodes 1 night later
                    target_id = player.bomb_target_night
                    if target_id in game.players:
                        return target_id
        
        return None
    
    @staticmethod
    def handle_wolf_seer_check(game: GameWerewolf, seer_id: int) -> Optional[Dict]:
        """
        Sói Tiên Tri xem vai trò, các sói khác sẽ biết
        Return: {'target_id': id, 'role': role_name}
        """
        if seer_id in game.players:
            seer = game.players[seer_id]
            if seer.role == Role.WOLF_SEER and seer.night_target:
                target = game.players.get(seer.night_target)
                if target:
                    return {
                        'target_id': seer.night_target,
                        'target_name': target.username,
                        'role': target.role.value if target.role else 'Unknown'
                    }
        
        return None
    
    @staticmethod
    def handle_cursed_villager_conversion(game: GameWerewolf) -> List[int]:
        """
        Bán Sói - nếu bị sói cắn, thành sói
        Return: list player_ids bị convert
        """
        converted = []
        
        for player in game.players.values():
            if player.role == Role.CURSED_VILLAGER and not player.is_alive:
                if player.user_id in game.night_actions_log.get('kills', []):
                    # Was killed by wolf
                    player.role = Role.WEREWOLF
                    player.is_alive = True
                    converted.append(player.user_id)
        
        return converted
    
    @staticmethod
    def calculate_wolf_voting_power(wolves: List[GamePlayer]) -> Dict[int, int]:
        """
        Tính voting power của sói (Sói Đầu Đàn có 2x vote)
        Return: {player_id: vote_weight}
        """
        weights = {}
        
        for wolf in wolves:
            if wolf.role == Role.WOLF_ALPHA:
                weights[wolf.user_id] = 2
            else:
                weights[wolf.user_id] = 1
        
        return weights
    
    @staticmethod
    def is_role_night_active(role: Role) -> bool:
        """Check if role is active during night"""
        metadata = ROLE_METADATA.get(role)
        if metadata:
            return metadata.is_night_active
        return False
    
    @staticmethod
    def should_wolf_be_hidden(disguised_targets: Dict, player_id: int, seer: GamePlayer) -> bool:
        """
        Check if a wolf should appear as villager to Seer (due to Shaman disguise)
        """
        if player_id in disguised_targets:
            return True
        return False
