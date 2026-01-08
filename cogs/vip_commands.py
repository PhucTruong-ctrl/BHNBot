"""VIP Commands - Purchase, Leaderboard, and Status display."""

import discord
from discord import app_commands
from discord.ext import commands, tasks
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
        self.vip_expiry_reminder.start()
        logger.info("[VIP] Expiry reminder task started")
    
    async def cog_unload(self):
        self.vip_expiry_reminder.cancel()
        
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
                "🎨 **Giao Diện**: Màu embed bạc, Tiền tố 🥈\n"
                "🎣 **Câu Cá**: 3 cá VIP\n"
                "🎲 **Trò Chơi**: Cược nhanh\n"
                "🌳 **Cây**: +10% XP\n"
                "🐠 **Hồ Cá**: +1 ô trang trí"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🥇 VÀNG - 150,000 Hạt/30 ngày",
            value=(
                "✅ **TẤT CẢ QUYỀN LỢI BẠC +**\n\n"
                "🎣 **Câu Cá**: +5 cá VIP (8 tổng) + Chấm Long Dịch\n"
                "🎲 **Trò Chơi**: Hoàn tiền 3%\n"
                "🌳 **Cây**: Trái phép đặc biệt\n"
                "🐠 **Hồ Cá**: +2 ô trang trí, Nền GIF"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💎 KIM CƯƠNG - 500,000 Hạt/30 ngày",
            value=(
                "✅ **TẤT CẢ QUYỀN LỢI VÀNG +**\n\n"
                "🎣 **Câu Cá**: +7 cá VIP (15 tổng) + Lưới Thần Thánh + Bán nhanh\n"
                "🎲 **Trò Chơi**: Hoàn tiền 5%\n"
                "🌳 **Cây**: Tự động tưới\n"
                "🐠 **Hồ Cá**: +3 ô trang trí, Tự động thăm"
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
                description=f"Top {len(rows)} thành viên VIP",
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
                    except Exception:
                        username = f"User#{user_id}"
                    
                    lines.append(
                        f"{idx}. **{username}**\n"
                        f"   └ {total_days} ngày VIP | {total_spent:,} Hạt đã chi"
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
            except Exception:
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
                        "• Màu embed riêng\n"
                        "• Cá VIP độc quyền\n"
                        "• Vật phẩm đặc biệt\n"
                        "• Hoàn tiền trò chơi"
                    ),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            tier = vip_data['tier']
            config = TIER_CONFIG[tier]
            
            row = await db_manager.fetchrow(
                "SELECT expiry_date, total_vip_days, total_spent "
                "FROM vip_subscriptions WHERE user_id = $1",
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
                        f"**Hạng**: {config['prefix']}\n"
                        f"**Hết hạn**: <t:{expiry_timestamp}:R> ({days_left} ngày)\n"
                        f"**Tổng ngày VIP**: {total_days} ngày\n"
                        f"**Tổng chi tiêu**: {total_spent:,} Hạt"
                    ),
                    inline=False
                )
            
            perks = []
            if tier >= 1:
                perks.append("✅ Màu embed riêng " + config['prefix'])
                perks.append(f"✅ {3 if tier == 1 else 8 if tier == 2 else 15} cá VIP")
            if tier >= 2:
                perks.append("✅ Chấm Long Dịch (vật phẩm)")
                perks.append("✅ Hoàn tiền 3% trò chơi")
            if tier >= 3:
                perks.append("✅ Lưới Thần Thánh (vật phẩm)")
                perks.append("✅ Hoàn tiền 5% trò chơi")
            
            embed.add_field(
                name="🎁 Quyền Lợi Hiện Tại",
                value="\n".join(perks),
                inline=False
            )
            
            milestones = [
                (30, "Huy Hiệu Ủng Hộ"),
                (100, "Màu Vĩnh Viễn"),
                (365, "Bảng Vàng Danh Vọng"),
                (730, "Giảm Giá 50% Trọn Đời")
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
            except Exception:
                logger.error(f"[VIP_STATUS] Failed to send error message")
    
    # ==================== VIP EXPIRY REMINDER TASK ====================
    
    @tasks.loop(hours=24)
    async def vip_expiry_reminder(self):
        from cogs.aquarium.constants import VIP_NAMES
        
        now = datetime.now(timezone.utc)
        three_days_later = now + timedelta(days=3)
        four_days_later = now + timedelta(days=4)
        
        logger.info("[VIP_REMINDER] Starting daily check...")
        
        rows = await db_manager.fetchall(
            "SELECT user_id, tier_level, expiry_date "
            "FROM vip_subscriptions "
            "WHERE expiry_date BETWEEN $1 AND $2",
            (three_days_later, four_days_later)
        )
        
        if not rows:
            logger.info("[VIP_REMINDER] No users expiring in 3 days")
            return
        
        success_count = 0
        for row in rows:
            user_id, tier, expiry = row
            try:
                user = await self.bot.fetch_user(user_id)
                
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                days_left = (expiry - now).days
                
                tier_name = VIP_NAMES.get(tier, f"Tier {tier}")
                
                embed = discord.Embed(
                    title="⚠️ VIP SẮP HẾT HẠN",
                    description=f"VIP **{tier_name}** của bạn còn **{days_left} ngày**!",
                    color=0xFF6B6B
                )
                embed.add_field(
                    name="Gia hạn ngay",
                    value="Dùng `/thuongluu b` để gia hạn VIP và nhận thêm 30 ngày!",
                    inline=False
                )
                embed.add_field(
                    name="Lợi ích VIP",
                    value="• Hoàn tiền khi chơi Bầu Cua\n• Tự động tưới cây\n• Cá VIP đặc biệt\n• Chủ đề hồ cá riêng",
                    inline=False
                )
                embed.set_footer(text="Cảm ơn bạn đã ủng hộ server! 💎")
                
                await user.send(embed=embed)
                success_count += 1
                logger.info(f"[VIP_REMINDER] Sent to user {user_id}, {days_left} days left")
                
            except discord.Forbidden:
                logger.warning(f"[VIP_REMINDER] Cannot DM user {user_id} (DMs closed)")
            except Exception as e:
                logger.error(f"[VIP_REMINDER] Error for user {user_id}: {e}")
        
        logger.info(f"[VIP_REMINDER] Completed. Sent {success_count}/{len(rows)} reminders")
    
    @vip_expiry_reminder.before_loop
    async def before_vip_reminder(self):
        await self.bot.wait_until_ready()


class VIPConfirmModal(discord.ui.Modal, title="Xác nhận mua VIP"):
    """Confirmation modal before VIP purchase."""
    
    confirm_input = discord.ui.TextInput(
        label="Nhập 'xacnhan' để mua",
        placeholder="xacnhan",
        required=True,
        max_length=10
    )
    
    def __init__(self, user_id: int, bot, tier: int, cost: int, parent_view):
        super().__init__()
        self.user_id = user_id
        self.bot = bot
        self.tier = tier
        self.cost = cost
        self.parent_view = parent_view
        self.tier_names = {1: "Bạc 🥈", 2: "Vàng 🥇", 3: "Kim Cương 💎"}
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm_input.value.lower().strip() != "xacnhan":
            await interaction.response.send_message(
                "❌ Nhập sai! Hãy nhập đúng 'xacnhan' để xác nhận mua.",
                ephemeral=True
            )
            return
        
        await self.parent_view._execute_purchase(interaction, self.tier, self.cost)


class VIPPurchaseView(discord.ui.View):
    """UI for VIP purchase confirmation."""
    
    def __init__(self, user_id: int, bot):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.bot = bot
        
    @discord.ui.button(label="Mua Bạc (50k)", style=discord.ButtonStyle.secondary, emoji="🥈")
    async def buy_silver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_confirmation(interaction, 1, 50000)
    
    @discord.ui.button(label="Mua Vàng (150k)", style=discord.ButtonStyle.primary, emoji="🥇")
    async def buy_gold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_confirmation(interaction, 2, 150000)
    
    @discord.ui.button(label="Mua Kim Cương (500k)", style=discord.ButtonStyle.success, emoji="💎")
    async def buy_diamond(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_confirmation(interaction, 3, 500000)
    
    @discord.ui.button(label="❌ Hủy", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Đã hủy mua VIP.", embed=None, view=None)
        self.stop()
    
    async def _show_confirmation(self, interaction: discord.Interaction, tier: int, cost: int):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải giao dịch của bạn!", ephemeral=True)
            return
        
        modal = VIPConfirmModal(self.user_id, self.bot, tier, cost, self)
        await interaction.response.send_modal(modal)
    
    async def _execute_purchase(self, interaction: discord.Interaction, tier: int, cost: int):
        """Process VIP purchase transaction."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải giao dịch của bạn!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        user_id = interaction.user.id
        
        try:
            async with db_manager.transaction() as conn:
                # CHECK EXISTING VIP FIRST - Block downgrade attempts BEFORE deducting seeds
                existing_vip = await conn.fetchrow(
                    "SELECT tier_level, expiry_date FROM vip_subscriptions "
                    "WHERE user_id = $1 AND expiry_date > NOW()",
                    user_id
                )
                
                if existing_vip:
                    old_tier = existing_vip[0] or 0
                    tier_names = {1: "Bạc 🥈", 2: "Vàng 🥇", 3: "Kim Cương 💎"}
                    
                    if tier < old_tier:
                        await interaction.followup.send(
                            f"❌ Bạn đang có **VIP {tier_names[old_tier]}**!\n"
                            f"Không thể mua gói thấp hơn. Chọn gói cao hơn hoặc chờ hết hạn để gia hạn.",
                            ephemeral=True
                        )
                        return
                
                # Check balance INSIDE transaction to prevent race condition
                balance_row = await conn.fetchrow(
                    "SELECT seeds FROM users WHERE user_id = $1 FOR UPDATE",
                    user_id
                )
                balance = balance_row[0] if balance_row else 0
                
                if balance < cost:
                    await interaction.followup.send(
                        f"❌ Không đủ Hạt!\nCần: {cost:,} | Có: {balance:,}",
                        ephemeral=True
                    )
                    return
                
                await conn.execute(
                    "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                    cost, user_id
                )
                
                await conn.execute(
                    "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                    user_id, -cost, f'vip_purchase_tier_{tier}', 'vip'
                )
                
                existing = await conn.fetchrow(
                    "SELECT expiry_date, total_vip_days, total_spent, tier_level FROM vip_subscriptions WHERE user_id = $1",
                    user_id
                )
                
                now = datetime.now(timezone.utc)
                expiry = now + timedelta(days=30)
                
                if existing:
                    old_expiry = existing[0]
                    old_tier = existing[3] or 0
                    
                    if old_expiry and old_expiry > now:
                        expiry = old_expiry + timedelta(days=30)
                    
                    total_days = (existing[1] or 0) + 30
                    total_spent = (existing[2] or 0) + cost
                    
                    # Only upgrade tier, never downgrade
                    new_tier = max(tier, old_tier)
                    
                    await conn.execute(
                        "UPDATE vip_subscriptions SET tier_level = $1, expiry_date = $2, "
                        "total_vip_days = $3, total_spent = $4 WHERE user_id = $5",
                        new_tier, expiry, total_days, total_spent, user_id
                    )
                else:
                    await conn.execute(
                        "INSERT INTO vip_subscriptions "
                        "(user_id, tier_level, start_date, expiry_date, total_vip_days, total_spent) "
                        "VALUES ($1, $2, $3, $4, $5, $6)",
                        user_id, tier, now, expiry, 30, cost
                    )
            
            VIPEngine.clear_cache(user_id)
            
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
            logger.error(f"[VIP] Purchase failed: {e}", exc_info=True)
            await interaction.followup.send("❌ Giao dịch thất bại!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VIPCommandsCog(bot))
