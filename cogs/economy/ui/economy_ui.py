"""
Economy UI - Discord embed builders for economy system.

Handles all presentation logic for economy features.
"""

import discord
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any


class EconomyUI:
    """UI builders for economy system."""
    
    @staticmethod
    def create_daily_reward_embed(reward_data: Dict[str, Any], user: discord.User) -> discord.Embed:
        """Create daily reward embed."""
        embed = discord.Embed(
            title="☀️ Chào buổi sáng!",
            color=discord.Color.gold()
        )
        
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        
        reward_text = f"**{reward_data['base_reward']}** hạt cơ bản"
        if reward_data['streak_bonus'] > 0:
            reward_text += f"\n**+{reward_data['streak_bonus']}** hạt streak (ngày {reward_data['current_streak']})"
        embed.add_field(name="🎁 Phần thưởng", value=reward_text, inline=False)
        
        streak_display = f"🔥 **{reward_data['current_streak']}** ngày liên tiếp"
        if reward_data['has_protection']:
            streak_display += "\n🛡️ Bảo vệ streak: **Có sẵn**"
        else:
            streak_display += "\n🛡️ Bảo vệ streak: Đạt 7 ngày để mở"
        embed.add_field(name="📊 Streak", value=streak_display, inline=False)
        
        if reward_data['protection_used']:
            embed.add_field(
                name="⚠️ Đã dùng bảo vệ!",
                value="Bạn quên 1 ngày nhưng streak được giữ nhờ bảo vệ.",
                inline=False
            )
        elif reward_data['streak_lost']:
            embed.add_field(
                name="💔 Streak đã reset",
                value=f"Bạn mất streak {reward_data['previous_streak']} ngày do nghỉ quá lâu.",
                inline=False
            )
        
        embed.add_field(name="💰 Hạt hiện tại", value=f"**{reward_data.get('current_balance', 'N/A')}**", inline=False)
        embed.set_footer(text="Tip: Đạt 20 ngày để nhận tối đa +100 hạt/ngày!")
        
        return embed
    
    @staticmethod
    def create_leaderboard_embed(top_users: List[Tuple[int, str, int]], requester: discord.User) -> discord.Embed:
        """Create leaderboard embed."""
        if not top_users:
            embed = discord.Embed(
                title="🏆 Bảng Xếp Hạng Hạt",
                description="❌ Chưa có ai trong bảng xếp hạng!",
                color=discord.Color.gold()
            )
            return embed
        
        # Get top 1 user details
        top1_id, top1_name, top1_balance = top_users[0]
        
        embed = discord.Embed(
            title="👑 **BẢNG VÀNG ĐẠI GIA (TOP RICH)** 👑",
            description="Vin danh những đại gia giàu nhất **Bên Hiên Nhà**.",
            color=0xFFD700,  # Gold
            timestamp=datetime.now()
        )
        
        # Try to get top 1 user avatar (would need bot instance, skip for now)
        
        # Top 3 (VIP Section)
        top3_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx in range(min(3, len(top_users))):
            user_id, username, balance = top_users[idx]
            medal = medals[idx]
            top3_text += f"{medal} **{username}**\n╚═ **{balance:,}** 🌱\n\n"
        
        embed.add_field(name="🏆 **TAM ĐẠI PHÚ HỘ**", value=top3_text, inline=True)
        
        # Ranks 4-10 (List Section)
        if len(top_users) > 3:
            others_text = "```yaml\n"  # Use yaml for semantic highlighting
            for idx in range(3, len(top_users)):
                user_id, username, balance = top_users[idx]
                display_name = (username[:12] + '..') if len(username) > 12 else username
                others_text += f"{idx+1}. {display_name:<14} {balance:,} 🌱\n"
            others_text += "```"
            embed.add_field(name="📜 **CHIẾN THẦN TÍCH LŨY**", value=others_text, inline=False)
        
        embed.set_footer(text=f"Yêu cầu bởi {requester.name}", icon_url=requester.display_avatar.url)
        
        return embed
    
    @staticmethod
    def create_simple_leaderboard_embed(top_users: List[Tuple[int, str, int]]) -> discord.Embed:
        """Create simple leaderboard embed."""
        embed = discord.Embed(
            title="🏆 Bảng Xếp Hạng Hạt",
            color=discord.Color.gold()
        )
        
        if not top_users:
            embed.description = "❌ Chưa có ai trong bảng xếp hạng!"
            return embed
        
        ranking_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (user_id, username, seeds) in enumerate(top_users, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}."
            ranking_text += f"{medal} **{username}** - {seeds} Hạt\n"
        
        embed.description = ranking_text
        embed.set_footer(text="Cập nhật hàng ngày • Xếp hạng dựa trên tổng hạt")
        
        return embed
    
    @staticmethod
    def create_admin_add_seeds_embed(user: discord.User, amount: int, new_balance: int, admin: discord.User) -> discord.Embed:
        """Create admin add seeds confirmation embed."""
        embed = discord.Embed(
            title="Thêm Hạt Thành Công",
            color=discord.Color.green()
        )
        embed.add_field(name="Người nhận", value=f"**{user.name}**", inline=False)
        embed.add_field(name="Hạt thêm", value=f"**+{amount}**", inline=True)
        embed.add_field(name="Số dư mới", value=f"**{new_balance}**", inline=True)
        embed.set_footer(text=f"Thực hiện bởi {admin.name}")
        
        return embed
    
    @staticmethod
    def create_error_embed(title: str, description: str) -> discord.Embed:
        """Create error embed."""
        return discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red()
        )
    
    @staticmethod
    def create_success_embed(title: str, description: str) -> discord.Embed:
        """Create success embed."""
        return discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=discord.Color.green()
        )
