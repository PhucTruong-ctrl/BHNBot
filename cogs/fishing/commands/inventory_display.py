"""Inventory Display Module - Clean embed formatting for user inventory.

Provides modern, well-structured inventory display with:
- Rod information (highlighted)
- Legendary fish section (caught only)
- Grouped items (fish, gifts, tools, trash)
- User avatar thumbnail
"""

import discord
from typing import Dict, Optional


async def create_inventory_embed(user: discord.User, seeds: int, inventory: Dict, rod_data: Optional[Dict] = None, legendary_fish_caught: Optional[list] = None) -> discord.Embed:
    """Create modern inventory embed.
    
    Args:
        user: Discord user object
        seeds: User's seed balance
        inventory: Dictionary of items {item_key: quantity}
        rod_data: Optional dict with rod info {name, level, durability, max_durability}
        legendary_fish_caught: Optional list of caught legendary fish keys
        
    Returns:
        discord.Embed: Formatted inventory embed
    """
    # Import dependencies
    from cogs.fishing import ALL_FISH
    from cogs.fishing.mechanics.glitch import is_glitch_active, apply_display_glitch
    from cogs.fishing.constants import ALL_ITEMS_DATA, LEGENDARY_FISH_KEYS
    
    # Create embed
    embed = discord.Embed(
        title=f"🎒 {user.display_name} - Túi Đồ",
        color=discord.Color.blue()
    )
    
    # Set user avatar
    embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
    
    # ==================== ROD INFO ====================
    if rod_data:
        rod_name = rod_data.get('name', 'Unknown')
        rod_level = rod_data.get('level', 1)
        durability = rod_data.get('durability', 0)
        max_durability = rod_data.get('max_durability', 10)
        
        # Create durability bar
        durability_percent = int((durability / max_durability) * 100) if max_durability > 0 else 0
        filled_blocks = int((durability / max_durability) * 10) if max_durability > 0 else 0
        empty_blocks = 10 - filled_blocks
        durability_bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}] {durability_percent}%"
        
        rod_value = f"**{rod_name}** (Lv. {rod_level})\n"
        rod_value += f"Độ bền: {durability_bar}\n"
        rod_value += f"└ {durability}/{max_durability}"
        
        embed.add_field(
            name="🎣 Cần Câu",
            value=rod_value,
            inline=False
        )
    
    # ==================== LEGENDARY FISH (Only caught) ====================
    if legendary_fish_caught:
        legendary_map = {
            "ca_ngan_ha": ("Cá Ngân Hà", "🌌"),
            "ca_phuong_hoang": ("Phượng Hoàng", "🔥"),
            "cthulhu_con": ("Cthulhu Non", "🐙"),
            "ca_voi_52hz": ("Cá Voi 52Hz", "🐋"),
            "ca_galaxy": ("Cá Galaxy", "🌠")
        }
        
        caught_legendary = [key for key in legendary_fish_caught if key in legendary_map]
        
        if caught_legendary:
            legendary_text = ""
            for fish_key in caught_legendary:
                name, emoji = legendary_map[fish_key]
                legendary_text += f"{emoji} **{name}** ✅\n"
            
            legendary_text += f"\n└ Đã bắt: **{len(caught_legendary)}/{len(LEGENDARY_FISH_KEYS)}**"
            
            embed.add_field(
                name="🌟 Cá Huyền Thoại",
                value=legendary_text,
                inline=False
            )
    
    # ==================== SEEDS ====================
    embed.add_field(
        name="💰 Hạt",
        value=f"**{seeds:,}**",
        inline=True
    )
    
    # ==================== INVENTORY ITEMS ====================
    if inventory:
        # FISH
        fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH and k not in LEGENDARY_FISH_KEYS}
        if fish_items:
            fish_lines = []
            for key, qty in sorted(fish_items.items())[:15]:  # Limit to 15 to avoid overflow
                fish = ALL_FISH[key]
                fish_name = apply_display_glitch(fish['name']) if is_glitch_active() else fish['name']
                price = fish['sell_price'] * qty
                fish_lines.append(f"{fish['emoji']} **{fish_name}** x{qty} = {price:,} Hạt")
            
            if len(fish_items) > 15:
                fish_lines.append(f"_...+{len(fish_items) - 15} loại khác_")
            
            embed.add_field(
                name=f"🐟 Cá ({len(fish_items)})",
                value="\n".join(fish_lines),
                inline=False
            )
        
        # GIFTS (compact)
        gift_lookup = {
            "cafe": ("Cà Phê", "☕"),
            "flower": ("Hoa", "🌹"),
            "ring": ("Nhẫn", "💍"),
            "gift": ("Quà", "🎁"),
            "chocolate": ("Sô Cô La", "🍫"),
            "card": ("Thiệp", "💌"),
        }
        gift_items = {k: v for k, v in inventory.items() if k in gift_lookup}
        if gift_items:
            # Compact format: 2 items per line
            gift_parts = [f"{gift_lookup[k][1]} {gift_lookup[k][0]} x{v}" for k, v in sorted(gift_items.items())]
            gift_text = " | ".join(gift_parts)
            
            embed.add_field(
                name=f"💝 Quà Tặng ({sum(gift_items.values())})",
                value=gift_text,
                inline=False
            )
        
        # TOOLS (compact)
        tool_lookup = {
            "ruong_kho_bau": ("Rương Kho Báu", "🎁"),
            "phan_bon": ("Phân Bón", "🌾"),
            "ngoc_trai": ("Ngọc Trai", "🔮"),
            "vat_lieu_nang_cap": ("Vật Liệu Nâng Cấp Cần", "⚙️"),
            "manh_ghep_a": ("Mảnh Ghép A", "🧩"),
            "manh_ghep_b": ("Mảnh Ghép B", "🧩"),
            "manh_ghep_c": ("Mảnh Ghép C", "🧩"),
            "manh_ghep_d": ("Mảnh Ghép D", "🧩"),
            "manh_ban_do_a": ("Mảnh Bản Đồ A", "🗺️"),
            "manh_ban_do_b": ("Mảnh Bản Đồ B", "🗺️"),
            "manh_ban_do_c": ("Mảnh Bản Đồ C", "🗺️"),
            "manh_ban_do_d": ("Mảnh Bản Đồ D", "🗺️"),
            "ban_do_ham_am": ("Bản Đồ Hắc", "🗺️✨"),
            "manh_sao_bang": ("Mảnh Sao Băng", "🌠"),
            "long_vu_lua": ("Lông Vũ Lửa", "🔥"),
            "may_do_song": ("Máy Dò Sóng", "📡"),
            # Commemorative items (season rewards)
            "qua_ngot_mua_1": ("Quả Ngọt Mùa 1", "🍎"),
            "qua_ngot_mua_2": ("Quả Ngọt Mùa 2", "🍏"),
            "qua_ngot_mua_3": ("Quả Ngọt Mùa 3", "�"),
            "qua_ngot_mua_4": ("Quả Ngọt Mùa 4", "🍋"),
            "qua_ngot_mua_5": ("Quả Ngọt Mùa 5", "🍌"),
            # Consumable buff items
            "nuoc_tang_luc": ("Nước TL", "💪"),
            "gang_tay_xin": ("Găng Tay", "🥊"),
            "thao_tac_tinh_vi": ("Thao Tác Tinh Vi", "🎯"),
            "tinh_yeu_ca": ("Tình Yêu Cá", "❤️"),
            "tinh_cau": ("Tinh Cầu Không Gian", "🌌"),
        }
        tool_items = {k: v for k, v in inventory.items() if k in tool_lookup}
        if tool_items:
            tool_parts = [f"{tool_lookup[k][1]} {tool_lookup[k][0]} x{v}" for k, v in sorted(tool_items.items())]
            tool_text = " | ".join(tool_parts)
            
            embed.add_field(
                name=f"🛠️ Công Cụ ({sum(tool_items.values())})",
                value=tool_text,
                inline=False
            )
        
        # TRASH (collapsed)
        trash_items = {k: v for k, v in inventory.items() if k.startswith("trash_")}
        if trash_items:
            total_trash = sum(trash_items.values())
            # Show first 3 items + count
            trash_list = list(sorted(trash_items.items()))[:3]
            trash_parts = []
            for key, qty in trash_list:
                name = ALL_ITEMS_DATA.get(key, {}).get('name', key.replace('trash_', '').replace('_', ' ').title())
                trash_parts.append(f"{name} x{qty}")
            
            trash_text = " | ".join(trash_parts)
            if len(trash_items) > 3:
                trash_text += f"\n_...+{len(trash_items) - 3} loại khác_"
            trash_text += f"\n└ **Tổng: {total_trash} items**"
            
            embed.add_field(
                name=f"🗑️ Rác ({len(trash_items)})",
                value=trash_text,
                inline=False
            )
    else:
        embed.add_field(
            name="🎒 Inventory",
            value="_Trống rỗng_",
            inline=False
        )
    
    return embed
