"""VIP Commands - Purchase, Leaderboard, and Status display."""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from typing import Optional

from database_manager import db_manager, get_user_balance, add_seeds
from core.services.vip_service import VIPEngine, TIER_CONFIG
from core.logger import setup_logger

logger = setup_logger("VIPCommands", "cogs/vip_commands.log")

class VIPCommandsCog(commands.Cog):
    """VIP purchase, leaderboard, and status commands."""
    
    def __init__(self, bot):
        self.bot = bot
        
    # ==================== /thuongluu COMMAND ====================
    
    @app_commands.command(name="thuongluu", description="Hệ thống VIP Thượng Lưu")
    @app_commands.describe(action="Chọn hành động (b=mua, t=top, s=status)")
    @app_commands.choices(action=[
        app_commands.Choice(name="🛒 Mua VIP (b)", value="b"),
        app_commands.Choice(name="🏆 Bảng xếp hạng (t)", value="t"),
        app_commands.Choice(name="📊 Trạng thái của bạn (s)", value="s")
    ])
    async def thuongluu(self, interaction: discord.Interaction, action: str):
        """VIP system - buy, leaderboard, or status."""
        
        if action == "b":
            await self._buy_vip(interaction)
        elif action == "t":
            await self._vip_leaderboard(interaction)
        elif action == "s":
            await self._vip_status(interaction)
    
    async def _buy_vip(self, interaction: discord.Interaction):
        """Purchase VIP subscription."""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        embed = discord.Embed(
            title="💎 MUA GÓI VIP THƯỢNG LƯU",
            description="Chọn gói phù hợp với bạn:",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🥈 BẠC - 50,000 Hạt/30 ngày",
            value=(
                "🎨 **Giao Diện**: Màu embed bạc, Prefix 🥈\n"
                "🎣 **Câu Cá**: 3 cá VIP\n"
                "🎲 **Minigames**: Quick Bet\n"
                "🌳 **Cây**: +10% XP\n"
                "🐠 **Aquarium**: +1 ô decor"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🥇 VÀNG - 150,000 Hạt/30 ngày",
            value=(
                "✅ **TẤT CẢ PERKS BẠC +**\n\n"
                "🎣 **Câu Cá**: +5 cá VIP (8 total) + Chấm Long Dịch\n"
                "🎲 **Minigames**: Cashback 3%\n"
                "🌳 **Cây**: Magic Fruit drop\n"
                "🐠 **Aquarium**: +2 ô decor, GIF bg"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💎 KIM CƯƠNG - 500,000 Hạt/30 ngày",
            value=(
                "✅ **TẤT CẢ PERKS VÀNG +**\n\n"
                "🎣 **Câu Cá**: +7 cá VIP (15 total) + Lưới Thần Thánh + Quick Sell\n"
                "🎲 **Minigames**: Cashback 5%\n"
                "🌳 **Cây**: Auto-Water\n"
                "🐠 **Aquarium**: +3 ô decor, Auto-Visit"
            ),
            inline=False
        )
        
        view = VIPPurchaseView(user_id, self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    async def _vip_leaderboard(self, interaction: discord.Interaction):
        """Display VIP leaderboard."""
        try:
            logger.info(f"[VIP_LEADERBOARD] Command started")
            await interaction.response.defer()
            
            logger.info(f"[VIP_LEADERBOARD] Fetching VIP users from database")
            rows = await db_manager.fetchall(
                "SELECT user_id, tier_level, total_vip_days, total_spent "
                "FROM vip_subscriptions "
                "WHERE expiry_date > NOW() "
                "ORDER BY total_vip_days DESC "
                "LIMIT 20",
                ()
            )
            
            if not rows:
                await interaction.followup.send("❌ Chưa có VIP nào trên server!", ephemeral=True)
                return
            
            tiers = {3: [], 2: [], 1: []}
            for row in rows:
                tier = row[1]
                if tier in tiers:
                    tiers[tier].append(row)
            
            embed = discord.Embed(
                title="🏆 BẢNG XẾP HẠNG VIP",
                description=f"Top {len(rows)} VIP users",
                color=discord.Color.blue()
            )
            
            tier_emoji = {1: "🥈", 2: "🥇", 3: "💎"}
            tier_names = {1: "BẠC", 2: "VÀNG", 3: "KIM CƯƠNG"}
            
            for tier in [3, 2, 1]:
                if not tiers[tier]:
                    continue
                    
                lines = []
                for idx, (user_id, tier_level, total_days, total_spent) in enumerate(tiers[tier][:5], 1):
                    try:
                        user = await self.bot.fetch_user(user_id)
                        username = user.display_name
                    except:
                        username = f"User#{user_id}"
                    
                    lines.append(
                        f"{idx}. **{username}**\n"
                        f"   └ {total_days} ngày VIP | {total_spent:,} Hạt spent"
                    )
                
                embed.add_field(
                    name=f"{tier_emoji[tier]} {tier_names[tier]} ({len(tiers[tier])} người)",
                    value="\n".join(lines) if lines else "Không có",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"[VIP_LEADERBOARD] Error: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"❌ Lỗi khi tải bảng xếp hạng: {str(e)}", ephemeral=True)
            except:
                logger.error(f"[VIP_LEADERBOARD] Failed to send error message")
    
    async def _vip_status(self, interaction: discord.Interaction):
        """Display user's VIP status."""
        try:
            logger.info(f"[VIP_STATUS] Command started for user {interaction.user.id}")
            await interaction.response.defer(ephemeral=True)
            
            user_id = interaction.user.id
            logger.info(f"[VIP_STATUS] Fetching VIP data for {user_id}")
            vip_data = await VIPEngine.get_vip_data(user_id)
            logger.info(f"[VIP_STATUS] VIP data: {vip_data}")
            
            if not vip_data:
                embed = discord.Embed(
                    title="❌ BẠN CHƯA CÓ VIP",
                    description=(
                        "Dùng `/thuongluu b` để mua gói VIP!\n\n"
                        "**Lợi ích VIP:**\n"
                        "• Custom màu embed\n"
                        "• Cá VIP độc quyền\n"
                        "• Buff consumables\n"
                        "• Cashback minigames"
                    ),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            tier = vip_data['tier']
            config = TIER_CONFIG[tier]
            
            row = await db_manager.fetchrow(
                "SELECT expiry_date, total_vip_days, total_spent "
                "FROM vip_subscriptions WHERE user_id = ?",
                (user_id,)
            )
            
            # PostgreSQL returns datetime object directly
            expiry_date = row[0] if row else None
            total_days = row[1] if row else 0
            total_spent = row[2] if row else 0
            
            embed = discord.Embed(
                title=f"{config['prefix']} THÔNG TIN VIP - {interaction.user.display_name}",
                color=config['color']
            )
            
            if expiry_date:
                days_left = (expiry_date - datetime.now(timezone.utc)).days
                expiry_timestamp = int(expiry_date.timestamp())
                
                embed.add_field(
                    name="📊 Trạng Thái",
                    value=(
                        f"**Tier**: {config['prefix']}\n"
                        f"**Hết hạn**: <t:{expiry_timestamp}:R> ({days_left} ngày)\n"
                        f"**Tổng ngày VIP**: {total_days} ngày\n"
                        f"**Tổng chi tiêu**: {total_spent:,} Hạt"
                    ),
                    inline=False
                )
            
            perks = []
            if tier >= 1:
                perks.append("✅ Custom embed màu " + config['prefix'])
                perks.append(f"✅ {3 if tier == 1 else 8 if tier == 2 else 15} cá VIP")
            if tier >= 2:
                perks.append("✅ Chấm Long Dịch consumable")
                perks.append("✅ Cashback 3% minigames")
            if tier >= 3:
                perks.append("✅ Lưới Thần Thánh consumable")
                perks.append("✅ Cashback 5% minigames")
            
            embed.add_field(
                name="🎁 Quyền Lợi Hiện Tại",
                value="\n".join(perks),
                inline=False
            )
            
            milestones = [
                (30, "Supporter Badge"),
                (100, "Permanent Color"),
                (365, "Hall of Fame"),
                (730, "Lifetime Discount 50%")
            ]
            
            milestone_text = []
            for days, reward in milestones:
                if total_days >= days:
                    milestone_text.append(f"✅ {days} ngày → {reward}")
                else:
                    milestone_text.append(f"🔒 {days} ngày → {reward}")
            
            embed.add_field(
                name="🏅 Cột Mốc Tích Lũy",
                value="\n".join(milestone_text),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"[VIP_STATUS] Error: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    f"❌ Lỗi khi kiểm tra VIP status: {str(e)}",
                    ephemeral=True
                )
            except:
                logger.error(f"[VIP_STATUS] Failed to send error message")


class VIPPurchaseView(discord.ui.View):
    """UI for VIP purchase confirmation."""
    
    def __init__(self, user_id: int, bot):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.bot = bot
        
    @discord.ui.button(label="Mua Bạc (50k)", style=discord.ButtonStyle.secondary, emoji="🥈")
    async def buy_silver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._process_purchase(interaction, 1, 50000)
    
    @discord.ui.button(label="Mua Vàng (150k)", style=discord.ButtonStyle.primary, emoji="🥇")
    async def buy_gold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._process_purchase(interaction, 2, 150000)
    
    @discord.ui.button(label="Mua Kim Cương (500k)", style=discord.ButtonStyle.success, emoji="💎")
    async def buy_diamond(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._process_purchase(interaction, 3, 500000)
    
    @discord.ui.button(label="❌ Hủy", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Đã hủy mua VIP.", embed=None, view=None)
        self.stop()
    
    async def _process_purchase(self, interaction: discord.Interaction, tier: int, cost: int):
        """Process VIP purchase transaction."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải giao dịch của bạn!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        user_id = interaction.user.id
        balance = await get_user_balance(user_id)
        
        if balance < cost:
            await interaction.followup.send(
                f"❌ Không đủ Hạt!\nCần: {cost:,} | Có: {balance:,}",
                ephemeral=True
            )
            return
        
        try:
            async with db_manager.transaction() as conn:
                await conn.execute(
                    "UPDATE users SET seeds = seeds - ? WHERE user_id = ?",
                    (cost, user_id)
                )
                
                await conn.execute(
                    "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES (?, ?, ?, ?)",
                    (user_id, -cost, f'vip_purchase_tier_{tier}', 'vip')
                )
                
                existing = await conn.fetchrow(
                    "SELECT expiry_date, total_vip_days, total_spent FROM vip_subscriptions WHERE user_id = ?",
                    (user_id,)
                )
                
                now = datetime.now(timezone.utc)
                expiry = now + timedelta(days=30)
                
                if existing:
                    # PostgreSQL returns datetime object directly
                    old_expiry = existing[0]
                    if old_expiry > now:
                        expiry = old_expiry + timedelta(days=30)
                    
                    total_days = existing[1] + 30
                    total_spent = existing[2] + cost
                    
                    await conn.execute(
                        "UPDATE vip_subscriptions SET tier_level = ?, expiry_date = ?, "
                        "total_vip_days = ?, total_spent = ? WHERE user_id = ?",
                        (tier, expiry.isoformat(), total_days, total_spent, user_id)
                    )
                else:
                    await conn.execute(
                        "INSERT INTO vip_subscriptions "
                        "(user_id, tier_level, start_date, expiry_date, total_vip_days, total_spent) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, tier, now.isoformat(), expiry.isoformat(), 30, cost)
                    )
            
            VIPEngine._vip_cache.pop(user_id, None)
            
            tier_names = {1: "Bạc 🥈", 2: "Vàng 🥇", 3: "Kim Cương 💎"}
            
            embed = discord.Embed(
                title="✅ MUA VIP THÀNH CÔNG!",
                description=f"Bạn đã mua gói **VIP {tier_names[tier]}**",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Chi phí", value=f"{cost:,} Hạt", inline=True)
            embed.add_field(name="💾 Còn lại", value=f"{balance - cost:,} Hạt", inline=True)
            embed.add_field(name="📅 Hết hạn", value=f"<t:{int(expiry.timestamp())}:R>", inline=False)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"[VIP] Purchase: user={user_id} tier={tier} cost={cost}")
            
            self.stop()
            
        except Exception as e:
            logger.error(f"[VIP] Purchase failed: {e}")
            await interaction.followup.send("❌ Giao dịch thất bại!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VIPCommandsCog(bot))
