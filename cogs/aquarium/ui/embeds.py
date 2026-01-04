
import discord
from typing import Dict, List, Optional

def create_aquarium_dashboard(
    user_name: str, 
    user_avatar: str,
    view_visuals: str,
    stats: Dict, # charm, value, sets
    inventory_count: int,
    theme_url: Optional[str] = None
) -> discord.Embed:
    """
    Generate the Standard Aquarium Dashboard Embed.
    Example:
    title: 🐠 Nhà của PhucTruong
    desc: *Sử dụng /trangtri sapxep...*
    field[0]: Visuals
    field[1]: Info (Value, Charm, Sets)
    footer: Inventory count
    """
    
    embed = discord.Embed(
        title=f"🐠 Nhà của {user_name}",
        description="*Sử dụng `/trangtri sapxep` để chỉnh sửa nội thất.*",
        color=0x3498db
    )
    if user_avatar:
        embed.set_thumbnail(url=user_avatar)
    
    # Set Custom Theme Background (VIP)
    if theme_url:
        embed.set_image(url=theme_url)
    
    # Visuals
    embed.add_field(name="🖼️ Bể Cá & Nội Thất", value=view_visuals, inline=False)
    
    # Stats & Sets
    active_sets = stats.get('sets', [])
    charm = stats.get('charm', 0)
    val = stats.get('value', 0)
    
    info_text = f"🍃 **Giá trị:** {val:,} Xu Lá\n💖 **Charm:** {charm}"
    
    if active_sets:
        info_text += "\n\n**🌟 Phong Thủy (Kích Hoạt):**\n"
        for s in active_sets:
            info_text += f"• {s['icon']} **{s['name']}**: {s['bonus_desc']}\n"
    elif charm == 0 and val == 0:
        info_text += "\n*(Chưa có nội thất)*"
        
    embed.add_field(name="📊 Thông Tin Hồ Cá", value=info_text, inline=False)
    
    embed.set_footer(text=f"Kho: {inventory_count} vật phẩm • Làng Chài BHNBot")
    
    return embed
