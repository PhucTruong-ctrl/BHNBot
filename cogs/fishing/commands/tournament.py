import discord
from discord import app_commands
from ..tournament import TournamentManager
from core.database import get_user_balance

async def tournament_create_action(interaction: discord.Interaction, entry_fee: int):
    """Handler for /giaidau create"""
    user = interaction.user
    
    # 1. Check VIP
    from core.services.vip_service import VIPEngine
    vip_data = await VIPEngine.get_vip_data(user.id)
    if not vip_data or vip_data['tier'] < 1:
        await interaction.response.send_message("❌ Chỉ VIP Tier 1 trở lên mới được tổ chức giải!", ephemeral=True)
        return

    # 2. Check Balance
    balance = await get_user_balance(user.id)
    if balance < entry_fee:
        await interaction.response.send_message(f"❌ Bạn không đủ tiền để đóng phí tham gia ({entry_fee:,} Hạt)!", ephemeral=True)
        return
        
    if entry_fee < 1000:
        await interaction.response.send_message("❌ Phí tham gia tối thiểu là 1,000 Hạt.", ephemeral=True)
        return

    # 3. Create
    # Defer handling?
    await interaction.response.defer(ephemeral=False)
    
    manager = TournamentManager.get_instance()
    t_id = await manager.create_tournament(user.id, entry_fee)
    
    if t_id is None:
        await interaction.followup.send("❌ Tạo giải thất bại! (Có thể bạn đã tham gia giải khác hoặc gặp lỗi hệ thống)")
        return
    elif t_id == -1:
         await interaction.followup.send("❌ Lỗi trừ tiền (Có thể số dư vừa thay đổi).")
         return
         
    embed = discord.Embed(
        title="🏆 GIẢI ĐẤU CÂU CÁ MỚI!",
        description=f"**Host:** {user.mention}\n"
                    f"**Phí Tham Gia:** {entry_fee:,} Hạt\n"
                    f"**Trạng Thái:** Đang đăng ký (15 phút)\n\n"
                    f"👉 Sử dụng `/giaidau join` để tham gia ngay!\n"
                    f"Requires 2+ players to start.",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"ID Giải: {t_id}")
    
    from ..views import TournamentLobbyView
    view = TournamentLobbyView(t_id, user.id)
    
    await interaction.followup.send(embed=embed, view=view)

async def tournament_join_action(interaction: discord.Interaction, tournament_id: int):
    """Handler for /giaidau join"""
    user = interaction.user
    manager = TournamentManager.get_instance()
    
    success, msg = await manager.join_tournament(tournament_id, user.id)
    
    if success:
        await interaction.response.send_message(f"✅ **{user.name}** đã tham gia giải đấu (ID: {tournament_id})!\n{msg}")
    else:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

async def tournament_rank_action(interaction: discord.Interaction):
    """Handler for /giaidau rank - Shows current active ranking"""
    user = interaction.user
    manager = TournamentManager.get_instance()
    
    # Check if user is in a tournament
    if user.id not in manager.active_participants:
        await interaction.response.send_message("❌ Bạn không tham gia giải đấu nào đang diễn ra.", ephemeral=True)
        return
        
    tournament_id = manager.active_participants[user.id]
    
    # Fetch Leaderboard
    from core.database import db_manager
    ranks = await db_manager.fetchall(
        """
        SELECT u.username, te.score 
        FROM tournament_entries te
        JOIN users u ON te.user_id = u.user_id
        WHERE te.tournament_id = ?
        ORDER BY te.score DESC
        LIMIT 10
        """, 
        (tournament_id,)
    )
    
    tourney = await db_manager.fetchrow("SELECT prize_pool, end_time FROM vip_tournaments WHERE id = ?", (tournament_id,))
    
    embed = discord.Embed(title=f"🏆 BẢNG XẾP HẠNG (ID: {tournament_id})", color=discord.Color.blue())
    
    desc = ""
    for i, (name, score) in enumerate(ranks, 1):
        medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"
        desc += f"{medal} **{name}**: {score:,} điểm\n"
        
    embed.description = desc
    embed.add_field(name="💰 Tổng Giải Thưởng", value=f"{tourney['prize_pool']:,} Hạt", inline=True)
    
    if tourney['end_time']:
         # Convert ISO string/native to dynamic timestamp
         # TODO: Handle string parsing properly if sqlite returns string
         # BUT better: We stored standard string in manager. Or just display "Dang dien ra"
         # Let's simple for now.
         embed.set_footer(text=f"Kết thúc: {tourney['end_time']} (UTC)")
         
    await interaction.response.send_message(embed=embed)
