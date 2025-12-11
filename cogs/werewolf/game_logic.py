"""
Werewolf Game Logic
Xử lý các pha game, actions, và win conditions
"""
import asyncio
import random
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from .models import (
    GameWerewolf, GamePlayer, GameState, Role, Faction, Alignment,
    ROLE_METADATA, get_role_by_alias
)


def log(msg: str):
    """Log message"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [GameLogic] {msg}")


class GameLogic:
    """Quản lý logic game Ma Sói"""
    
    def __init__(self):
        self.games: Dict[int, GameWerewolf] = {}  # guild_id -> GameWerewolf
        self.game_locks: Dict[int, asyncio.Lock] = {}  # guild_id -> Lock
    
    def get_lock(self, guild_id: int) -> asyncio.Lock:
        """Lấy lock cho guild"""
        if guild_id not in self.game_locks:
            self.game_locks[guild_id] = asyncio.Lock()
        return self.game_locks[guild_id]
    
    def get_game(self, guild_id: int) -> Optional[GameWerewolf]:
        """Lấy game hiện tại của guild"""
        return self.games.get(guild_id)
    
    def create_game(self, guild_id: int, channel_id: int, min_players: int = 4) -> GameWerewolf:
        """Tạo game mới"""
        game = GameWerewolf(guild_id=guild_id, channel_id=channel_id, min_players=min_players)
        self.games[guild_id] = game
        return game
    
    def delete_game(self, guild_id: int) -> None:
        """Xóa game"""
        if guild_id in self.games:
            del self.games[guild_id]
        if guild_id in self.game_locks:
            del self.game_locks[guild_id]
    
    # =========== PLAYER MANAGEMENT ===========
    
    def add_player(self, game: GameWerewolf, user_id: int, username: str) -> bool:
        """Thêm người chơi vào game. Return True nếu thành công"""
        if user_id in game.players:
            return False  # Đã join rồi
        
        player = GamePlayer(user_id=user_id, username=username, game=game)
        game.players[user_id] = player
        return True
    
    def remove_player(self, game: GameWerewolf, user_id: int) -> bool:
        """Loại người chơi khỏi game"""
        if user_id not in game.players:
            return False
        
        del game.players[user_id]
        return True
    
    # =========== ROLE DISTRIBUTION ===========
    
    def build_role_list(self, num_players: int) -> List[Role]:
        """
        Xây dựng danh sách role cân bằng dựa trên số người chơi
        
        Công thức:
        - 4 người: 2D + 1W + 1S
        - 5-9 người: 3D + 1W + 1S (base), +1D cho mỗi người thêm đến 9
        - 10-14 người: 6D + 2W + 2S (tăng +1D mỗi người từ 10-14)
        - 15-19 người: 8D + 3W + 3S (tăng +1D mỗi người từ 15-19)
        - 20+ người: Tính động mỗi 5 người
        
        Bảng tham khảo:
        - 4: 2D + 1W + 1S
        - 5: 3D + 1W + 1S
        - 6: 4D + 1W + 1S
        - 9: 7D + 1W + 1S
        - 10: 6D + 2W + 2S
        - 14: 10D + 2W + 2S
        - 15: 8D + 3W + 4S (lưu ý: 3 sói + 4 đặc + 8 dân = 15)
        """
        print(f"[BUILD_ROLE_LIST_START] num_players={num_players}")
        roles = []
        
        # Determine wolves and special count based on player count
        if num_players <= 4:
            # Special case for 4 players: 2D + 1W + 1S
            num_wolves = 1
            num_special = 1
            num_villagers = 2
            print(f"[BRANCH] num_players <= 4: W={num_wolves}, S={num_special}, V={num_villagers}")
        elif num_players < 10:
            # 5-9 players: 1 wolf, 1 special, rest villagers
            num_wolves = 1
            num_special = 1
            num_villagers = num_players - num_wolves - num_special
            print(f"[BRANCH] 5-9 players: W={num_wolves}, S={num_special}, V={num_villagers}")
        elif num_players < 15:
            # 10-14 players: 2 wolves, 2 special, rest villagers
            num_wolves = 2
            num_special = 2
            num_villagers = num_players - num_wolves - num_special
            print(f"[BRANCH] 10-14 players: W={num_wolves}, S={num_special}, V={num_villagers}")
        elif num_players < 20:
            # 15-19 players: 3 wolves, 3-4 special, rest villagers
            num_wolves = 3
            num_special = 4 if num_players >= 15 else 3
            num_villagers = num_players - num_wolves - num_special
            print(f"[BRANCH] 15-19 players: W={num_wolves}, S={num_special}, V={num_villagers}")
        else:
            # 20+ players: scale dynamically
            num_wolves = 1 + (num_players - 5) // 5
            num_special = 1 + (num_players - 5) // 5
            num_villagers = num_players - num_wolves - num_special
            print(f"[BRANCH] 20+ players: W={num_wolves}, S={num_special}, V={num_villagers}")
        
        log(f"ROLE_CALC: {num_players} players -> calc {num_wolves}W, {num_special}S, {num_villagers}V")
        
        # Add wolves to roles
        roles.extend([Role.WEREWOLF] * num_wolves)
        log(f"ROLE_ADD_WOLVES: Added {num_wolves} wolves, roles count = {len(roles)}")
        
        # Add special roles
        special_roles = [
            Role.DOCTOR,
            Role.SEER,
            Role.WITCH,
            Role.AURA_SEER,
            Role.ARCHER,
            Role.BEAST_HUNTER,
            Role.MEDIUM,
        ]
        
        added_special = 0
        for i in range(num_special):
            if i < len(special_roles):
                roles.append(special_roles[i])
                added_special += 1
                log(f"ROLE_ADD_SPECIAL[{i}]: Added {special_roles[i].value}")
        
        log(f"ROLE_ADD_SPECIAL_TOTAL: Added {added_special} special roles, roles count = {len(roles)}")
        
        # Add villagers
        roles.extend([Role.VILLAGER] * num_villagers)
        log(f"ROLE_ADD_VILLAGERS: Added {num_villagers} villagers, roles count = {len(roles)}")
        
        log(f"ROLE_BUILD_FINAL: {num_players} players -> {len(roles)} roles: {[r.value for r in roles]}")
        print(f"[BUILD_ROLE_LIST_END] Returning {len(roles)} roles: {[r.value for r in roles]}")
        
        return roles
    
    def distribute_roles(self, game: GameWerewolf, role_list: List[Role]) -> None:
        """
        Phát vai trò cho người chơi
        role_list: danh sách role theo thứ tự (đã được setup trước đó)
        """
        print(f"[DISTRIBUTE_ROLES_START] role_list={[r.value for r in role_list]}, len={len(role_list)}")
        alive_players = list(game.players.values())
        print(f"[DISTRIBUTE_ROLES] Found {len(alive_players)} alive players")
        random.shuffle(alive_players)
        print(f"[DISTRIBUTE_ROLES] Shuffled players: {[p.username for p in alive_players]}")
        
        for i, player in enumerate(alive_players):
            if i < len(role_list):
                player.role = role_list[i]
                log(f"ROLE_DIST: {player.username} <- {player.role.value}")
                print(f"[ROLE_ASSIGN] Player {player.username} (index {i}) <- {player.role.value}")
            else:
                print(f"[ROLE_ASSIGN_ERROR] Player {player.username} (index {i}) has NO ROLE - role_list only has {len(role_list)} roles")
        print(f"[DISTRIBUTE_ROLES_END]")
    
    # =========== NIGHT PHASE ===========
    
    async def resolve_night_actions(self, game: GameWerewolf) -> Dict:
        """
        Xử lý tất cả hành động ban đêm
        Return: {"killed": [user_ids], "healed": [user_ids], "log": str}
        """
        log_lines = []
        
        # Tập hợp các mục tiêu bị chọn
        wolf_targets = []  # Sói chọn ai để cắn
        doctor_heals = []  # Bác sĩ che chở ai
        kills = []  # Người bị chết
        
        # 1. Collect Wolf kills
        for player in game.get_players_by_faction(Faction.WOLF):
            if player.night_target and player.is_alive:
                wolf_targets.append(player.night_target)
        
        if wolf_targets:
            # Nếu có multiple targets, random chọn 1
            victim = max(set(wolf_targets), key=wolf_targets.count)
            kills.append(victim)
            log_lines.append(f"🐺 Sói cắn người chơi #{victim}")
        
        # 2. Collect Doctor heals
        for player in game.players.values():
            if player.role == Role.DOCTOR and player.night_target and player.is_alive:
                doctor_heals.append(player.night_target)
        
        # 3. Apply heals (loại bỏ kills nếu có doctor)
        final_kills = [k for k in kills if k not in doctor_heals]
        
        # 4. Handle special roles
        # TODO: Witch, Medium, Beast Hunter, etc.
        
        # 5. Apply kills
        for user_id in final_kills:
            if user_id in game.players:
                player = game.players[user_id]
                player.is_alive = False
                game.dead_players.append(user_id)
                log_lines.append(f"💀 Người chơi {player.username} đã chết")
        
        # 6. Check cursed villager turning into wolf
        for user_id in final_kills:
            if user_id in game.players:
                player = game.players[user_id]
                if player.role == Role.CURSED_VILLAGER:
                    player.role = Role.WEREWOLF
                    player.is_alive = True  # Resurrected as wolf
                    log_lines.append(f"🔄 {player.username} đã biến thành Sói!")
        
        return {
            "killed": final_kills,
            "healed": doctor_heals,
            "log": "\n".join(log_lines)
        }
    
    # =========== DAY PHASE ===========
    
    async def resolve_votes(self, game: GameWerewolf) -> Optional[int]:
        """
        Xử lý bỏ phiếu ban ngày
        Return: user_id của người bị treo cổ, hoặc None
        """
        vote_counts = {}
        
        # Đếm phiếu (xét trọng số cho Alpha Wolf)
        for player in game.get_alive_players():
            if player.voted_for:
                vote_weight = 2 if player.role == Role.WOLF_ALPHA else 1
                vote_counts[player.voted_for] = vote_counts.get(player.voted_for, 0) + vote_weight
        
        if not vote_counts:
            return None
        
        # Lấy người có phiếu nhiều nhất
        lynched = max(vote_counts, key=vote_counts.get)
        
        # Kill
        if lynched in game.players:
            player = game.players[lynched]
            player.is_alive = False
            game.dead_players.append(lynched)
        
        return lynched
    
    # =========== WIN CONDITION ===========
    
    def check_win_condition(self, game: GameWerewolf) -> Optional[Dict]:
        """
        Kiểm tra điều kiện thắng
        Return: {"winner": "WOLF|VILLAGE|SOLO", "reason": str, "winners": [user_ids]}
        """
        alive_wolves = game.get_players_by_faction(Faction.WOLF)
        alive_villagers = [
            p for p in game.get_alive_players()
            if ROLE_METADATA.get(p.role, {}).faction == Faction.VILLAGER
        ]
        
        # Condition 1: Sói >= Dân
        if len(alive_wolves) >= len(alive_villagers) and len(alive_villagers) > 0:
            return {
                "winner": "WOLF",
                "reason": "🐺 Sói đã kiểm soát số đông!",
                "winners": [p.user_id for p in alive_wolves]
            }
        
        # Condition 2: Sói = 0
        if len(alive_wolves) == 0 and len(alive_villagers) > 0:
            return {
                "winner": "VILLAGE",
                "reason": "🏘️ Dân làng đã tiêu diệt tất cả sói!",
                "winners": [p.user_id for p in alive_villagers]
            }
        
        # Condition 3: Check solo wins
        # TODO: Implement Fool, Hunter, Bomber win conditions
        
        return None
    
    # =========== UTILITY FUNCTIONS ===========
    
    def reset_night_actions(self, game: GameWerewolf) -> None:
        """Reset night actions sau mỗi đêm"""
        for player in game.players.values():
            player.night_target = None
            player.night_action = None
    
    def reset_day_votes(self, game: GameWerewolf) -> None:
        """Reset votes sau mỗi ngày"""
        for player in game.players.values():
            player.voted_for = None
            player.votes_for_me = 0
    
    def get_game_status_embed(self, game: GameWerewolf) -> Dict:
        """Tạo embed thông tin game"""
        alive = game.get_alive_players()
        dead = game.get_dead_players()
        
        return {
            "title": f"🐺 Game Ma Sói - Vòng {game.night_count}/{game.day_count}",
            "description": f"Trạng thái: **{game.state.value}**",
            "fields": [
                {"name": "👥 Còn sống", "value": str(len(alive)), "inline": True},
                {"name": "💀 Đã chết", "value": str(len(dead)), "inline": True},
            ]
        }
    
    def format_player_list(self, game: GameWerewolf, show_roles: bool = False) -> str:
        """Format danh sách người chơi"""
        lines = []
        for player in game.get_alive_players():
            status = "🟢" if player.is_alive else "⚫"
            role_info = f" ({player.role.value})" if show_roles and player.role else ""
            lines.append(f"{status} {player.username}{role_info}")
        
        return "\n".join(lines) if lines else "Không có ai"
