"""
VIP Service - Core Cross-Module Service
Manages VIP subscriptions, styling, and caching.

Moved from cogs/aquarium/logic/vip.py to prevent dependency hell.
"""

from typing import Tuple, Optional, Dict
from datetime import datetime, timedelta
from core.logging import get_logger
import discord
import random

from core.database import db_manager  # SQLite
# Note: VIPSubscription model imported dynamically to avoid circular imports

logger = get_logger("services_vip_service")

# --- VIP CONFIGURATION ---
VIP_QUOTES = [
    # Wealth & Status
    "Tiền nhiều để làm gì? Để flex.",
    "Ngân hàng gọi em là VIP.",
    "Két sắt không đáy, vibe không giới hạn.",
    "Rich mindset, broke wallet không quen.",
    "Đại gia phố Discord.",
    "Hỏi sao giàu? Vì chăm chỉ... chơi bot.",
    "Tiền là công cụ, flex là nghệ thuật.",
    "Bạn nghèo là do chưa mua VIP thôi.",
    
    # Gen Z Lifestyle
    "Slay everyday, VIP all the way.",
    "Living rent-free in your head.",
    "Main character energy.",
    "Delulu is the solulu.",
    "Chilling như tỷ phú.",
    "No thoughts, head VIP.",
    "Understood the assignment.",
    "Nói ít, flex nhiều.",
    
    # Meme References (2020-2025)
    "Gigachad energy 💪",
    "We're so back.",
    "It's giving... wealthy.",
    "POV: You're rich.",
    "Just like me fr fr.",
    "He's just like me for real.",
    "Ừ thì skill issue.",
    "Cope harder.",
    "L + ratio + VIP.",
    
    # Self-Deprecating Humor
    "Giàu mà tâm hồn vẫn nghèo.",
    "Nhiều tiền nhưng ít não.",
    "VIP nhưng IQ vẫn âm.",
    "Flex thôi chứ thực ra cũng bình thường.",
    "Giàu có nhưng cô đơn.",
    
    # Random Funny
    "Ngày mai ăn gì nhỉ?",
    "Anh em mình ai đó chuyển nhầm 5tr?",
    "Lương về liền hết, VIP remain.",
    "Broke but make it VIP.",
    "Ngày xưa nghèo, giờ nghèo có VIP.",
    "Vẫn ăn mì tôm nhưng là mì tôm VIP.",
    
    # Motivational (But Gen Z)
    "Hustle in silence, flex in Discord.",
    "Grindset sigma male.",
    "Wake up, get bag, repeat.",
    "Passive income go brrr.",
    "NFT hết tiền, còn VIP thôi.",
    "Crypto xuống, tinh thần lên.",
    
    # Premium Vibes
    "Sang chảnh từ trong trứng nước.",
    "Đẳng cấp thượng lưu Discord.",
    "VIP card never expires.",
    "Membership có giá, đẳng cấp vô giá.",
    "Bạn bình thường, tôi extraordinary.",
    "Khác biệt từng pixel.",
    
    # Short & Punchy
    "Built different.",
    "Simply better.",
    "Just VIP things.",
    "Upgrade your life."
]

TIER_CONFIG = {
    1: {
        "prefix": "🥈 [BẠC]",
        "color": 0xBDC3C7,
        "border": "◽",
        "merchant": "Cửa Hàng Hải Sản",
        "location": "Siêu Thị Hải Sản Cao Cấp",
        "footer_icon": None
    },
    2: {
        "prefix": "🥇 [VÀNG]",
        "color": 0xF1C40F,
        "border": "🔸",
        "merchant": "Nhà Hàng 5 Sao",
        "location": "Chuỗi Nhà Hàng Quốc Tế",
        "footer_icon": None 
    },
    3: {
        "prefix": "💎 [KIM CƯƠNG]",
        "color": 0x3498DB,
        "border": "💎",
        "merchant": "Tập Đoàn Xuất Khẩu",
        "location": "Sàn Giao Dịch Thủy Sản Quốc Tế",
        "footer_icon": "https://cdn.discordapp.com/emojis/123456789.png"
    }
}

# --- VIP DATA CACHE (TTL: 5 minutes) ---
_vip_cache: Dict[int, tuple] = {}
_cache_ttl = timedelta(minutes=5)

class VIPEngine:
    """Manages VIP subscriptions and styling (Core Service)."""

    @staticmethod
    async def subscribe(user_id: int, tier: int, duration_days: int = 30) -> Tuple[bool, str]:
        """
        Subscribe or upgrade VIP.
        Deducts Hạt (SQLite) → Updates VIP (Postgres).
        
        Args:
            user_id: Discord user ID
            tier: VIP tier (1=Silver, 2=Gold, 3=Diamond)
            duration_days: Subscription duration
            
        Returns:
            (success: bool, message: str)
        """
        # Import here to avoid circular dependency
        from cogs.aquarium.models import VIPSubscription
        from cogs.aquarium.constants import VIP_PRICES, VIP_NAMES
        
        price = VIP_PRICES.get(tier)
        if not price:
            return False, "Gói không hợp lệ."

        # 1. READ: Check Balance (SQLite)
        rows = await db_manager.fetchone("SELECT seeds FROM users WHERE user_id = $1", (user_id,))
        balance = rows[0] if rows else 0
        
        if balance < price:
            return False, f"Bạn không đủ tiền! Cần {price:,} Hạt Giống."

        try:
            # 2. WRITE: SQLite Transaction (Deduct)
            await db_manager.execute("UPDATE users SET seeds = seeds - ? WHERE user_id = ?", (price, user_id))
            
            # 3. WRITE: Postgres Transaction (VIP)
            start_date = datetime.now()
            expiry_date = start_date + timedelta(days=duration_days)
            
            # Upsert
            sub, created = await VIPSubscription.get_or_create(
                user_id=user_id,
                defaults={'tier_level': tier, 'expiry_date': expiry_date}
            )
            
            if not created:
                sub.tier_level = tier
                sub.start_date = start_date
                sub.expiry_date = expiry_date
                await sub.save()
            
            # Invalidate cache
            _vip_cache.pop(user_id, None)
            logger.info(f"[VIP_SUBSCRIBE] User {user_id} subscribed to Tier {tier} for {duration_days} days")

            return True, f"Đăng ký {VIP_NAMES[tier]} thành công! Hạn dùng: 30 ngày."

        except Exception as e:
            logger.error(f"[VIP_ERROR] User {user_id}: {e}", exc_info=True)
            return False, "Lỗi hệ thống."

    @staticmethod
    async def get_vip_data(user_id: int, use_cache: bool = True) -> Optional[Dict]:
        """
        Get active VIP data with TTL caching (5 minutes).
        
        Args:
            user_id: Discord user ID
            use_cache: Whether to use cache (default True)
            
        Returns:
            Dict with tier, expiry, footer if VIP active, else None
        """
        # Import here to avoid circular dependency
        from cogs.aquarium.models import VIPSubscription
        
        # Check cache first
        if use_cache and user_id in _vip_cache:
            cached_data, cached_time = _vip_cache[user_id]
            if datetime.now() - cached_time < _cache_ttl:
                return cached_data
        
        # Cache miss or expired → Query DB
        sub = await VIPSubscription.get_or_none(user_id=user_id)
        if sub and sub.expiry_date > datetime.now(sub.expiry_date.tzinfo):
            data = {
                "tier": sub.tier_level,
                "expiry": sub.expiry_date,
                "footer": sub.custom_footer
            }
            _vip_cache[user_id] = (data, datetime.now())
            return data
        
        # No active VIP
        _vip_cache[user_id] = (None, datetime.now())
        return None

    @staticmethod
    async def create_vip_embed(
        user: discord.User, 
        title: str, 
        description: str, 
        vip_data: Optional[Dict] = None,
        footer_text: Optional[str] = None,
        footer_icon: Optional[str] = None
    ) -> discord.Embed:
        """
        Factory method to create Premium VIP Embed with smart footer handling.
        
        Args:
            user: Discord user object
            title: Embed title (emojis auto-removed, tier prefix added for VIPs)
            description: Embed description
            vip_data: Pre-fetched VIP data (optional, will auto-fetch if None)
            footer_text: Custom footer text (overrides random quote for pagination/game state)
            footer_icon: Custom footer icon URL (optional)
            
        Returns:
            discord.Embed with VIP styling applied
        """
        # If no VIP data provided, fetch it
        if vip_data is None:
            vip_data = await VIPEngine.get_vip_data(user.id)
            
        tier = vip_data['tier'] if vip_data else 0
        config = TIER_CONFIG.get(tier)
        
        # --- NON-VIP / EXPIRED USER ---
        if not config:
            # Return standard embed
            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue()
            )
            # Smart footer for non-VIPs
            if footer_text:
                embed.set_footer(text=footer_text, icon_url=footer_icon or user.display_avatar.url)
            else:
                embed.set_footer(text=f"{user.name} • Member", icon_url=user.display_avatar.url)
            return embed

        # --- VIP VISUALS ---
        
        # 1. Prefix Title (auto-remove common emojis)
        clean_title = title.replace("🎣", "").replace("🎲", "").replace("🃏", "").replace("🌳", "").replace("🐠", "").strip()
        final_title = f"{config['prefix']} {clean_title.upper()}"
        
        # 2. Create Embed
        embed = discord.Embed(
            title=final_title,
            description=description,
            color=discord.Color(config['color'])
        )
        
        # 3. SMART FOOTER (Priority system)
        if footer_text:
            # Priority 1: Developer-provided footer (e.g. "Page 1/5", "Đang suy nghĩ...")
            embed.set_footer(text=footer_text, icon_url=footer_icon or user.display_avatar.url)
        else:
            # Priority 2: VIP random quote (only if no custom footer)
            quote = random.choice(VIP_QUOTES)
            
            # Combine with custom user footer if Tier 2+
            if tier >= 2 and vip_data.get('footer'):
                quote = f"{vip_data['footer']} | {quote}"
            
            embed.set_footer(text=quote, icon_url=user.display_avatar.url)
        
        return embed

    @staticmethod
    async def apply_vip_style(embed: discord.Embed, user: discord.User):
        """
        Mutates embed to apply VIP styling (Legacy Support).
        
        DEPRECATED: Use create_vip_embed() instead for new code.
        """
        # Guard Colors (don't override semantic colors)
        if embed.color in [discord.Color.red(), discord.Color.green(), discord.Color.dark_red()]:
            return

        vip = await VIPEngine.get_vip_data(user.id)
        if not vip:
            return

        tier = vip['tier']
        config = TIER_CONFIG.get(tier)
        if not config:
            return

        # Apply Color
        embed.color = discord.Color(config['color'])

        # Apply Title Prefix if not present
        if embed.title and config['prefix'] not in embed.title:
            embed.title = f"{config['prefix']} {embed.title}"

        # Apply Footer
        if tier >= 1:
            # Random quote
            quote = random.choice(VIP_QUOTES)
            if tier >= 2 and vip['footer']:
                quote = vip['footer']
            
            icon = user.display_avatar.url
            embed.set_footer(text=quote, icon_url=icon)

    @staticmethod
    def clear_cache(user_id: Optional[int] = None):
        """Clear VIP cache for a specific user or all users."""
        global _vip_cache
        if user_id:
            _vip_cache.pop(user_id, None)
            logger.info(f"[VIP_CACHE] Cleared cache for user {user_id}")
        else:
            _vip_cache.clear()
            logger.info("[VIP_CACHE] Cleared all VIP cache")
