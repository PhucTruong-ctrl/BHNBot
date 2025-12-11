"""
Werewolf Game Models
Định nghĩa các vai trò, trạng thái, và cấu trúc dữ liệu
"""
from enum import Enum
from typing import Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime

# ============= FACTION ENUM =============
class Faction(Enum):
    """Phe trong game"""
    VILLAGER = "Dân Làng"      # Phe thiện
    WOLF = "Sói"                # Phe ác
    SOLO = "Riêng"              # Phe độc lập


class Alignment(Enum):
    """Sắc thái (thiện/ác/không rõ)"""
    GOOD = "Thiện"
    EVIL = "Ác"
    NEUTRAL = "Không Rõ"


# ============= ROLE ENUM =============
class Role(Enum):
    """Tất cả 21 vai trò"""
    # === VILLAGER ROLES ===
    DOCTOR = "Bác Sĩ"
    ARCHER = "Xạ Thủ"
    SEER = "Tiên Tri"
    AURA_SEER = "Thầy Bói"
    MEDIUM = "Thầy Đồng"
    WITCH = "Phù Thủy"
    AVENGER = "Kẻ Báo Thù"
    BEAST_HUNTER = "Thợ Săn Quái Thú"
    CURSED_VILLAGER = "Bán Sói"
    
    # === WOLF ROLES ===
    WEREWOLF = "Ma Sói"
    WOLF_SHAMAN = "Sói Pháp Sư"
    WOLF_ALPHA = "Sói Đầu Đàn"
    WOLF_SEER = "Sói Tiên Tri"
    
    # === SOLO ROLES ===
    HUNTER = "Thợ Săn Người"
    FOOL = "Thằng Ngố"
    BOMBER = "Kẻ Đặt Bom"
    
    # PLACEHOLDER (nếu game chưa đủ người)
    VILLAGER = "Dân Làng"


# ============= ROLE METADATA =============
class RoleMetadata:
    """Thông tin chi tiết của mỗi role"""
    def __init__(
        self,
        role: Role,
        faction: Faction,
        alignment: Alignment,
        aliases: List[str],
        description: str,
        is_night_active: bool = False,
    ):
        self.role = role
        self.faction = faction
        self.alignment = alignment
        self.aliases = aliases
        self.description = description
        self.is_night_active = is_night_active
    
    def __repr__(self) -> str:
        return f"<Role: {self.role.value} ({self.faction.value})"


# Dictionary lưu metadata cho mỗi role
ROLE_METADATA = {
    Role.DOCTOR: RoleMetadata(
        role=Role.DOCTOR,
        faction=Faction.VILLAGER,
        alignment=Alignment.GOOD,
        aliases=["bs", "doc", "bác sĩ", "doctor"],
        description="Che chở một người mỗi đêm (không bị giết).",
        is_night_active=True,
    ),
    Role.ARCHER: RoleMetadata(
        role=Role.ARCHER,
        faction=Faction.VILLAGER,
        alignment=Alignment.NEUTRAL,
        aliases=["gun", "xạ", "xạ thủ", "archer"],
        description="Có 2 viên đạn để bắn vào ban ngày.",
        is_night_active=False,
    ),
    Role.SEER: RoleMetadata(
        role=Role.SEER,
        faction=Faction.VILLAGER,
        alignment=Alignment.GOOD,
        aliases=["tri", "seer", "tiên tri"],
        description="Xem vai trò của một người mỗi đêm.",
        is_night_active=True,
    ),
    Role.AURA_SEER: RoleMetadata(
        role=Role.AURA_SEER,
        faction=Faction.VILLAGER,
        alignment=Alignment.GOOD,
        aliases=["bói", "aura", "thầy bói"],
        description="Xem phe của một người mỗi đêm.",
        is_night_active=True,
    ),
    Role.MEDIUM: RoleMetadata(
        role=Role.MEDIUM,
        faction=Faction.VILLAGER,
        alignment=Alignment.NEUTRAL,
        aliases=["đồng", "cu", "med", "thầy đồng"],
        description="Nói với người chết mỗi đêm, hồi sinh 1 người/ván.",
        is_night_active=True,
    ),
    Role.WITCH: RoleMetadata(
        role=Role.WITCH,
        faction=Faction.VILLAGER,
        alignment=Alignment.NEUTRAL,
        aliases=["phù", "witch", "phù thủy"],
        description="Có 2 bình thuốc: cứu (khi bị tấn công) và giết.",
        is_night_active=True,
    ),
    Role.AVENGER: RoleMetadata(
        role=Role.AVENGER,
        faction=Faction.VILLAGER,
        alignment=Alignment.GOOD,
        aliases=["báo", "av", "avenge", "kẻ báo thù"],
        description="Chọn người để chết khi bạn bị giết.",
        is_night_active=False,
    ),
    Role.BEAST_HUNTER: RoleMetadata(
        role=Role.BEAST_HUNTER,
        faction=Faction.VILLAGER,
        alignment=Alignment.NEUTRAL,
        aliases=["săn", "bh", "bhunter", "thợ săn quái thú"],
        description="Đặt bẫy lên người (nếu sói cắn thì sói yếu nhất chết).",
        is_night_active=True,
    ),
    Role.CURSED_VILLAGER: RoleMetadata(
        role=Role.CURSED_VILLAGER,
        faction=Faction.VILLAGER,
        alignment=Alignment.GOOD,
        aliases=["bán", "cursed", "bán sói"],
        description="Dân bình thường, nếu bị sói cắn thành sói.",
        is_night_active=False,
    ),
    
    # WOLF ROLES
    Role.WEREWOLF: RoleMetadata(
        role=Role.WEREWOLF,
        faction=Faction.WOLF,
        alignment=Alignment.EVIL,
        aliases=["sói", "ww", "ma sói"],
        description="Chọn một người để cắn chết mỗi đêm.",
        is_night_active=True,
    ),
    Role.WOLF_SHAMAN: RoleMetadata(
        role=Role.WOLF_SHAMAN,
        faction=Faction.WOLF,
        alignment=Alignment.EVIL,
        aliases=["sói pháp", "shaman", "wshaman", "wwshaman"],
        description="Yểm một người (Tiên Tri sẽ thấy là Sói).",
        is_night_active=True,
    ),
    Role.WOLF_ALPHA: RoleMetadata(
        role=Role.WOLF_ALPHA,
        faction=Faction.WOLF,
        alignment=Alignment.NEUTRAL,
        aliases=["đầu đàn", "alpha", "aw", "aww"],
        description="Ma Sói bình thường nhưng gấp đôi phiếu vote.",
        is_night_active=True,
    ),
    Role.WOLF_SEER: RoleMetadata(
        role=Role.WOLF_SEER,
        faction=Faction.WOLF,
        alignment=Alignment.EVIL,
        aliases=["sói tri", "ws", "wws"],
        description="Xem vai trò người chơi, sói khác sẽ biết.",
        is_night_active=True,
    ),
    
    # SOLO ROLES
    Role.HUNTER: RoleMetadata(
        role=Role.HUNTER,
        faction=Faction.SOLO,
        alignment=Alignment.NEUTRAL,
        aliases=["săn", "săn người", "hh"],
        description="Lừa mục tiêu bị treo cổ. Thắng với dân nếu mục tiêu bị giết.",
        is_night_active=False,
    ),
    Role.FOOL: RoleMetadata(
        role=Role.FOOL,
        faction=Faction.SOLO,
        alignment=Alignment.NEUTRAL,
        aliases=["ngố", "fool"],
        description="Lừa dân treo cổ bạn vào ban ngày để thắng.",
        is_night_active=False,
    ),
    Role.BOMBER: RoleMetadata(
        role=Role.BOMBER,
        faction=Faction.SOLO,
        alignment=Alignment.NEUTRAL,
        aliases=["bom", "bomb", "bomber"],
        description="Đặt bom vào đêm (nổ đêm tiếp theo). Không bị giết sói.",
        is_night_active=True,
    ),
    
    # DEFAULT
    Role.VILLAGER: RoleMetadata(
        role=Role.VILLAGER,
        faction=Faction.VILLAGER,
        alignment=Alignment.GOOD,
        aliases=["dân", "villager"],
        description="Dân làng bình thường.",
        is_night_active=False,
    ),
}


def get_role_by_alias(alias: str) -> Optional[Role]:
    """Lấy Role từ alias"""
    alias = alias.lower().strip()
    for role, metadata in ROLE_METADATA.items():
        if alias in [a.lower() for a in metadata.aliases]:
            return role
    return None


# ============= GAME STATE ENUM =============
class GameState(Enum):
    """Trạng thái game"""
    WAITING = "WAITING"           # Đợi người chơi join
    GAME_START = "GAME_START"     # Bắt đầu, phát role
    NIGHT_PHASE = "NIGHT_PHASE"   # Ban đêm
    DAY_DISCUSS = "DAY_DISCUSS"   # Ban ngày - thảo luận
    DAY_VOTE = "DAY_VOTE"         # Ban ngày - bỏ phiếu
    ENDED = "ENDED"               # Kết thúc


# ============= PLAYER CLASS =============
@dataclass
class GamePlayer:
    """Thông tin người chơi trong một ván"""
    user_id: int
    username: str
    role: Optional[Role] = None
    is_alive: bool = True
    is_in_game: bool = True
    game: Optional['GameWerewolf'] = None  # Reference to game
    
    # Night actions
    night_target: Optional[int] = None  # ID của người được chọn tác động
    night_action: Optional[str] = None  # Loại hành động: "kill", "heal", "check", etc
    
    # Vote tracking
    votes_for_me: int = 0  # Số phiếu bầu cho người này
    voted_for: Optional[int] = None  # ID người được vote
    
    # Extras
    ammo: int = 0  # Đạn (Xạ Thủ)
    potion_heal: bool = False  # Bình cứu (Phù Thủy)
    potion_kill: bool = False  # Bình giết (Phù Thủy)
    has_bomb: bool = False  # Bom (Kẻ Đặt Bom)
    bomb_target_night: Optional[int] = None  # Target của bom
    revival_available: bool = True  # Hồi sinh (Thầy Đồng)
    trap_on: Optional[int] = None  # Người bị bẫy (Thợ Săn Quái Thú)
    avenge_target: Optional[int] = None  # Mục tiêu báo thù (Kẻ Báo Thù)
    hunter_target: Optional[int] = None  # Mục tiêu mà Thợ Săn lừa
    hunter_own_target: bool = False  # Nếu Thợ Săn lừa chính mục tiêu thì thắng
    
    # Doctor protection history
    doctor_last_protected: Optional[int] = None  # ID người được bác sĩ che chở đêm trước
    
    def get_role_metadata(self) -> Optional[RoleMetadata]:
        """Lấy metadata của role"""
        if self.role:
            return ROLE_METADATA.get(self.role)
        return None


# ============= GAME CLASS =============
@dataclass
class GameWerewolf:
    """Quản lý trạng thái game Ma Sói"""
    guild_id: int
    channel_id: int
    min_players: int = 4  # Số người chơi tối thiểu
    wolf_thread_id: Optional[int] = None  # Thread ID cho cuộc họp sói ban đêm
    created_at: datetime = field(default_factory=datetime.now)
    state: GameState = GameState.WAITING
    
    players: dict[int, GamePlayer] = field(default_factory=dict)  # user_id -> GamePlayer
    night_count: int = 0
    day_count: int = 0
    round: int = 1  # Đêm/Ngày hiện tại
    
    # Phase timing
    night_duration: int = 45  # giây
    day_discuss_duration: int = 30  # giây
    day_vote_duration: int = 60  # giây
    
    # Dead players tracking
    dead_players: List[int] = field(default_factory=list)  # IDs
    
    # Last night's actions (để display kết quả)
    night_actions_log: dict = field(default_factory=dict)
    
    # Last day's vote result
    lynched_player: Optional[int] = None
    lynch_votes: dict = field(default_factory=dict)  # user_id -> [votes]
    
    # Game messages
    main_channel_msg_id: Optional[int] = None
    night_msg_ids: List[int] = field(default_factory=list)
    
    def get_alive_players(self) -> List[GamePlayer]:
        """Lấy danh sách người chơi còn sống"""
        return [p for p in self.players.values() if p.is_alive and p.is_in_game]
    
    def get_dead_players(self) -> List[GamePlayer]:
        """Lấy danh sách người chơi đã chết"""
        return [p for p in self.players.values() if not p.is_alive and p.is_in_game]
    
    def get_players_by_faction(self, faction: Faction) -> List[GamePlayer]:
        """Lấy người chơi theo phe"""
        return [
            p for p in self.get_alive_players()
            if p.role and ROLE_METADATA[p.role].faction == faction
        ]
    
    def check_win_condition(self) -> Optional[str]:
        """
        Kiểm tra điều kiện thắng.
        Return: "WOLF", "VILLAGE", "SOLO", hoặc None (game tiếp tục)
        """
        alive_wolves = self.get_players_by_faction(Faction.WOLF)
        alive_villagers = [
            p for p in self.get_alive_players()
            if ROLE_METADATA[p.role].faction == Faction.VILLAGER
        ]
        
        # Sói thắng nếu >= Dân Làng
        if len(alive_wolves) >= len(alive_villagers):
            return "WOLF"
        
        # Sói tất cả chết
        if len(alive_wolves) == 0:
            return "VILLAGE"
        
        # TODO: Check solo win conditions (Fool, Hunter, Bomber)
        
        return None
