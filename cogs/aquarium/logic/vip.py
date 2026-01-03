
from typing import Tuple, Optional, Dict, List
from datetime import datetime, timedelta
import logging
import discord
import random

from core.database import db_manager # SQLite
from ..models import VIPSubscription # Postgres
from ..constants import VIP_PRICES, VIP_NAMES, VIP_COLORS

logger = logging.getLogger("VIPEngine")

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
        "border": "◽", # White medium square
        "merchant": "Cửa Hàng Hải Sản",
        "location": "Siêu Thị Hải Sản Cao Cấp",
        "footer_icon": None
    },
    2: {
        "prefix": "🥇 [VÀNG]",
        "color": 0xF1C40F,
        "border": "🔸", # Small orange diamond
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
        "footer_icon": "https://cdn.discordapp.com/emojis/123456789.png" # Placeholder or use User Avatar
    }
}

class VIPEngine:
    """Manages VIP subscriptions and styling (Hybrid)."""

    @staticmethod
    async def subscribe(user_id: int, tier: int, duration_days: int = 30) -> Tuple[bool, str]:
        """
        Subscribe or upgrade.
        Deducts Hạt (SQLite) -> Updates VIP (Postgres).
        """
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

            return True, f"Đăng ký {VIP_NAMES[tier]} thành công! Hạn dùng: 30 ngày."

        except Exception as e:
            logger.error(f"[VIP_ERROR] User {user_id}: {e}", exc_info=True)
            return False, "Lỗi hệ thống."

    @staticmethod
    async def get_vip_data(user_id: int) -> Optional[Dict]:
        """Get active VIP data (Postgres)."""
        sub = await VIPSubscription.get_or_none(user_id=user_id)
        if sub and sub.expiry_date > datetime.now(sub.expiry_date.tzinfo):
             return {
                "tier": sub.tier_level,
                "expiry": sub.expiry_date,
                "footer": sub.custom_footer
            }
        return None

    @staticmethod
    async def create_vip_embed(
        user: discord.User, 
        title: str, 
        description: str, 
        vip_data: Optional[Dict] = None
    ) -> discord.Embed:
        """Factory method to create a Premium VIP Embed."""
        
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
                color=discord.Color.blue() # Default blue
            )
            embed.set_footer(text=f"{user.name} • Member", icon_url=user.display_avatar.url)
            return embed

        # --- VIP VISUALS ---
        
        # 1. Prefix Title
        # e.g. "💎 [KIM CƯƠNG] KẾT QUẢ CÂU CÁ"
        # Strip existing emojis if needed/requested, but usually title passed is clean or contains base info
        clean_title = title.replace("🎣", "").strip() 
        final_title = f"{config['prefix']} {clean_title.upper()}"
        
        # 3. Create Embed
        embed = discord.Embed(
            title=final_title,
            description=description,
            color=discord.Color(config['color'])
        )
        
        # 4. Premium Footer
        # Add merchant location if applicable (e.g. for Sell events)
        # Or random quote
        footer_text = random.choice(VIP_QUOTES)
        
        # Combine with custom user footer if valid (Tier 2+)
        if tier >= 2 and vip_data.get('footer'):
             footer_text = f"{vip_data['footer']} | {footer_text}"

        embed.set_footer(text=footer_text, icon_url=user.display_avatar.url)
        
        # 5. Thumbnail (Optional - maybe user avatar or tier icon)
        # embed.set_thumbnail(url=...) 
        
        return embed

    @staticmethod
    async def apply_vip_style(embed: discord.Embed, user: discord.User):
        """Mutates embed to apply VIP styling (Legacy Support)."""
        # Guard Colors
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
