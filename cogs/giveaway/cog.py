import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import json
import asyncio
from typing import Optional
from database_manager import db_manager
from .views import GiveawayJoinView, GiveawayResultView
from .models import Giveaway
from .constants import *
from .helpers import end_giveaway
from core.logger import setup_logger

logger = setup_logger("GiveawayCog", "cogs/giveaway.log")

# Create giveaway command group
giveaway_group = app_commands.Group(name="giveaway", description="Quản lý giveaway")

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {} # {guild_id: {code: uses}}
        self.update_tasks = {}  # {giveaway_id: asyncio.Task} for delayed embed updates
        self.check_giveaways_task.start()

    def cog_unload(self):
        self.check_giveaways_task.cancel()

    @tasks.loop(minutes=1)
    async def check_giveaways_task(self):
        try:
            now = discord.utils.utcnow()
            active_gas = await db_manager.execute("SELECT * FROM giveaways WHERE status = 'active'")
            for row in active_gas:
                try:
                    ga = Giveaway.from_db(row)
                    if now >= ga.end_time:
                        await end_giveaway(ga.message_id, self.bot)
                except Exception as e:
                     logger.error(f"Error processing giveaway {row[0]}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Task error: {e}", exc_info=True)

    @check_giveaways_task.before_loop
    async def before_check_task(self):
        await self.bot.wait_until_ready()

    async def cog_load(self):
        logger.info("Loading module...")
        
        # 1. Restore Active Giveaways Views
        active_giveaways = await db_manager.execute("SELECT * FROM giveaways WHERE status = 'active'")
        count = 0
        for row in active_giveaways:
            try:
                ga = Giveaway.from_db(row)
                # Check if message still exists before restoring view
                try:
                    channel = self.bot.get_channel(ga.channel_id)
                    if channel:
                        await channel.fetch_message(ga.message_id)
                        view = GiveawayJoinView(ga.message_id, ga.requirements, self)
                        self.bot.add_view(view)
                        count += 1
                    else:
                        logger.info(f"Channel {ga.channel_id} not found for giveaway {ga.message_id}, skipping view restore")
                except:
                    logger.info(f"Message {ga.message_id} not found, skipping view restore")
            except Exception as e:
                logger.error(f"Error restoring view for giveaway {row[0]}: {e}", exc_info=True)
        logger.info(f"Restored {count} active giveaway views.")

        # 2. Restore Ended Giveaway Result Views (for reroll/end functionality)
        ended_giveaways = await db_manager.execute("SELECT * FROM giveaways WHERE status = 'ended'")
        result_count = 0
        for row in ended_giveaways:
            try:
                ga = Giveaway.from_db(row)
                # Get current winners from participants (assuming winners are still in the pool)
                participants = await db_manager.execute(
                    "SELECT user_id FROM giveaway_participants WHERE giveaway_id = ? ORDER BY id LIMIT ?",
                    (ga.message_id, ga.winners_count)
                )
                current_winners = [row[0] for row in participants]
                
                # Try to find the result message (it's a reply to the original giveaway message)
                try:
                    channel = self.bot.get_channel(ga.channel_id)
                    if channel:
                        original_msg = await channel.fetch_message(ga.message_id)
                        # Get the last reply (assuming it's the result message)
                        async for message in original_msg.channel.history(after=original_msg, limit=5):
                            if message.author == self.bot.user and message.embeds:
                                embed = message.embeds[0]
                                if "GIVEAWAY KẾT QUẢ" in embed.title:
                                    # This is likely the result message
                                    view = GiveawayResultView(ga.message_id, current_winners, self.bot)
                                    self.bot.add_view(view)
                                    result_count += 1
                                    break
                except Exception as e:
                    logger.error(f"Could not restore result view for giveaway {ga.message_id}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error restoring result view for giveaway {row[0]}: {e}", exc_info=True)
        logger.info(f"Restored {result_count} ended giveaway result views.")
        for guild in self.bot.guilds:
            await self.cache_invites(guild)

    async def update_giveaway_embed(self, giveaway_id: int):
        """Update giveaway embed with current participant count and any updated data"""
        try:
            logger.info(f"Updating embed for giveaway {giveaway_id}")
            
            # Get participant count
            participants = await db_manager.execute(
                "SELECT COUNT(*) FROM giveaway_participants WHERE giveaway_id = ?",
                (giveaway_id,)
            )
            count = participants[0][0] if participants else 0
            logger.info(f"Participant count for {giveaway_id}: {count}")
            
            # Get full giveaway data
            row = await db_manager.fetchone("SELECT * FROM giveaways WHERE message_id = ?", (giveaway_id,))
            if not row:
                logger.info(f"No giveaway data found for {giveaway_id}")
                return
            
            ga = Giveaway.from_db(row)
            channel = self.bot.get_channel(ga.channel_id)
            if not channel:
                logger.info(f"Channel {ga.channel_id} not found")
                return
            
            # Get message
            try:
                msg = await channel.fetch_message(giveaway_id)
                logger.info(f"Fetched message {giveaway_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch message {giveaway_id}: {e}")
                return
            
            # Create Discord timestamp for relative time display
            unix_timestamp = int(ga.end_time.timestamp())
            time_string = f"<t:{unix_timestamp}:R>"
            
            # Create new embed with updated data
            embed = discord.Embed(
                title=f"🎉 GIVEAWAY NÈ MẤY BÀ DÔ HÚP ĐI!",
                description=f"**Giải thưởng:** {ga.prize}\n**Số người thắng:** {ga.winners_count}\n\n**Kết thúc:** {time_string}\n\nNhấn nút dưới để tham gia!",
                color=COLOR_GIVEAWAY
            )
            
            # Add participant count
            embed.add_field(name="Số người tham gia", value=str(count), inline=True)
            
            # Add requirements if any
            if ga.requirements:
                req_text = ""
                if ga.requirements.get("min_invites", 0) > 0:
                    req_text += f"• {ga.requirements['min_invites']} Invites (Acc > 7 ngày)\n"
                if ga.requirements.get("min_rod_level", 0) > 0:
                    req_text += f"• Cần Câu Cấp {ga.requirements['min_rod_level']}\n"
                if ga.requirements.get("cost", 0) > 0:
                    req_text += f"• {ga.requirements['cost']} Hạt\n"
                if req_text:
                    embed.add_field(name="Yêu cầu tham gia", value=req_text.strip(), inline=False)
            
            embed.set_footer(text=f"Giveaway ID: {giveaway_id}")
            
            # Set image if available
            if ga.image_url:
                embed.set_image(url=ga.image_url)
            
            await msg.edit(embed=embed)
            logger.info(f"Successfully updated embed for giveaway {giveaway_id}")
            
        except Exception as e:
            logger.error(f"Error updating embed for giveaway {giveaway_id}: {e}", exc_info=True)
        finally:
            # Remove from update tasks
            if giveaway_id in self.update_tasks:
                del self.update_tasks[giveaway_id]

    def schedule_embed_update(self, giveaway_id: int):
        """Schedule embed update with 5 second delay, cancelling previous if exists"""
        import asyncio
        
        # Cancel existing task if any
        if giveaway_id in self.update_tasks:
            self.update_tasks[giveaway_id].cancel()
        
        # Create new task
        async def delayed_update():
            await asyncio.sleep(5)
            await self.update_giveaway_embed(giveaway_id)
        
        task = asyncio.create_task(delayed_update())
        self.update_tasks[giveaway_id] = task

    async def cache_invites(self, guild):
        try:
            invites = await guild.invites()
            self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites}
        except Exception as e:
            logger.info(f"Could not cache invites for {guild.name}: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.guild.id not in self.invite_cache:
            self.invite_cache[invite.guild.id] = {}
        self.invite_cache[invite.guild.id][invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        if invite.guild.id in self.invite_cache:
             self.invite_cache[invite.guild.id].pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        inviter = await self.find_inviter(member)
        if not inviter: return

        # Check account age
        account_age = (discord.utils.utcnow() - member.created_at).days
        is_valid = account_age >= 7
        
        logger.info(f"{member.name} joined. Inviter: {inviter.name}. Valid: {is_valid}")

        # Save to DB
        # user_invites: inviter_id, joined_user_id, is_valid, created_at
        try:
            await db_manager.modify(
                "INSERT OR IGNORE INTO user_invites (inviter_id, joined_user_id, is_valid) VALUES (?, ?, ?)",
                (inviter.id, member.id, 1 if is_valid else 0)
            )
        except Exception as e:
            logger.error(f"Error saving invite: {e}", exc_info=True)

    async def find_inviter(self, member):
        guild = member.guild
        if guild.id not in self.invite_cache:
            return None
        
        old_invites = self.invite_cache[guild.id]
        try:
            new_invites_list = await guild.invites()
        except:
            return None
            
        new_invites = {inv.code: inv.uses for inv in new_invites_list}
        self.invite_cache[guild.id] = new_invites # Update cache
        
        # Compare
        for code, uses in new_invites.items():
            old_uses = old_invites.get(code, 0)
            if uses > old_uses:
                # Found the invite used
                for inv in new_invites_list:
                    if inv.code == code:
                        return inv.inviter
        return None

    @giveaway_group.command(name="test_inv", description="[Admin/Test] Thêm invite ảo để test")
    @app_commands.checks.has_permissions(administrator=True)
    async def gatest_invite(self, interaction: discord.Interaction, target: discord.User, amount: int = 1):
        """Add fake invites for testing"""
        try:
            import random
            await interaction.response.defer(ephemeral=True)
            
            for _ in range(amount):
                # Generate random dummy user ID for the "joined" person
                dummy_id = random.randint(100000000000000000, 999999999999999999)
                await db_manager.modify(
                    "INSERT INTO user_invites (inviter_id, joined_user_id, is_valid) VALUES (?, ?, 1)",
                    (target.id, dummy_id)
                )
            
            # Clear cache so new value is fetched immediately
            db_manager.clear_cache_by_prefix(f"invites_{target.id}")
            
            await interaction.followup.send(f"✅ Đã thêm {amount} invite ảo cho {target.mention}")
        except Exception as e:
             await interaction.followup.send(f"❌ Lỗi: {e}")

    @giveaway_group.command(name="end", description="[Admin] Kết thúc Giveaway ngay lập tức")
    @app_commands.checks.has_permissions(administrator=True)
    async def gaend_now(self, interaction: discord.Interaction):
        """End a giveaway immediately by selecting from active giveaways."""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get all active giveaways in this guild
            active_gas = await db_manager.execute(
                "SELECT message_id, prize, end_time FROM giveaways WHERE status = 'active' AND guild_id = ? ORDER BY end_time ASC",
                (interaction.guild.id,)
            )
            
            if not active_gas:
                return await interaction.followup.send("❌ Không có Giveaway nào đang hoạt động!")
            
            # Limit to 25 options for Discord select menu
            active_gas = active_gas[:25]
            
            # Create select menu options
            options = []
            for idx, (msg_id, prize, end_time) in enumerate(active_gas, 1):
                # Create short code like GA001, GA002, etc
                code = f"GA{idx:03d}"
                label = f"{code} - {prize[:50]}"  # Truncate prize if too long
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=str(msg_id),
                        description=f"Kết thúc lúc: {end_time[:16] if isinstance(end_time, str) else end_time}"
                    )
                )
            
            from .views import GiveawayEndSelectView
            view = GiveawayEndSelectView(self.bot, options)
            embed = discord.Embed(
                title="🛑 Kết Thúc Giveaway",
                description="Chọn Giveaway bạn muốn kết thúc ngay lập tức:",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in gaend_now: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Có lỗi xảy ra: {e}")

    @giveaway_group.command(name="create", description="Tạo Giveaway với các điều kiện")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        prize="Phần thưởng",
        duration="Thời gian (vd: 1h, 30m, 1d)",
        winners="Số người thắng (mặc định 1)",
        req_invite="Số invite yêu cầu (Acc > 7 ngày)",
        req_rod="Cấp cần câu yêu cầu (1-5)",
        cost="Giá vé tham gia (Hạt)",
        image_url="Link ảnh/gif để hiển thị (tùy chọn)"
    )
    async def create_giveaway(self, interaction: discord.Interaction, 
                              prize: str, duration: str, winners: int = 1,
                              req_invite: int = 0, req_rod: int = 0, cost: int = 0, image_url: str = None):
        
        # 1. Parse Duration
        seconds = 0
        try:
            if len(duration) < 2:
                raise ValueError("Too short")
            unit = duration[-1].lower()
            value = int(duration[:-1])
            if unit == 's': seconds = value
            elif unit == 'm': seconds = value * 60
            elif unit == 'h': seconds = value * 3600
            elif unit == 'd': seconds = value * 86400
            else:
                raise ValueError("Invalid unit")
        except ValueError:
            return await interaction.response.send_message("❌ Định dạng thời gian không hợp lệ! (vd: 1h, 30m, 10s)", ephemeral=True)
            
        end_time = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        
        # 2. Build Requirements
        reqs = {}
        if req_invite > 0: reqs["min_invites"] = req_invite
        if req_rod > 0: reqs["min_rod_level"] = req_rod
        if cost > 0: reqs["cost"] = cost
        
        # 3. Create Embed
        embed = discord.Embed(title="🎉 GIVEAWAY NÈ! DÔ LỤM LÚA!", description=f"**Phần thưởng:** {prize}\n**Kết thúc:** <t:{int(end_time.timestamp())}:R> ({duration})", color=COLOR_GIVEAWAY)
        embed.add_field(name="Số lượng giải", value=f"{winners} giải")
        embed.add_field(name="Số người tham gia", value="0", inline=True)
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
        
        if req_invite > 0: embed.add_field(name="Điều kiện", value=f"✉️ **{req_invite} Lời mời hợp lệ (Mời người vào server)**", inline=True)
        if req_rod > 0: embed.add_field(name="Điều kiện", value=f"🎣 **Cần Câu Lv{req_rod}**", inline=True)
        if cost > 0: embed.add_field(name="Vé tham gia", value=f"💰 **{cost} Hạt**", inline=True)

        if image_url:
            embed.set_image(url=image_url)

        # 4. Send Message (Temporary ID)
        # We need to send first to get ID
        # View needs ID to be persistent. 
        # Chicken and egg problem?
        # No, we can insert DB first with placeholder message_id? No message_id is PK.
        # We can send message with Dummy View, then update it?
        # Or we can generate a unique ID for the giveaway internally, but message_id is convenient.
        
        # Solution: Send message without View first (or disabled view), get ID, then Edit message with View.
        await interaction.response.send_message("⏳ Đang tạo...", ephemeral=True)
        
        msg = await interaction.channel.send(embed=embed)
        
        # 5. Create View with real ID
        view = GiveawayJoinView(msg.id, reqs, self)
        await msg.edit(view=view)
        
        # 6. Save to DB
        await db_manager.modify(
            """INSERT INTO giveaways 
            (message_id, channel_id, guild_id, host_id, prize, winners_count, end_time, requirements, status, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg.id, msg.channel.id, interaction.guild.id, interaction.user.id, prize, winners, end_time, json.dumps(reqs), 'active', image_url)
        )
        
        logger.info(f"Created giveaway ID {msg.id} by {interaction.user} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}) - Prize: {prize}, Winners: {winners}, Duration: {duration}, Requirements: {reqs}")
        
        await interaction.edit_original_response(content="✅ Đã tạo Giveaway thành công!")

        # 7. Schedule End (Optional: using asyncio.sleep if short duration, or a task loop)
        # For robustness, a background task loop checking DB is better, but for simple MVP, sleep is ok if short.
        # But if bot restarts, sleep is lost.
        # Ideally, we have a task loop `check_giveaways`.
        # I'll add a simple loop in cog_load or a separate task.


    # Task loop handles checking end times


async def setup(bot):
    bot.tree.add_command(giveaway_group)
    await bot.add_cog(GiveawayCog(bot))

