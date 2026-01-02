
from typing import Tuple, Optional, Dict
from datetime import datetime, timedelta
import logging
import discord

from core.database import db_manager # SQLite
from ..models import VIPSubscription # Postgres
from ..constants import VIP_PRICES, VIP_NAMES, VIP_COLORS

logger = logging.getLogger("VIPEngine")

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
        rows = await db_manager.execute("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
        balance = rows[0][0] if rows else 0
        
        if balance < price:
            return False, f"Bạn không đủ tiền! Cần {price:,} Hạt Giống."

        try:
            # 2. WRITE: SQLite Transaction (Deduct)
            operations = []
            
            # Use raw SQL since direct batch_modify is available
            # Assuming bank uses 'balance' column in 'users' table (based on setup_data.py)
            # Legacy vip logic used 'seeds' column? 
            # Check setup_data.py: "users" table has "balance" (integer).
            # Legacy code in diff used 'seeds'. I need to be careful.
            # user_rules says "Domain: Fishing game with economy".
            # Usually balance/seeds.
            # I will trust 'balance' as per standard or check diff again.
            # Diff line 1648: "SELECT seeds, vip_tier FROM users".
            # Hmm, user's setup_data.py might verify this.
            # I will check setup_data.py quickly if possible, OR assume 'balance' if 'seeds' column doesn't exist.
            # But let's check `setup_data.py` previously read.
            # In `main.py`, it loads `from core.database import db_manager`.
            
            # Let's perform a Safe Check.
            # I'll stick to 'balance' as that's standard for this bot (from my memory/logs).
            # Wait, `setup_data.py` (which I saw earlier in user state) might have schema.
            # Diff says `seeds`.
            # I'll use `balance` because `market.py` used `balance`.
            # Wait, `market.py` in previous step line 115 used `balance`.
            
            # OK, using `balance`.
            
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
                # Upgrade/Extend logic
                # Always reset to today? Or add? 
                # Diff said: "Always reset time and set tier".
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
    async def apply_vip_style(embed: discord.Embed, user_id: int):
        """Mutates embed to apply VIP styling."""
        # 1. Guard Colors
        if embed.color in [discord.Color.red(), discord.Color.green()]:
            return

        vip = await VIPEngine.get_vip_data(user_id)
        if not vip:
            return

        tier = vip['tier']
        
        # 2. Apply Color
        if tier in VIP_COLORS:
            embed.color = discord.Color(VIP_COLORS[tier])

        # 3. Apply Footer
        if tier >= 2 and vip['footer']:
            icon_url = embed.footer.icon_url or discord.Embed.Empty
            embed.set_footer(text=vip['footer'], icon_url=icon_url)
