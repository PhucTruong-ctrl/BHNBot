import discord
from discord.ext import commands, tasks
from discord import app_commands
import time
import asyncio
import logging
import random
from datetime import datetime

from core import checks
from core.errors import UserFeedbackError
from .core import logic, models, constants 
# REMOVED helpers import that caused crash
from .services.action_service import ActionService
from .ui import embeds
from .mechanics.events import roll_fishing_event, roll_npc_event

# Function imports from existing modules
from .commands.sell import sell_fish_action as _sell_fish_impl
from .commands.bucket import (
    open_chest_action as _open_chest_impl,
    recycle_trash_action as _recycle_trash_impl,
    use_phan_bon_action as _use_phan_bon_impl,
    view_collection_action as _view_collection_impl
)
from .commands.craft import (
    hiente_action as _hiente_impl,
    chetao_action as _chetao_impl,
    dosong_action as _dosong_impl,
    ghepbando_action as _ghepbando_impl
)
from .commands.rod import nangcap_action as _nangcap_impl
from .commands.legendary import legendary_hall_of_fame_action as _legendary_hall_of_fame_impl
from .commands.admin import trigger_event_action as _trigger_event_impl
from .utils.global_event_manager import GlobalEventManager

from database_manager import get_user_balance, add_seeds, increment_stat, get_stat
from .constants import ROD_LEVELS, WORM_COST, ItemKeys

logger = logging.getLogger("FishingCog")

class FishingCog(commands.Cog):
    """Refactored Fishing Cog (Phase 2.5). Controller Only."""

    def __init__(self, bot):
        self.bot = bot
        self.global_event_manager = GlobalEventManager(bot)
        self.action_service = ActionService(bot, self) # Injected Service
        
        self.fishing_cooldown = {} 
        self.pending_fishing_event = {}
        self.avoid_event_users = {}
        self.lucky_buff_users = {}
        
        # Disaster State (Consider moving to a StateService)
        self.is_server_frozen = False
        self.freeze_end_time = 0
        self.current_disaster = None
        self.disaster_channel = None
        self.disaster_effect_end_time = 0
        self.disaster_fine_amount = 0
        self.disaster_cooldown_penalty = 0
        
        self.cleanup_stale_state.start()
        
    async def cog_load(self):
        logger.info("Fishing Cog Loaded (Fixed Phase 2.5)")

    def cog_unload(self):
        self.global_event_manager.unload()
        self.cleanup_stale_state.cancel()

    @tasks.loop(hours=1)
    async def cleanup_stale_state(self):
        current_time = time.time()
        expired = [uid for uid, t in list(self.fishing_cooldown.items()) if t < current_time]
        for uid in expired: del self.fishing_cooldown[uid]

    @cleanup_stale_state.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # ==================== MAIN ACTION ====================
    @commands.hybrid_command(name="cauca", description="Câu cá giải trí kiếm tiền")
    async def fish(self, ctx):
        await self._fish_action(ctx)

    @app_commands.command(name="fish", description="Fishing command (English alias)")
    async def fish_slash(self, interaction: discord.Interaction):
        await self._fish_action(interaction)

    async def _fish_action(self, ctx_or_int):
        try:
            is_slash = isinstance(ctx_or_int, discord.Interaction)
            user = ctx_or_int.user if is_slash else ctx_or_int.author
            
            if is_slash:
                if not ctx_or_int.response.is_done():
                    await ctx_or_int.response.defer()
                channel = ctx_or_int.channel
                ctx = ctx_or_int
            else:
                channel = ctx_or_int.channel
                ctx = ctx_or_int

            # 1. PRE-FLIGHT CHECKS (Delegated to Service)
            username = user.name
            if await self.action_service.check_server_freeze(user.id, username, is_slash, ctx):
                return

            inventory = await self.bot.inventory.get_all(user.id)
            if await self.action_service.check_bucket_limit(user.id, inventory, username, is_slash, ctx):
                return

            # 2. ROD & REPAIR
            rod_lvl, rod_durability, rod_config, wait_time = await logic.get_cast_parameters(user.id)
            
            # Service Call
            rod_durability, repair_msg, is_broken = await self.action_service.check_and_repair_rod(
                user.id, rod_lvl, rod_durability, rod_config, channel, username
            )
            if is_broken:
                msg = f"❌ **{username} ơi!** Cần câu đã gãy! Hãy dùng `/fix` hoặc bán ve chai."
                if is_slash: await ctx.followup.send(msg)
                else: await ctx.reply(msg)
                return

            # 3. COOLDOWN
            if user.id in self.fishing_cooldown:
                remaining = self.fishing_cooldown[user.id] - time.time()
                if remaining > 0:
                    msg = f"⏱️ Chờ chút! <t:{int(self.fishing_cooldown[user.id])}:R>"
                    if is_slash: await ctx.followup.send(msg, ephemeral=True)
                    else: await ctx.reply(msg, delete_after=remaining)
                    return
            
            # 4. PRE-FISHING EVENT ROLL (Mechanic)
            user_luck = await self.get_user_total_luck(user.id)
            fishing_event = await roll_fishing_event(self, user.id, rod_lvl, user_luck)
            
            # Terminal Event Check (Mất lượt, gãy cần, v.v.)
            if fishing_event["triggered"] and fishing_event.get("is_terminal"):
                 await logic.process_fishing_failure(user.id, rod_lvl, fishing_event, self.bot.inventory)
                 
                 evt_embed = embeds.create_event_embed(
                     title=fishing_event.get("message", "Sự cố!"),
                     description="Bạn đã gặp xui xẻo và không thể tiếp tục câu lần này.",
                     event_type="bad"
                 )
                 if is_slash: await ctx.followup.send(embed=evt_embed)
                 else: await ctx.reply(embed=evt_embed)
                 
                 # Minimal penalty cooldown
                 self.fishing_cooldown[user.id] = time.time() + 5
                 return

            # 5. ANIMATION (UI)
            has_worm = inventory.get(ItemKeys.MOI, 0) > 0
            
            # Append good event message
            if fishing_event["triggered"] and fishing_event["category"] == "good":
                 repair_msg = (repair_msg or "") + f"\n✨ **{fishing_event['message']}**"
                 
            embed = embeds.create_casting_embed(
                username, wait_time, rod_config, rod_lvl, rod_durability, 
                has_worm=has_worm, auto_bought=False, repair_msg=repair_msg
            )
            
            if is_slash: msg = await ctx.followup.send(embed=embed)
            else: msg = await ctx.send(embed=embed)

            await asyncio.sleep(wait_time)

            # 6. TRANSACTION (Core Logic)
            result = await logic.execute_cast_transaction(
                user_id=user.id,
                guild_id=channel.guild.id if channel.guild else 0,
                bot_inventory=self.bot.inventory,
                cog_instance=self,
                rod_lvl=rod_lvl,
                rod_config=rod_config,
                forced_event=fishing_event if fishing_event["triggered"] else None
            )

            # 7. POST-PROCESS
            if result["status"] == "broken_rod":
                await channel.send(f"❌ **{username} ơi!** Cần câu gãy trong lúc câu!")
                return
            
            cd_penalty = self.disaster_cooldown_penalty if time.time() < self.disaster_effect_end_time else 0
            self.fishing_cooldown[user.id] = result["cooldown_end"] + cd_penalty
            
            # 8. DISPLAY RESULTS
            
            # A. PRE-FISHING EVENT (Significant)
            if fishing_event["triggered"] and fishing_event["category"] != "neutral" and not fishing_event.get("avoided"):
                 # Determine visual style
                 evt_type = fishing_event["category"]
                 evt_embed = embeds.create_event_embed(
                     title=fishing_event.get("message"),
                     description="",
                     event_type=evt_type
                 )
                 await channel.send(embed=evt_embed)
            
            # B. MAIN CATCH
            res_embed = embeds.create_result_embed(
                username, 
                result["caught_items"], 
                result["xp_gained"], 
                result.get("money_gained", 0)
            )
            await channel.send(embed=res_embed)
            
            # C. NPC EVENT
            npc_data = await roll_npc_event(self, user.id, result)
            if npc_data:
                 npc_embed = embeds.create_event_embed(
                     title=f"Gặp Gỡ: {npc_data['base_data']['name']}",
                     description=npc_data['base_data']['description'] + "\n\n*(Tính năng tương tác đang phát triển...)*",
                     event_type="neutral"
                 )
                 await channel.send(embed=npc_embed)

        except Exception as e:
            logger.error(f"FATAL FISH ACTION ERROR: {e}", exc_info=True)
            if 'channel' in locals() and channel:
                await channel.send(f"⚠️ Lỗi hệ thống: {e}")

    # ==================== DELEGATED COMMANDS ====================
    @commands.command(name="banca")
    async def sell_fish(self, ctx, *, args=None):
        await _sell_fish_impl(self, ctx_or_interaction=ctx, fish_types=args)

    @app_commands.command(name="sell", description="Bán cá")
    async def sell_slash(self, interaction: discord.Interaction, type: str = None):
        await _sell_fish_impl(self, ctx_or_interaction=interaction, fish_types=type)

    # --- INVENTORY ---
    @commands.command(name="moruong")
    async def open_chest(self, ctx, amount: int = 1):
        await _open_chest_impl(self, ctx_or_interaction=ctx, amount=amount)

    @app_commands.command(name="open_chest", description="Mở rương kho báu")
    async def open_chest_slash(self, interaction: discord.Interaction, amount: int = 1):
        await _open_chest_impl(self, ctx_or_interaction=interaction, amount=amount)
        
    @commands.command(name="taiche", aliases=["vechai"])
    async def recycle_trash(self, ctx):
        await _recycle_trash_impl(self, ctx_or_interaction=ctx)

    @commands.command(name="bosuutap")
    async def view_collection(self, ctx):
        await _view_collection_impl(self, ctx_or_interaction=ctx, user_id=ctx.author.id, username=ctx.author.name)

    @commands.command(name="chetao")
    async def craft_rod(self, ctx):
        await _chetao_impl(self, ctx_or_interaction=ctx, item_key="tinh_cau", is_slash=False)
        
    @app_commands.command(name="chetao", description="Chế tạo vật phẩm")
    async def chetao_slash(self, interaction: discord.Interaction, item_key: str):
        await _chetao_impl(self, ctx_or_interaction=interaction, item_key=item_key, is_slash=True)

    @commands.command(name="nangcap")
    async def upgrade_rod(self, ctx):
        await _nangcap_impl(self, ctx_or_interaction=ctx)
        
    @app_commands.command(name="nangcap", description="Nâng cấp cần câu")
    async def upgrade_rod_slash(self, interaction: discord.Interaction):
        await _nangcap_impl(self, ctx_or_interaction=interaction)

    @commands.command(name="hiente")
    async def hiente(self, ctx, fish_key: str = None):
        await _hiente_impl(self, ctx_or_interaction=ctx, fish_key=fish_key, is_slash=False)

    @app_commands.command(name="hiente", description="Hiến tế cá")
    async def hiente_slash(self, interaction: discord.Interaction, fish_key: str):
        await _hiente_impl(self, ctx_or_interaction=interaction, fish_key=fish_key, is_slash=True)

    @commands.command(name="dosong")
    async def dosong(self, ctx):
        await _dosong_impl(self, ctx_or_interaction=ctx, is_slash=False)

    @commands.command(name="ghepbando")
    async def ghepbando(self, ctx):
        await _ghepbando_impl(self, ctx_or_interaction=ctx, is_slash=False)

    @commands.command(name="bonphan", aliases=["be"])
    async def use_phan_bon(self, ctx):
        await _use_phan_bon_impl(self, ctx_or_interaction=ctx)

    @commands.hybrid_command(name="bxh_cauca", description="Xem bảng xếp hạng câu cá")
    async def leaderboard(self, ctx):
        await self.bot.get_cog("LeaderboardCog").show_leaderboard(ctx, "fishing") 
    
    # --- ADMIN / DEBUG COMMANDS ---
    @commands.command(name="trigger", aliases=["sukiencauca"])
    @checks.is_admin()
    async def trigger_event(self, ctx, event_type: str, event_key: str):
         await _trigger_event_impl(self, ctx_or_interaction=ctx, target_user_id=ctx.author.id, event_type=event_type, event_key=event_key, is_slash=False)

    @commands.command(name="legendarytrigger", description="TEST: Trigger legendary fish encounter (Admin Only)")
    @checks.is_owner()
    async def debug_legendary_trigger(self, ctx, fish_key: str = None):
        """Debug command to trigger legendary fish encounter"""
        user_id = ctx.author.id
        channel = ctx.channel
        guild_id = ctx.guild.id
        
        # Select a legendary fish (random or specified)
        legendary_fish = None
        if fish_key:
            for fish in LEGENDARY_FISH:
                if fish['key'].lower() == fish_key.lower():
                    legendary_fish = fish
                    break
            if not legendary_fish:
                await ctx.reply(f"❌ Cá huyền thoại '{fish_key}' không tồn tại!")
                return
        else:
            legendary_fish = random.choice(LEGENDARY_FISH)
        
        rod_level, rod_durability = await logic.get_rod_data(user_id)
        rod_config = ROD_LEVELS.get(rod_level, ROD_LEVELS[1])
        
        legendary_embed = discord.Embed(
            title=f"⚠️ {ctx.author.display_name} - CẢNH BÁO: DÂY CÂU CĂNG CỰC ĐỘ!",
            description=f"🌊 Có một con quái vật đang cắn câu!\n💥 Nó đang kéo bạn xuống nước!\n\n**{legendary_fish['emoji']} {apply_display_glitch(legendary_fish['name'])}**\n_{legendary_fish['description']}_",
            color=discord.Color.dark_red()
        )
        legendary_embed.add_field(name="⚔️ CHUẨN BỊ ĐẤU BOSS!", value=f"Độ bền cần câu: {rod_durability}/{rod_config['durability']}\nCấp độ cần: {rod_level}/5", inline=False)
        legendary_embed.set_image(url=legendary_fish.get('image_url', ''))
        
        boss_view = LegendaryBossFightView(self, user_id, legendary_fish, rod_durability, rod_level, channel, guild_id, ctx.author)
        await channel.send(f"<@{user_id}> [🧪 DEBUG TEST]", embed=legendary_embed, view=boss_view)
        logger.info(f"[DEBUG] {ctx.author.name} triggered legendary encounter: {legendary_fish['key']}")

    @commands.command(name="huyenthoai")
    async def legendary_hall(self, ctx):
        await _legendary_hall_of_fame_impl(self, ctx_or_interaction=ctx, is_slash=False)

    @app_commands.command(name="lichcauca", description="📅 Xem lịch sự kiện")
    async def event_schedule(self, interaction: discord.Interaction):
        manager = self.global_event_manager
        current = manager.current_event
        active = f"🔥 **{current['data']['name']}**" if current else "*Không có sự kiện.*"
        embed = discord.Embed(title="📅 Lịch Trình Sự Kiện", color=discord.Color.blue())
        embed.add_field(name="Đang được kích hoạt", value=active, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="taiche", description="Bán tất cả rác trong túi")
    async def recycle_trash_slash(self, interaction: discord.Interaction):
        await _recycle_trash_impl(self, ctx_or_interaction=interaction)

    @app_commands.command(name="bosuutap", description="Xem bộ sưu tập cá")
    async def view_collection_slash(self, interaction: discord.Interaction):
        await _view_collection_impl(self, ctx_or_interaction=interaction, user_id=interaction.user.id, username=interaction.user.name)

    @app_commands.command(name="dosong", description="Sử dụng máy dò sóng 52Hz")
    async def dosong_slash(self, interaction: discord.Interaction):
        await _dosong_impl(self, ctx_or_interaction=interaction, is_slash=True)

    @app_commands.command(name="ghepbando", description="Ghép mảnh bản đồ hầm ám")
    async def ghepbando_slash(self, interaction: discord.Interaction):
        await _ghepbando_impl(self, ctx_or_interaction=interaction, is_slash=True)

    @app_commands.command(name="bonphan", description="Sử dụng phân bón cho cây tiền")
    async def use_phan_bon_slash(self, interaction: discord.Interaction):
        await _use_phan_bon_impl(self, ctx_or_interaction=interaction)

    @app_commands.command(name="huyenthoai", description="Xem sảnh danh vọng huyền thoại")
    async def legendary_hall_slash(self, interaction: discord.Interaction):
        await _legendary_hall_of_fame_impl(self, ctx_or_interaction=interaction, is_slash=True)

    # Required API for mechanics/events.py
    async def get_user_total_luck(self, user_id):
        # Base luck
        luck = 0.0
        
        # 1. Rod Luck
        try:
            rod_lvl, _ = await logic.get_rod_data(user_id)
            rod_config = ROD_LEVELS.get(rod_lvl, {})
            luck += rod_config.get("luck", 0)
        except:
            pass
            
        # 2. Consumable Buffs (Delegated to ConsumableCog if available)
        consumable_cog = self.bot.get_cog("ConsumableCog")
        if consumable_cog:
            # Assume consumable_cog has get_user_luck_buff API
            # If not, we might need to check DB directly, but for now safe default
            if hasattr(consumable_cog, "get_user_luck_buff"):
                luck += await consumable_cog.get_user_luck_buff(user_id)
        
        return luck

async def setup(bot):
    await bot.add_cog(FishingCog(bot))