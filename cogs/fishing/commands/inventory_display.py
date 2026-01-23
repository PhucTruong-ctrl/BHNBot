"""Inventory Display Module - Clean embed formatting for user inventory."""

import discord
from typing import Dict, Optional


async def create_inventory_embed(
    user: discord.User, 
    seeds: int, 
    inventory: Dict, 
    rod_data: Optional[Dict] = None, 
    legendary_fish_caught: Optional[list] = None, 
    vip_data: Optional[Dict] = None,
    currency_data: Optional[Dict] = None
) -> discord.Embed:
    from cogs.fishing.constants import ALL_FISH, LEGENDARY_FISH_KEYS
    from cogs.fishing.mechanics.glitch import is_glitch_active, apply_display_glitch
    from core.services.vip_service import VIPEngine

    title = f"🎒 {user.display_name} - Túi Đồ"
    
    if vip_data:
        embed = await VIPEngine.create_vip_embed(user, title, "", vip_data)
    else:
        embed = discord.Embed(title=title, color=discord.Color.blue())
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
    
    if rod_data:
        rod_name = rod_data.get('name', 'Unknown')
        rod_level = rod_data.get('level', 1)
        durability = rod_data.get('durability', 0)
        max_durability = rod_data.get('max_durability', 10)
        
        durability_percent = int((durability / max_durability) * 100) if max_durability > 0 else 0
        filled_blocks = int((durability / max_durability) * 10) if max_durability > 0 else 0
        empty_blocks = 10 - filled_blocks
        durability_bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}] {durability_percent}%"
        
        rod_value = f"**{rod_name}** (Lv. {rod_level})\n"
        rod_value += f"Độ bền: {durability_bar}\n"
        rod_value += f"└ {durability}/{max_durability}"
        
        embed.add_field(name="🎣 Cần Câu", value=rod_value, inline=False)
    
    if legendary_fish_caught:
        caught_legendary = [k for k in legendary_fish_caught if k in ALL_FISH]
        
        if caught_legendary:
            legendary_text = ""
            for fish_key in caught_legendary:
                fish = ALL_FISH[fish_key]
                name = fish.get('name', fish_key)
                emoji = fish.get('emoji', '🐟')
                legendary_text += f"{emoji} **{name}** ✅\n"
            
            legendary_text += f"\n└ Đã bắt: **{len(caught_legendary)}/{len(LEGENDARY_FISH_KEYS)}**"
            embed.add_field(name="🌟 Cá Huyền Thoại", value=legendary_text, inline=False)
    
    currency_parts = [f"💰 **{seeds:,}** Hạt"]
    
    if currency_data:
        leaf_coin = currency_data.get('leaf_coin', 0)
        if leaf_coin > 0:
            currency_parts.append(f"🍃 **{leaf_coin:,}** Xu Lá")
        
        event_currency = currency_data.get('event_currency', 0)
        event_emoji = currency_data.get('event_emoji', '🎫')
        event_name = currency_data.get('event_name', 'Token')
        if event_currency > 0:
            currency_parts.append(f"{event_emoji} **{event_currency:,}** {event_name}")
    
    embed.add_field(name="💎 Tiền Tệ", value="\n".join(currency_parts), inline=False)
    
    if inventory:
        from core.item_system import item_system
        fish_items = {}
        gift_items = {}
        tool_items = {}
        trash_items = {}
        
        for key, qty in inventory.items():
            if qty <= 0:
                continue
            
            item = item_system.get_item(key)
            if item:
                itype = item.get("type", "misc")
                
                if itype == "trash":
                    trash_items[key] = qty
                elif itype == "gift":
                    gift_items[key] = qty
                elif itype in ["tool", "material", "consumable", "container", "legendary_component", "commemorative", "special", "buff"]:
                    tool_items[key] = qty
                else:
                    tool_items[key] = qty
            
            elif key in LEGENDARY_FISH_KEYS:
                fish_items[key] = qty
            
            elif key in ALL_FISH:
                fish_items[key] = qty
            
            else:
                tool_items[key] = qty
                  
        # 1. FISH
        if fish_items:
            fish_lines = []
            for key, qty in sorted(fish_items.items())[:15]:
                fish = ALL_FISH.get(key, {})
                fish_name = apply_display_glitch(fish.get('name', key)) if is_glitch_active() else fish.get('name', key)
                price = (fish.get('price', {}).get('sell') or fish.get('sell_price', 0)) * qty
                fish_lines.append(f"{fish.get('emoji','🐟')} **{fish_name}** x{qty} = {price:,} Hạt")
            
            if len(fish_items) > 15:
                fish_lines.append(f"_...+{len(fish_items) - 15} loại khác_")
            
            embed.add_field(name=f"🐟 Cá ({len(fish_items)})", value="\n".join(fish_lines), inline=False)
        
        # 2. GIFTS
        if gift_items:
            gift_parts = []
            for key, qty in sorted(gift_items.items()):
                item = item_system.get_item(key) or {}
                gift_parts.append(f"{item.get('emoji','🎁')} {item.get('name', key)} x{qty}")
            
            gift_text = " | ".join(gift_parts)
            embed.add_field(name=f"💝 Quà Tặng ({sum(gift_items.values())})", value=gift_text, inline=False)
            
        # 3. TOOLS / MATERIALS
        if tool_items:
            tool_parts = []
            for key, qty in sorted(tool_items.items()):
                item = item_system.get_item(key)
                if item:
                    name = item['name']
                    emoji = item.get('emoji', '📦')
                elif key in ALL_FISH:
                    item = ALL_FISH[key]
                    name = item['name']
                    emoji = item.get('emoji', '🐟')
                else:
                    name = key
                    emoji = "❓"

                tool_parts.append(f"{emoji} {name} x{qty}")
                
            tool_text = " | ".join(tool_parts)
            embed.add_field(name=f"🛠️ Công Cụ ({sum(tool_items.values())})", value=tool_text, inline=False)
            
        # 4. TRASH
        if trash_items:
            total_trash = sum(trash_items.values())
            trash_list = list(sorted(trash_items.items()))[:3]
            trash_parts = []
            for key, qty in trash_list:
                item = item_system.get_item(key) or {}
                name = item.get('name', key.replace('trash_', '').title())
                trash_parts.append(f"{name} x{qty}")
            
            trash_text = " | ".join(trash_parts)
            if len(trash_items) > 3:
                trash_text += f"\n_...+{len(trash_items) - 3} loại khác_"
            trash_text += f"\n└ **Tổng: {total_trash} rác**"
            
            embed.add_field(name=f"🗑️ Rác ({len(trash_items)})", value=trash_text, inline=False)
            
    else:
        embed.add_field(name="🎒 Inventory", value="_Trống rỗng_", inline=False)
    
    return embed
