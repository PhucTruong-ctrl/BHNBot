import json
import random
import discord
from database_manager import db_manager, get_rod_data, get_user_balance

from core.logging import get_logger
from .constants import COLOR_GIVEAWAY, EMOJI_WINNER
from .models import Giveaway

from core.logging import get_logger
logger = get_logger("giveaway")


logger = get_logger("GiveawayHelpers")

async def join_giveaway_transaction(giveaway_id: int, user_id: int, cost: int) -> tuple[bool, str]:
    """
    Executes a secure transaction to join a giveaway:
    1. Check if already joined (Atomic)
    2. Check Balance (Atomic)
    3. Deduct Cost (Atomic)
    4. Insert Participant (Atomic)
    
    Returns: (success: bool, message: str)
    """
    try:
        async with db_manager.transaction() as conn:
            # 1. Check if already joined
            # Note: We use row locking indirectly if needed, but INSERT will fail on unique constraint anyway if one exists.
            # However, we do a check first for user feedback.
            row = await conn.fetchrow(
                "SELECT 1 FROM giveaway_participants WHERE giveaway_id = $1 AND user_id = $2", 
                giveaway_id, user_id
            )
            if row:
                return False, "Bạn đã tham gia giveaway này rồi!"

            # 2. Check Balance & Deduct (if cost > 0)
            if cost > 0:
                row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1 FOR UPDATE", user_id)
                
                if not row or row['seeds'] < cost:
                    return False, f"Không đủ tiền! Cần {cost} Hạt."
                    
                await conn.execute(
                    "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                    cost, user_id
                )
                
                # Manual Log for ACID Transaction
                await conn.execute(
                    "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, $3, $4, NOW())",
                    user_id, -cost, f"join_giveaway_{giveaway_id}", "giveaway"
                )

            # 3. Insert Participant
            await conn.execute(
                "INSERT INTO giveaway_participants (giveaway_id, user_id) VALUES ($1, $2)",
                giveaway_id, user_id
            )
            
            # Clear caches (outside transaction logic effectively, but good to do here if successful)
            if cost > 0:
                db_manager.clear_cache_by_prefix(f"balance_{user_id}")
            
            return True, "Tham gia thành công!"
            
    except Exception as e:
        logger.error(f"Transaction error (join_giveaway): {e}", exc_info=True)
        return False, "Lỗi hệ thống khi xử lý giao dịch!"

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

    # 2. Check Cost (removed rod level requirement)
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

    # 2. Get Participants (each user has 1 entry)
    participants = await db_manager.execute(
        "SELECT user_id FROM giveaway_participants WHERE giveaway_id = ?", 
        (giveaway_id,)
    )
    
    # Extract user IDs
    user_ids = [row[0] for row in participants]
    
    # 3. Pick Winners (simple random selection)
    winners_ids = []
    if user_ids:
        count = min(len(user_ids), ga.winners_count)
        winners_ids = random.sample(user_ids, count)
        logger.debug("[giveaway]_winner_selection_-_", giveaway_id=giveaway_id)
    else:
        logger.debug("[giveaway]_no_participants_for", giveaway_id=giveaway_id)
    
    logger.debug("[giveaway]_giveaway_id__ended_", giveaway_id=giveaway_id)
    
    # 4. Send DMs to Winners
    dm_success = []
    dm_failed = []
    
    if winners_ids:
        import asyncio
        for winner_id in winners_ids:
            try:
                user = await bot.fetch_user(winner_id)
                
                # Create DM embed
                dm_embed = discord.Embed(
                    title="🎉 Chúc Mừng - Bạn Đã Thắng Giveaway!",
                    description=f"Bạn đã thắng **{ga.prize}**!",
                    color=COLOR_GIVEAWAY
                )
                dm_embed.add_field(
                    name="🔗 Link Giveaway",
                    value=f"[Nhấn để xem kết quả](https://discord.com/channels/{ga.guild_id}/{ga.channel_id}/{ga.message_id})",
                    inline=False
                )
                dm_embed.set_footer(text=f"Giveaway ID: {giveaway_id}")
                
                await user.send(embed=dm_embed)
                dm_success.append(winner_id)
                logger.debug("[giveaway]_dm_sent_to_winner", username=user.name)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.3)
                
            except discord.Forbidden:
                dm_failed.append(winner_id)
                logger.debug("[giveaway]_❌_failed_to_dm_winn", winner_id=winner_id)
            except Exception as e:
                dm_failed.append(winner_id)
                logger.debug("[giveaway]_❌_error_dming_winne", winner_id=winner_id)
        
        logger.debug("[giveaway]_dm_results", success_count=len(dm_success))
    
    # 5. Update Status
    import json
    await db_manager.modify(
        "UPDATE giveaways SET status = 'ended', winners = ? WHERE message_id = ?", 
        (json.dumps(winners_ids), giveaway_id)
    )

    # 6. Announce
    try:
        channel = bot.get_channel(ga.channel_id)
        if not channel:
            # Try fetching if not in cache
            try:
                channel = await bot.fetch_channel(ga.channel_id)
            except Exception as e:
                return
        
        try:
            msg = await channel.fetch_message(ga.message_id)
        except Exception as e:
            msg = None

        if winners_ids:
            winners_text = ", ".join([f"<@{uid}>" for uid in winners_ids])
            result_text = f"Xin chúc mừng {winners_text} đã thắng **{ga.prize}**! {EMOJI_WINNER}. Hẹn các bạn trong các giveaway sau!"
        else:
            result_text = "Không có ai tham gia, không có người thắng. 😢"

        # Create result embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY KẾT QUẢ",
            description=result_text,
            color=COLOR_GIVEAWAY
        )
        embed.set_footer(text=f"Giveaway ID: {giveaway_id}")

        # Create result view with admin controls
        from .views import GiveawayResultView
        result_view = GiveawayResultView(giveaway_id, winners_ids, bot)

        # Reply to giveaway message
        if msg:
            # Update original embed to show ENDED
            original_embed = msg.embeds[0]
            new_embed = discord.Embed(
                title="🔴 GIVEAWAY ĐÃ KẾT THÚC", 
                description=f"**Giải thưởng:** {ga.prize}\n**Kết quả:** Xem bên dưới 👇",
                color=discord.Color.dark_grey() 
            )
            if original_embed.image:
                new_embed.set_image(url=original_embed.image.url)
            new_embed.set_footer(text=f"Giveaway ID: {giveaway_id} | Đã kết thúc")

            # Disable view and update embed
            await msg.edit(embed=new_embed, view=None)
            await msg.reply(embed=embed, view=result_view)
        else:
            await channel.send(embed=embed, view=result_view)
            
    except Exception as e:
        logger.debug("error_ending_giveaway_:_{e}", giveaway_id=giveaway_id)

