import discord
from ..core.constants import ROD_LEVELS, WORM_COST

def create_casting_embed(username, wait_time, rod_config, rod_lvl, rod_durability, has_worm, auto_bought, repair_msg=None):
    """Creates the 'Fishing...' casting animation embed."""
    embed = discord.Embed(
        title=f"🎣 {username} - Đang Câu Cá",
        description=f"⏳ **Chờ cá cắn câu trong {wait_time}s...**",
        color=discord.Color.blue()
    )

    # ROD INFO
    rod_name = rod_config.get('name', 'Unknown')
    max_durability = rod_config.get('durability', 10)
    cd_time = rod_config.get('cd', 0)

    durability_percent = int((rod_durability / max_durability) * 100) if max_durability > 0 else 0
    filled_blocks = int((rod_durability / max_durability) * 10) if max_durability > 0 else 0
    empty_blocks = 10 - filled_blocks
    durability_bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}] {durability_percent}%"

    rod_value = f"**{rod_name}** (Lv. {rod_lvl})\n"
    rod_value += f"Độ bền: {durability_bar}\n"
    rod_value += f"└ {rod_durability}/{max_durability}\n"
    rod_value += f"⏱️ Cooldown: {cd_time}s"

    embed.add_field(name="🎣 Cần Câu", value=rod_value, inline=False)

    # BAIT STATUS
    if auto_bought:
        bait_value = f"✅ **Tự Động Mua**\n└ Phí: {WORM_COST} Hạt"
        bait_icon = "💸"
    elif not has_worm:
        bait_value = f"❌ **Không Có Mồi**\n└ Tỉ lệ rác cao!"
        bait_icon = "⚠️"
    else:
        bait_value = f"✅ **Đã Sử Dụng**\n└ Tăng khả năng bắt cá"
        bait_icon = "🐛"

    embed.add_field(name=f"{bait_icon} Mồi Câu", value=bait_value, inline=True)

    if repair_msg:
        embed.set_footer(text=repair_msg.replace("\n", " • "))
        
    return embed

def create_result_embed(username, caught_items, earned_xp, earned_money, auto_sell=False):
    """Creates the Catch Result embed."""
    title = f"🎣 Kết Quả Câu Cá - {username}"
    
    if not caught_items:
        desc = "Không câu được gì... 😢"
        color = discord.Color.light_grey()
    else:
        desc = ""
        # Group items
        for item_key, quantity in caught_items.items():
            # Get item emoji and name (This would require item lookup, for now using key)
            # Formatting: 🔮 Ngọc Trai x1
            name = item_key.replace('_', ' ').title()
            desc += f"• **{name}** x{quantity}\n"
            
        color = discord.Color.green()

    embed = discord.Embed(title=title, description=desc, color=color)
    
    footer_text = f"✨ +{earned_xp} XP"
    if earned_money > 0:
        footer_text += f" • 💰 +{earned_money} Hạt"
    if auto_sell:
        footer_text += " (Đã bán tự động)"
        
    embed.set_footer(text=footer_text)
    return embed

def create_event_embed(title, description, event_type="neutral"):
    """Creates an event notification embed."""
    colors = {
        "good": discord.Color.gold(),
        "bad": discord.Color.red(),
        "neutral": discord.Color.blue(),
        "mixed": discord.Color.orange()
    }
    
    embed = discord.Embed(
        title=f"🔔 {title}",
        description=description,
        color=colors.get(event_type, discord.Color.blue())
    )
    return embed
