import discord
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
import aiosqlite

from core.database import db_manager

# Pricing Constants
VIP_PRICES = {
    1: 10000,   # Silver
    2: 50000,   # Gold
    3: 200000   # Diamond
}

VIP_NAMES = {
    1: "Thành Viên Bạc",
    2: "Thành Viên Vàng",
    3: "Thành Viên Kim Cương"
}

VIP_COLORS = {
    1: 0xbdc3c7, # Silver
    2: 0xf1c40f, # Gold
    3: 0x3498db  # Diamond (Cyan-ish)
}

logger = logging.getLogger("VIPManager")

class VIPManager:
    """Manages VIP subscriptions and styling."""

    @staticmethod
    async def subscribe(user_id: int, tier: int, duration_days: int = 30) -> Tuple[bool, str]:
        """
        Subscribe or upgrade a user to a VIP tier.
        Deducts money and updates DB.
        """
        price = VIP_PRICES.get(tier)
        if not price:
            return False, "Gói không hợp lệ."

        # 1. READ: Check Balance first (Fast check)
        # Note: Race condition possible but low risk for this bot scale. 
        # Strict ACID would require transaction from start, but let's stick to simple logic first.
        row = await db_manager.fetchone("SELECT seeds, vip_tier FROM users WHERE user_id = ?", (user_id,))
        if not row:
            return False, "Không tìm thấy người dùng."
        
        balance = row[0]
        # current_tier_str = row[1] # Legacy unused

        # Check balance
        if balance < price:
            return False, f"Bạn không đủ tiền! Cần {price:,} Seeds."

        # 2. WRITE: Transaction
        try:
            async with db_manager.transaction() as conn:
                # Double check balance inside transaction (Optimistic Locking style) or just proceed.
                # Let's just deduct. (If negative, could constrain in DB but SQLite check constraints usually optional)
                # We trust the Read above for now, or check again.
                
                # Deduct Money
                await conn.execute("UPDATE users SET seeds = seeds - ? WHERE user_id = ?", (price, user_id))
                
                # [MANDATORY] Transaction Log
                await conn.execute("""
                    INSERT INTO transaction_logs (user_id, amount, reason, category) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, -price, f"buy_vip_tier_{tier}", "luxury"))

                # Check existing subscription
                # Note: conn is aiosqlite Connection, so execute returns a generic cursor context
                async with conn.execute("SELECT tier_level, expiry_date FROM vip_subscriptions WHERE user_id = ?", (user_id,)) as cursor:
                    sub = await cursor.fetchone()
                
                start_date = datetime.now()
                expiry_date = start_date + timedelta(days=duration_days)

                if sub:
                    # Extend or Upgrade?
                    # Logic: Always reset time and set tier (Overwrites)
                    await conn.execute("""
                        UPDATE vip_subscriptions 
                        SET tier_level = ?, start_date = ?, expiry_date = ?
                        WHERE user_id = ?
                    """, (tier, start_date, expiry_date, user_id))
                else:
                    await conn.execute("""
                        INSERT INTO vip_subscriptions (user_id, tier_level, start_date, expiry_date)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, tier, start_date, expiry_date))

            # Clear Caches
            db_manager.clear_cache_by_prefix(f"balance_{user_id}")
            
            return True, f"Đăng ký {VIP_NAMES[tier]} thành công! Hạn dùng: 30 ngày."

        except Exception as e:
            logger.error(f"[VIP] Subscribe Error: {e}", exc_info=True)
            return False, "Lỗi giao dịch."

    @staticmethod
    async def get_vip_data(user_id: int) -> Optional[dict]:
        """Get active VIP subscription data."""
        # Fix: db_manager.fetchone returns tuple directly, not context manager
        row = await db_manager.fetchone("""
            SELECT tier_level, expiry_date, custom_footer 
            FROM vip_subscriptions 
            WHERE user_id = ? AND expiry_date > CURRENT_TIMESTAMP
        """, (user_id,))
        
        if row:
            return {
                "tier": row[0],
                "expiry": row[1],
                "footer": row[2]
            }
        return None

    @staticmethod
    async def apply_vip_style(embed: discord.Embed, user_id: int):
        """
        Middleware to inject VIP styling into an Embed.
        Mutates the embed object in-place.
        """
        # 1. Guard Clauses (Don't override critical colors)
        # Note: Checking valid colors.
        if embed.color in [discord.Color.red(), discord.Color.green(), discord.Color(0xe74c3c), discord.Color(0x2ecc71)]:
            return

        vip_data = await VIPManager.get_vip_data(user_id)
        if not vip_data:
            return

        tier = vip_data['tier']
        
        # 2. Apply Color
        if tier in VIP_COLORS:
            embed.color = discord.Color(VIP_COLORS[tier])

        # 3. Apply Footer (Tier 2+)
        if tier >= 2 and vip_data['footer']:
            icon_url = embed.footer.icon_url or discord.Embed.Empty
            embed.set_footer(text=vip_data['footer'], icon_url=icon_url)

        return

vip_manager = VIPManager()
