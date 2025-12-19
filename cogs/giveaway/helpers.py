import json
import random
import discord
from database_manager import db_manager, get_rod_data, get_user_balance

async def get_valid_invites(user_id: int) -> int:
    """Count valid invites for a user"""
    result = await db_manager.fetchone(
        "SELECT COUNT(*) FROM user_invites WHERE inviter_id = ? AND is_valid = 1",
        (user_id,),
        use_cache=True,
        cache_key=f"invites_{user_id}",
        cache_ttl=60
    )
    return result[0] if result else 0

async def check_requirements(user: discord.Member, requirements: dict) -> tuple[bool, str]:
    """Check if user meets all requirements. Returns (passed, reason)"""
    
    # 1. Check Invites
    if "min_invites" in requirements:
        required = requirements["min_invites"]
        valid_count = await get_valid_invites(user.id)
        if valid_count < required:
            return False, f"Yêu cầu: **{required} Invites** (Acc > 7 ngày).\nBạn có: **{valid_count}**."

    # 2. Check Rod Level
    if "min_rod_level" in requirements:
        required_rod = requirements["min_rod_level"]
        # get_rod_data returns (level, durability) or similar. 
        # Checking database_manager.py or fishing cog would confirm, but assuming per user prompt
        # User prompt said: lvl, _ = await get_rod_data(user.id)
        try:
            # Need to ensure get_rod_data is imported or available. 
            # I will assume it is available from database_manager as suggested in prompt
            rod_data = await get_rod_data(user.id)
            if rod_data:
                lvl = rod_data[0]
            else:
                lvl = 0
                
            if lvl < required_rod:
                return False, f"Yêu cầu **Cần Câu Cấp {required_rod}** mới được tham gia!"
        except Exception as e:
            print(f"Error checking rod level: {e}")
            # If function not found or error, maybe skip or fail? 
            # For safety, fail.
            return False, "Lỗi kiểm tra cấp cần câu."

    # 3. Check Cost (User prompt handled this in view, but we can check balance here)
    if "cost" in requirements and requirements["cost"] > 0:
        cost = requirements["cost"]
        bal = await get_user_balance(user.id)
        if bal < cost:
            return False, "Không đủ tiền mua vé!"

    return True, ""

async def end_giveaway(giveaway_id: int, bot: discord.Client):
    """End a giveaway and pick winners"""
    from .models import Giveaway
    from .constants import COLOR_GIVEAWAY, EMOJI_WINNER
    
    # 1. Get Giveaway Data
    row = await db_manager.fetchone("SELECT * FROM giveaways WHERE message_id = ?", (giveaway_id,))
    if not row: return
    ga = Giveaway.from_db(row)
    
    if ga.status != 'active': return

    # 2. Get Participants
    # Entries > 1 support (weighted choice)
    participants = await db_manager.execute(
        "SELECT user_id, entries FROM giveaway_participants WHERE giveaway_id = ?", 
        (giveaway_id,)
    )
    
    pool = []
    for user_id, entries in participants:
        pool.extend([user_id] * entries)
    
    # 3. Pick Winners
    winners_ids = []
    if pool:
        count = min(len(set(pool)), ga.winners_count) # Unique winners
        # Use simple random.sample if entries=1, but with weights we use pool
        # To ensure unique winners with weights is tricky.
        # Simplest: shuffle pool, pick unique.
        random.shuffle(pool)
        seen = set()
        for uid in pool:
            if uid not in seen:
                winners_ids.append(uid)
                seen.add(uid)
            if len(winners_ids) >= count:
                break
    
    # 4. Update Status
    await db_manager.modify(
        "UPDATE giveaways SET status = 'ended' WHERE message_id = ?", 
        (giveaway_id,)
    )

    # 5. Announce
    try:
        channel = bot.get_channel(ga.channel_id)
        if not channel:
            # Try fetching if not in cache
            try:
                channel = await bot.fetch_channel(ga.channel_id)
            except:
                return
        
        try:
            msg = await channel.fetch_message(ga.message_id)
        except:
            msg = None

        if winners_ids:
            winners_text = ", ".join([f"<@{uid}>" for uid in winners_ids])
            result_text = f"Xin chúc mừng {winners_text} đã thắng **{ga.prize}**! {EMOJI_WINNER}. Hẹn các bạn trong các giveaway sau!"
        else:
            result_text = "Không có ai tham gia, không có người thắng. 😢"

        # Reply to giveaway message
        if msg:
            # Disable view
            await msg.edit(view=None)
            await msg.reply(result_text)
        else:
            await channel.send(f"Giveaway **{ga.prize}** đã kết thúc.\n{result_text}")
            
    except Exception as e:
        print(f"Error ending giveaway {giveaway_id}: {e}")

