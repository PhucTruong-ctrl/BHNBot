"""Inventory Display Module - Clean embed formatting for user inventory.

Provides modern, well-structured inventory display with:
- Rod information (highlighted)
- Legendary fish section (caught only)
- Grouped items (fish, gifts, tools, trash)
- User avatar thumbnail
"""

import discord
from typing import Dict, Optional




def create_inventory_embed(user: discord.User, seeds: int, inventory: Dict, rod_data: Optional[Dict] = None, legendary_fish_caught: Optional[list] = None, vip_data: Optional[Dict] = None) -> discord.Embed:
    """Create modern inventory embed.
    
    Args:
        user: Discord user object
        seeds: User's seed balance
        inventory: Dictionary of items {item_key: quantity}
        rod_data: Optional dict with rod info {name, level, durability, max_durability}
        legendary_fish_caught: Optional list of caught legendary fish keys
        vip_data: Optional VIP data for styling
        
    Returns:
        discord.Embed: Formatted inventory embed
    """
    # Import dependencies
    from cogs.fishing.constants import ALL_FISH, ALL_ITEMS_DATA, LEGENDARY_FISH_KEYS
    from cogs.fishing.mechanics.glitch import is_glitch_active, apply_display_glitch
    from configs.item_constants import ItemKeys
    from core.services.vip_service import VIPEngine
    
    # Create embed using VIP Factory if available, else standard
    title = f"🎒 {user.display_name} - Túi Đồ"
    description = "" # Inventory has no top description usually, or we can add one.
    
    # For Factory, we need async... wait. Factory is async `create_vip_embed`.
    # But this function `create_inventory_embed` is sync.
    # CRITICAL: We cannot await inside a sync function.
    # Options:
    # 1. Make this function async (requires updating `economy.py`).
    # 2. Use `apply_vip_style` (which is async... wait, `apply_vip_style` is async too in new `vip.py`?).
    # `vip.py` line 101: `async def apply_vip_style`.
    # EVERYTHING in `vip.py` is async because it might fetch DB.
    # BUT if we pass `vip_data`, we don't need to fetch DB.
    # `create_vip_embed` (line 101 in new file) calls `get_vip_data` if not provided.
    # If provided, it just builds embed.
    # DOES IT AWAIT anything else?
    # `create_vip_embed` checks TIER_CONFIG (sync).
    # It constructs embed (sync).
    # It returns embed.
    # IT does NOT need to be async if `vip_data` is provided?
    # Line 105 in new `vip.py`: `async def create_vip_embed`. It is defined as async.
    # If I change `inventory_display.py` to use it, `create_inventory_embed` MUST be async.
    
    # Conclusion: I MUST Update `create_inventory_embed` to be ASYNC.
    # And update `economy.py` to await it.
    
    pass # Placeholder for thought process.
    
    # Since I'm editing the file content here, I will make it async.
    
async def create_inventory_embed(user: discord.User, seeds: int, inventory: Dict, rod_data: Optional[Dict] = None, legendary_fish_caught: Optional[list] = None, vip_data: Optional[Dict] = None) -> discord.Embed:
    # ... imports ...
    from cogs.fishing.constants import ALL_FISH, ALL_ITEMS_DATA, LEGENDARY_FISH_KEYS
    from cogs.fishing.mechanics.glitch import is_glitch_active, apply_display_glitch
    from configs.item_constants import ItemKeys
    from core.services.vip_service import VIPEngine

    title = f"🎒 {user.display_name} - Túi Đồ"
    
    if vip_data:
        # Use factory (await it)
        embed = await VIPEngine.create_vip_embed(user, title, "", vip_data)
        # Fix description if factory sets one (it sets border empty lines)
        # We might want to keep description empty if no text?
        # create_vip_embed sets description to borders. Good.
    else:
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue()
        )
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
        # We can try to dynamic load legendary fish names/emojis too if possible, 
        # but LEGENDARY_FISH_KEYS are just keys. We need ALL_FISH data.
        
        caught_legendary = []
        for key in legendary_fish_caught:
            if key in ALL_FISH:
                caught_legendary.append(key)
        
        if caught_legendary:
            legendary_text = ""
            for fish_key in caught_legendary:
                fish = ALL_FISH[fish_key]
                name = fish.get('name', fish_key)
                emoji = fish.get('emoji', '🐟')
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
    
    # ==================== INVENTORY ITEMS (DYNAMIC CLASSIFICATION) ====================
    if inventory:
        fish_items = {}
        gift_items = {}
        tool_items = {} # Tools, Materials, Consumables, Containers
        trash_items = {}
        
        for key, qty in inventory.items():
            if qty <= 0: continue
            
            # Check ALL_ITEMS_DATA first (Items System)
            if key in ALL_ITEMS_DATA:
                item = ALL_ITEMS_DATA[key]
                itype = item.get("type", "misc")
                
                if itype == "trash":
                    trash_items[key] = qty
                elif itype == "gift":
                    gift_items[key] = qty
                elif itype in ["tool", "material", "consumable", "container", "legendary_component", "commemorative", "special", "buff"]:
                    tool_items[key] = qty
                else:
                    # Fallback to tool/misc
                    tool_items[key] = qty
            
            # Check ALL_FISH (Fishing System)
            elif key in ALL_FISH and key not in LEGENDARY_FISH_KEYS:
                # Ensure we don't double count if it was in ITEMS_DATA
                # But we handled checks above.
                fish_items[key] = qty
            
            # Fallback for truly unknown items (legacy?)
            else:
                 # Put in tools just to show it exists
                 tool_items[key] = qty
                 
        # --- DISPLAY SECTIONS ---

        # 1. FISH
        if fish_items:
            fish_lines = []
            for key, qty in sorted(fish_items.items())[:15]:
                fish = ALL_FISH[key]
                fish_name = apply_display_glitch(fish['name']) if is_glitch_active() else fish['name']
                # Safe Price Accessor
                price = (fish.get('price', {}).get('sell') or fish.get('sell_price', 0)) * qty
                fish_lines.append(f"{fish.get('emoji','🐟')} **{fish_name}** x{qty} = {price:,} Hạt")
            
            if len(fish_items) > 15:
                fish_lines.append(f"_...+{len(fish_items) - 15} loại khác_")
            
            embed.add_field(
                name=f"🐟 Cá ({len(fish_items)})",
                value="\n".join(fish_lines),
                inline=False
            )
        
        # 2. GIFTS
        if gift_items:
            gift_parts = []
            for key, qty in sorted(gift_items.items()):
                 item = ALL_ITEMS_DATA[key]
                 gift_parts.append(f"{item.get('emoji','🎁')} {item['name']} x{qty}")
            
            gift_text = " | ".join(gift_parts)
            embed.add_field(
                name=f"💝 Quà Tặng ({sum(gift_items.values())})",
                value=gift_text,
                inline=False
            )
            
        # 3. TOOLS / MATERIALS
        if tool_items:
            tool_parts = []
            for key, qty in sorted(tool_items.items()):
                # Try ALL_ITEMS_DATA first, fallback to ALL_FISH if needed (unlikely here)
                # Then check ORPHAN_ITEMS_METADATA for legacy items, or use raw key as last resort
                if key in ALL_ITEMS_DATA:
                    item = ALL_ITEMS_DATA[key]
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
            embed.add_field(
                name=f"🛠️ Công Cụ ({sum(tool_items.values())})",
                value=tool_text,
                inline=False
            )
            
        # 4. TRASH
        if trash_items:
            total_trash = sum(trash_items.values())
            trash_list = list(sorted(trash_items.items()))[:3]
            trash_parts = []
            for key, qty in trash_list:
                item = ALL_ITEMS_DATA.get(key, {})
                name = item.get('name', key.replace('trash_', '').title())
                trash_parts.append(f"{name} x{qty}")
            
            trash_text = " | ".join(trash_parts)
            if len(trash_items) > 3:
                trash_text += f"\n_...+{len(trash_items) - 3} loại khác_"
            trash_text += f"\n└ **Tổng: {total_trash} rác**"
            
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
