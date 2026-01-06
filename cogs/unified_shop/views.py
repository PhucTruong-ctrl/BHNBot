
import discord
from discord import ui
import logging
from typing import List, Dict, Optional

from core.item_system import item_system
from database_manager import db_manager, get_user_balance
from cogs.aquarium.logic.market import MarketEngine # Reuse buy logic or refactor?
# Ideally we should use a unified Market Controller. 
# For now, I'll implement buying logic here using MarketEngine (which I fixed) for Decor, 
# and ShopCog logic for others? 
# Better: Create a unified 'buy_item' in this module's logic.py

logger = logging.getLogger("UnifiedShopUI")

# ==================== CONSTANTS ====================
# ==================== CONSTANTS ====================
CATEGORIES = {
    "consumables": {"label": "Mồi & Buff", "emoji": "🎒", "desc": "Mồi câu, nước tăng lực..."},
    "tools": {"label": "Dụng Cụ", "emoji": "🎣", "desc": "Cần câu, máy dò..."},
    "decor": {"label": "Nội Thất Hồ Cá", "emoji": "🛋️", "desc": "Trang trí nhà cửa"},
    "vip": {"label": "Thẻ VIP", "emoji": "💎", "desc": "Nâng cấp tài khoản"},
    "gift": {"label": "Quà Tặng", "emoji": "🎁", "desc": "Tặng người khác"}
}

# ==================== PERSISTENT LAUNCHER ====================
class ShopLauncher(ui.View):
    """
    The persistent view attached to the Shop Message.
    """
    def __init__(self):
        super().__init__(timeout=None)

    @ui.select(
        placeholder="📂 Chọn danh mục...",
        custom_id="unified_shop:launcher_select",
        min_values=1, max_values=1,
        options=[
            discord.SelectOption(label=v["label"], value=k, emoji=v["emoji"], description=v["desc"])
            for k, v in CATEGORIES.items()
        ] + [discord.SelectOption(label="Xem Túi Đồ của tôi", value="inventory", emoji="🎒")]
    )
    async def select_category(self, interaction: discord.Interaction, select: ui.Select):
        cat_key = select.values[0]
        
        if cat_key == "inventory":
            from cogs.economy import EconomyCog
            # Invoke built-in inventory command logic if possible, or simple message
            # For now, simplistic response:
            await interaction.response.send_message("🎒 Hãy dùng lệnh `/tuido` để xem chi tiết.", ephemeral=True)
            return

        # Open Category Browser
        view = ShopCategoryView(interaction.user.id, cat_key)
        await view.send_initial_message(interaction)

# ==================== CATEGORY BROWSER ====================
class ShopCategoryView(ui.View):
    """
    Ephemeral view for browsing items in a category.
    """
    def __init__(self, user_id: int, category: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.category = category
        self.page = 0
        self.items_per_page = 10
        self.items_per_page = 10
        self.items = []
    
    async def load_items(self):
        """Fetch items matching category."""
        all_items = item_system.get_all_items()
        filtered = []
        
        # MAPPING LOGIC
        # Map JSON 'shop_category' to View Categories
        CAT_MAPPING = {
            "buff": "consumables",
            "fishing": "consumables", # baits
            "consumable": "consumables",
            "rod": "tools",
            "tool": "tools", 
            "gift": "gift",
            "vip": "vip",
            "vip_card": "vip",
            "decor": "decor"
        }
        
        for key, item in all_items.items():
            # 1. Check Buyable Flag
            flags = item.get("flags", {})
            if not flags.get("buyable", False):
                continue
            
            # 2. Determine Category
            # Check explicit flag first
            raw_cat = flags.get("shop_category")
            
            # If no flag, check top-level category field (for premium items)
            if not raw_cat:
                raw_cat = item.get("category")

            # If still no flag, infer from type
            if not raw_cat:
                raw_cat = item.get("type", "misc")
            
            # Map to View Category
            mapped_cat = CAT_MAPPING.get(raw_cat, "misc")
            
            # Additional Mapping for VIP Premium
            if raw_cat == "vip_premium": mapped_cat = "vip"
            
            # Special case: Decor type always goes to decor
            if item.get("type") == "decor": mapped_cat = "decor"
            
            if mapped_cat == self.category:
                filtered.append(item)
                
        # For Decor: Sort by Set to keep them together in pagination
        if self.category == "decor":
            filtered.sort(key=lambda x: x.get("attributes", {}).get("decor_set", "zzzz"))

        # SPECIAL: DYNAMIC ROD UPGRADE (For Tools)
        if self.category == "tools":
            try:
                from cogs.fishing.mechanics.rod_system import get_rod_data
                from configs.settings import ROD_LEVELS
                
                # Fetch user data
                level, durability = await get_rod_data(self.user_id)
                next_lvl = level + 1
                
                if next_lvl in ROD_LEVELS:
                    next_data = ROD_LEVELS[next_lvl]
                    price = next_data.get("cost", 0)
                    name = next_data.get("name", f"Cần Lv {next_lvl}")
                    
                    # Create Dummy Item
                    rod_item = {
                        "key": "dynamic_rod_upgrade",
                        "name": f"Nâng Cấp: {name}",
                        "price": {"buy": price, "currency": "seeds"},
                        "description": f"Cấp hiện tại: {level} -> {next_lvl}. Tăng độ bền và luck.",
                        "emoji": next_data.get("emoji", "🎣"),
                        "activation_command": "/nangcap",
                        "type": "upgrade",
                        "flags": {"buyable": True}
                    }
                    # Insert at TOP
                    filtered.insert(0, rod_item)
            except Exception as e:
                logger.error(f"[SHOP] Failed to load rod upgrade: {e}")

        self.items = filtered

    async def send_initial_message(self, interaction: discord.Interaction):
        await self.load_items()
        
        if not self.items:
            return await interaction.response.send_message(f"❌ Danh mục này chưa có vật phẩm nào hoặc đang hết hàng.", ephemeral=True)
            
        embed = await self._build_embed(interaction)
        self._refresh_components()
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    async def _build_embed(self, interaction) -> discord.Embed:
        cat_info = CATEGORIES.get(self.category, {"label": "Unknown", "emoji": "❓"})
        
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_items = self.items[start:end]
        total_pages = (len(self.items) - 1) // self.items_per_page + 1
        
        # Calculate Balance
        seeds = await get_user_balance(self.user_id)
        
        embed = discord.Embed(
            title=f"{cat_info['emoji']} {cat_info['label']}",
            description=f"💰 **Số dư:** {seeds:,} Hạt\n",
            color=0x3498db
        )
        embed.set_footer(text=f"Trang {self.page + 1}/{total_pages} • Tổng {len(self.items)} món")
        
        # Fetch ownership
        owned_map = {}
        if current_items:
            keys = [i['key'] for i in current_items]
            rows = await db_manager.fetchall(
               "SELECT item_id, quantity FROM inventory WHERE user_id = $1 AND item_id = ANY($2::text[])",
               (self.user_id, keys)
            )
            for r in rows:
                owned_map[r[0]] = r[1]

        # SPECIAL LOGIC FOR DECOR: Group by Set
        if self.category == "decor":
            from cogs.aquarium.constants import FENG_SHUI_SETS
            
            # 1. Group items by set
            items_by_set = {}
            misc_items = []
            
            for item in current_items:
                # Check set key
                set_key = None
                # Check attributes (JSON structure)
                attrs = item.get("attributes", {})
                if attrs and "decor_set" in attrs:
                    set_key = attrs["decor_set"]
                # Fallback to old dict structure (if any)
                elif item.get("set"):
                     set_key = item.get("set")
                
                if set_key and set_key in FENG_SHUI_SETS:
                    if set_key not in items_by_set: items_by_set[set_key] = []
                    items_by_set[set_key].append(item)
                else:
                    misc_items.append(item)
            
            # 2. Render Sets
            embed.description += "\n" # Spacing
            
            for set_key, set_items in items_by_set.items():
                set_info = FENG_SHUI_SETS[set_key]
                set_name = set_info.get("name", "Set Unknown")
                bonus = set_info.get("bonus_desc", "")
                
                field_value = f"✨ **Bonus:** {bonus}\n"
                for item in set_items:
                    price = item.get("price", {}).get("buy", 0)
                    owned = owned_map.get(item['key'], 0)
                    status = "✅" if owned > 0 else "⬜"
                    field_value += f"{status} **{item['name']}** - `{price:,} Hạt`\n"
                
                embed.add_field(name=f"{set_info['icon']} {set_name}", value=field_value, inline=False)
            
            # 3. Render Misc Items
            if misc_items:
                field_value = ""
                for item in misc_items:
                    price = item.get("price", {}).get("buy", 0)
                    owned = owned_map.get(item['key'], 0)
                    status = "✅" if owned > 0 else "⬜"
                    field_value += f"{status} **{item['name']}** - `{price:,} Hạt`\n"
                embed.add_field(name="🛋️ Nội Thất Khác", value=field_value, inline=False)
                
            return embed

        # DEFAULT LIST LOGIC (For other categories)
        for item in current_items:
            price = item.get("price", {}).get("buy", 0)
            owned = owned_map.get(item['key'], 0)
            status = f"✅ Đã có: {owned}" if owned > 0 else ""
            desc = item.get("description", "Không có mô tả.")
            
            # Determine Usage Hint
            usage = ""
            if item.get("type") == "decor":
                usage = "👉 Trang trí tại `/nha`"
            elif item.get('activation_command'):
                usage = f"👉 Dùng: `{item['activation_command']}`"
            elif item.get('type') == 'consumable':
                usage = "👉 Tự động dùng khi câu hoặc `/sudung`"
            
            # Format: [Emoji] Name - Price
            #         Description
            embed.description += f"\n**{item.get('emoji','📦')} {item['name']}** - `{price:,} Hạt` {status}\n_{desc}_\n{usage}\n"
            
        return embed

    def _refresh_components(self):
        self.clear_items()
        
        # 1. Item Select
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_items = self.items[start:end]
        
        options = []
        for item in current_items:
            price = item.get("price", {}).get("buy", 0)
            desc_short = item.get("description", "Vật phẩm shop")[:95] + "..." if len(item.get("description", "")) > 95 else item.get("description", "Vật phẩm shop")
            
            options.append(discord.SelectOption(
                label=item['name'][:100],
                value=item['key'],
                description=desc_short,
                emoji=item.get('emoji', '📦')
            ))
            
        if options:
            select = ui.Select(placeholder="🛒 Bấm vào đây để chọn món mua...", options=options, row=0)
            select.callback = self.on_item_select
            self.add_item(select)

        # 2. Pagination
        total_pages = (len(self.items) - 1) // self.items_per_page + 1
        if total_pages > 1:
            btn_prev = ui.Button(emoji="⬅️", style=discord.ButtonStyle.secondary, disabled=(self.page==0), row=1)
            btn_prev.callback = self.prev_page
            self.add_item(btn_prev)
            
            btn_next = ui.Button(emoji="➡️", style=discord.ButtonStyle.secondary, disabled=(self.page >= total_pages-1), row=1)
            btn_next.callback = self.next_page
            self.add_item(btn_next)

    # Callbacks
    async def prev_page(self, interaction):
        self.page = max(0, self.page - 1)
        await self._update(interaction)

    async def next_page(self, interaction):
        self.page += 1
        await self._update(interaction)
        
    async def _update(self, interaction):
        if interaction.user.id != self.user_id: return
        embed = await self._build_embed(interaction)
        self._refresh_components()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_item_select(self, interaction: discord.Interaction):
        item_key = interaction.data['values'][0]
        # Open Modal
        await interaction.response.send_modal(TransactionModal(item_key))

# ==================== TRANSACTION MODAL ====================
class TransactionModal(ui.Modal):
    def __init__(self, item_key: str):
        self.item_key = item_key
        item = item_system.get_item(item_key)
        self.item_name = item['name']
        title = f"Mua {self.item_name}"[:45]
        super().__init__(title=title)
        
        self.quantity = ui.TextInput(label="Số lượng", default="1", min_length=1, max_length=2)
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value)
            if qty <= 0: raise ValueError
        except:
             return await interaction.response.send_message("❌ Số lượng không hợp lệ.", ephemeral=True)
        
        # Check Item Data for Currency Options
        item = item_system.get_item(self.item_key)
        if not item: return
        
        # Determine available currencies
        # Generic items usually only seeds. Decor has leaf.
        # Check prices
        price_seeds = item.get("price", {}).get("buy", 0)
        attrs = item.get("attributes", {})
        price_leaf = attrs.get("price_leaf", 0)
        
        # If item has only seeds price (or is generic), instant buy (simplify flow)
        if price_leaf <= 0:
             from .logic import ShopController
             success, msg = await ShopController.process_purchase(interaction.user.id, self.item_key, qty, "seeds")
             color = 0x2ecc71 if success else 0xe74c3c
             embed = discord.Embed(description=msg, color=color)
             return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Multi-currency: Show Payment View
        view = PaymentMethodView(interaction.user.id, self.item_key, qty, price_seeds, price_leaf)
        embed = discord.Embed(
            title="💳 Chọn phương thức thanh toán",
            description=f"Bạn muốn mua **{qty}x {item['name']}**?",
            color=0xf1c40f
        )
        embed.add_field(name="Chi phí tạm tính", value=f"💰 Hạt: {price_seeds * qty:,}\n🍃 Xu: {price_leaf * qty:,}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PaymentMethodView(ui.View):
    def __init__(self, user_id, item_key, qty, price_seeds, price_leaf):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_key = item_key
        self.qty = qty
        
        # Button Seeds
        if price_seeds > 0:
            btn_seeds = ui.Button(label=f"{price_seeds*qty:,} Hạt", emoji="💰", style=discord.ButtonStyle.primary)
            btn_seeds.callback = self.pay_seeds
            self.add_item(btn_seeds)
            
        # Button Leaf
        if price_leaf > 0:
            btn_leaf = ui.Button(label=f"{price_leaf*qty:,} Xu", emoji="🍃", style=discord.ButtonStyle.success)
            btn_leaf.callback = self.pay_leaf
            self.add_item(btn_leaf)
            
    async def pay_seeds(self, interaction: discord.Interaction):
        await self._process(interaction, "seeds")

    async def pay_leaf(self, interaction: discord.Interaction):
        await self._process(interaction, "leaf")

    async def _process(self, interaction, currency):
        if interaction.user.id != self.user_id: return
        
        await interaction.response.defer()
        from .logic import ShopController
        success, msg = await ShopController.process_purchase(self.user_id, self.item_key, self.qty, currency)
        
        color = 0x2ecc71 if success else 0xe74c3c
        embed = discord.Embed(description=msg, color=color)
        await interaction.edit_original_response(embed=embed, view=None)
