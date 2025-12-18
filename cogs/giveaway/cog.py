import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import json
import asyncio
from database_manager import db_manager
from .views import GiveawayJoinView
from .models import Giveaway
from .constants import *
from .helpers import end_giveaway

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {} # {guild_id: {code: uses}}
        self.check_giveaways_task.start()

    def cog_unload(self):
        self.check_giveaways_task.cancel()

    @tasks.loop(minutes=1)
    async def check_giveaways_task(self):
        try:
            now = discord.utils.utcnow()
            # Fetch active giveaways that have ended
            # SQLite stores datetime as string usually? Or helpers handles it?
            # aiosqlite/sqlite3 default adapter might store as string "YYYY-MM-DD HH:MM:SS..."
            # We can select all active and check in python, or try sqlite datetime func
            active_gas = await db_manager.execute("SELECT * FROM giveaways WHERE status = 'active'")
            for row in active_gas:
                ga = Giveaway.from_db(row)
                # Ensure ga.end_time is timezone aware if now is
                end_time = ga.end_time
                if isinstance(end_time, str):
                    try:
                        end_time = datetime.datetime.fromisoformat(end_time)
                    except:
                        # Fallback parsing if format differs
                        try:
                            end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f%z")
                        except:
                            # Last resort
                            continue
                
                # Make naive aware if needed
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=datetime.timezone.utc)
                
                if now >= end_time:
                    await end_giveaway(ga.message_id, self.bot)
        except Exception as e:
            print(f"[Giveaway] Task error: {e}")

    @check_giveaways_task.before_loop
    async def before_check_task(self):
        await self.bot.wait_until_ready()

    async def cog_load(self):
        print("[Giveaway] Loading module...")
        
        # 1. Restore Active Giveaways Views
        active_giveaways = await db_manager.execute("SELECT * FROM giveaways WHERE status = 'active'")
        count = 0
        for row in active_giveaways:
            ga = Giveaway.from_db(row)
            view = GiveawayJoinView(ga.message_id, ga.requirements)
            self.bot.add_view(view)
            count += 1
        print(f"[Giveaway] Restored {count} active giveaway views.")

        # 2. Cache Invites
        for guild in self.bot.guilds:
            await self.cache_invites(guild)

    async def cache_invites(self, guild):
        try:
            invites = await guild.invites()
            self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites}
        except Exception as e:
            print(f"[Giveaway] Could not cache invites for {guild.name}: {e}")

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
        
        print(f"[Giveaway] {member.name} joined. Inviter: {inviter.name}. Valid: {is_valid}")

        # Save to DB
        # user_invites: inviter_id, joined_user_id, is_valid, created_at
        try:
            await db_manager.modify(
                "INSERT OR IGNORE INTO user_invites (inviter_id, joined_user_id, is_valid) VALUES (?, ?, ?)",
                (inviter.id, member.id, 1 if is_valid else 0)
            )
        except Exception as e:
            print(f"[Giveaway] Error saving invite: {e}")

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

    @app_commands.command(name="gacreate", description="Tạo Giveaway với các điều kiện")
    @app_commands.describe(
        prize="Phần thưởng",
        duration="Thời gian (vd: 1h, 30m, 1d)",
        winners="Số người thắng (mặc định 1)",
        req_invite="Số invite yêu cầu (Acc > 7 ngày)",
        req_rod="Cấp cần câu yêu cầu (1-5)",
        cost="Giá vé tham gia (Hạt)"
    )
    async def create_giveaway(self, interaction: discord.Interaction, 
                              prize: str, duration: str, winners: int = 1,
                              req_invite: int = 0, req_rod: int = 0, cost: int = 0):
        
        # 1. Parse Duration
        seconds = 0
        unit = duration[-1].lower()
        value = int(duration[:-1])
        if unit == 's': seconds = value
        elif unit == 'm': seconds = value * 60
        elif unit == 'h': seconds = value * 3600
        elif unit == 'd': seconds = value * 86400
        else:
            return await interaction.response.send_message("❌ Định dạng thời gian không hợp lệ! (vd: 1h, 30m)", ephemeral=True)
            
        end_time = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        
        # 2. Build Requirements
        reqs = {}
        if req_invite > 0: reqs["min_invites"] = req_invite
        if req_rod > 0: reqs["min_rod_level"] = req_rod
        if cost > 0: reqs["cost"] = cost
        
        # 3. Create Embed
        embed = discord.Embed(title="🎉 GIVEAWAY!", description=f"**Phần thưởng:** {prize}\n**Kết thúc:** <t:{int(end_time.timestamp())}:R> ({duration})", color=COLOR_GIVEAWAY)
        embed.add_field(name="Số lượng giải", value=f"{winners} giải")
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
        
        if req_invite > 0: embed.add_field(name="Điều kiện", value=f"✉️ **{req_invite} Valid Invites**", inline=True)
        if req_rod > 0: embed.add_field(name="Điều kiện", value=f"🎣 **Cần Câu Lv{req_rod}**", inline=True)
        if cost > 0: embed.add_field(name="Vé tham gia", value=f"💰 **{cost} Hạt**", inline=True)

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
        view = GiveawayJoinView(msg.id, reqs)
        await msg.edit(view=view)
        
        # 6. Save to DB
        await db_manager.modify(
            """INSERT INTO giveaways 
            (message_id, channel_id, guild_id, host_id, prize, winners_count, end_time, requirements, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg.id, msg.channel.id, interaction.guild.id, interaction.user.id, prize, winners, end_time, json.dumps(reqs), 'active')
        )
        
        await interaction.edit_original_response(content="✅ Đã tạo Giveaway thành công!")

        # 7. Schedule End (Optional: using asyncio.sleep if short duration, or a task loop)
        # For robustness, a background task loop checking DB is better, but for simple MVP, sleep is ok if short.
        # But if bot restarts, sleep is lost.
        # Ideally, we have a task loop `check_giveaways`.
        # I'll add a simple loop in cog_load or a separate task.


    # Task loop handles checking end times


async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))

