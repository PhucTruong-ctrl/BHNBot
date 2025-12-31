import logging
import time
import discord
from database_manager import get_user_balance, add_seeds, increment_stat, get_stat
from ..constants import FISH_BUCKET_LIMIT, COMMON_FISH_KEYS, RARE_FISH_KEYS, LEGENDARY_FISH_KEYS, ItemKeys
from ..core import models

logger = logging.getLogger("FishingService")

class ActionService:
    """Service handling pre-flight checks and side-effects for fishing actions."""
    
    def __init__(self, bot, cog):
        self.bot = bot
        self.cog = cog # Reference to parent cog for shared state (legacy compat)

    async def check_server_freeze(self, user_id: int, username: str, is_slash: bool, ctx) -> bool:
        """Check if server is frozen due to disaster."""
        # Using cog state for now (refactor to DB later if needed)
        if not self.cog.is_server_frozen:
            return False
            
        remaining = int(self.cog.freeze_end_time - time.time())
        if remaining > 0:
            msg = f"⛔ **SERVER ĐANG BẢO TRÌ ĐỘT XUẤT!** Vui lòng chờ **{remaining}s**."
            if is_slash: await ctx.followup.send(msg, ephemeral=True)
            else: await ctx.reply(msg)
            return True
        else:
            # Expired, reset state
            self.cog.is_server_frozen = False
            self.cog.current_disaster = None
            if self.cog.disaster_channel:
                 await self.cog.disaster_channel.send("✅ **Sự kiện thảm họa đã kết thúc!** Server hoạt động trở lại.")
            return False

    async def check_bucket_limit(self, user_id: int, inventory: dict, username: str, is_slash: bool, ctx) -> bool:
        """Check if user's fish bucket is full."""
        fish_count = sum(v for k, v in inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS and k != ItemKeys.CA_ISEKAI)
        if fish_count >= FISH_BUCKET_LIMIT:
            msg = f"⚠️ **XÔ ĐÃ ĐẦY!** Bạn có {fish_count}/{FISH_BUCKET_LIMIT} cá. Hãy bán bớt!"
            if is_slash: await ctx.followup.send(msg, ephemeral=True)
            else: await ctx.reply(msg)
            return True
        return False

    async def check_and_repair_rod(self, user_id: int, rod_lvl: int, rod_durability: int, rod_config: dict, channel, username: str) -> tuple:
        """Auto-repair rod if broken and user has money.
        Returns: (new_durability, repair_msg, is_broken)
        """
        repair_msg = None
        is_broken = False
        
        if rod_durability <= 0:
            repair_cost = rod_config["repair"]
            balance = await get_user_balance(user_id)
            if balance >= repair_cost:
                await add_seeds(user_id, -repair_cost, 'rod_repair', 'fishing')
                rod_durability = rod_config["durability"]
                await models.update_rod_data(user_id, rod_durability, rod_lvl)
                repair_msg = f"🛠️ **Tự động sửa cần:** -{repair_cost} Hạt"
                
                # Stats
                try:
                    await increment_stat(user_id, "fishing", "rods_repaired", 1)
                    # Helper call for achievement check could go here if extracted
                except Exception as e:
                    logger.error(f"[ACHIEVEMENT] Error updating rods_repaired: {e}")
            else:
                is_broken = True
        
        return rod_durability, repair_msg, is_broken
