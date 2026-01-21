
import discord
from discord import ui
from ..logic.market import MarketEngine
from ..logic.housing import HousingEngine
from ..logic.render import RenderEngine
from ..logic.effect_manager import SetsDataLoader
from core.services.vip_service import VIPEngine
from ..constants import VIP_PRICES, VIP_NAMES, VIP_COLORS

# ==================== MAIN DASHBOARD VIEW ====================
class AquariumDashboardView(ui.View):
    """Main Controller for Aquarium."""
    def __init__(self, user_id: int):
        super().__init__(timeout=None) # Persistent view ideally, but for now standard
        self.user_id = user_id

    @ui.button(label="Cửa Hàng", style=discord.ButtonStyle.success, emoji="🛍️", row=0)
    async def shop_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id: 
            return await interaction.response.send_message("❌ Không phải nhà của bạn!", ephemeral=True)
            
        embed = discord.Embed(
            title="🏪 Cửa Hàng Nội Thất", 
            description="Chào mừng! Bạn muốn mua gì hôm nay?", 
            color=0xe67e22
        )
        view = DecorShopView(self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="Trang Trí", style=discord.ButtonStyle.primary, emoji="🛋️", row=0)
    async def decor_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
             return await interaction.response.send_message("❌ Không phải nhà của bạn!", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        # Load Data
        slots = await HousingEngine.get_slots(self.user_id)
        inventory = await HousingEngine.get_inventory(self.user_id)
        visuals = RenderEngine.generate_view(slots)
        
        embed = discord.Embed(
            title=f"🛋️ Thiết Kế Nội Thất",
            description=f"👇 **Chọn VỊ TRÍ cần sửa đổi:**\n\n{visuals}",
            color=0x9b59b6
        )
        embed.set_footer(text=f"Kho: {len(inventory)} loại vật phẩm")
        
        view = DecorPlacementView(self.user_id, inventory, slots)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @ui.button(label="VIP Club", style=discord.ButtonStyle.secondary, emoji="💎", row=0)
    async def vip_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id: return
        
        vip_data = await VIPEngine.get_vip_data(self.user_id)
        desc = "Chào mừng đến với CLB Thượng Lưu!\nHãy chọn gói thành viên để hưởng đặc quyền."
        color = 0x2b2d31
        
        if vip_data:
            tier = vip_data['tier']
            tier_name = VIP_NAMES.get(tier, "Unknown")
            desc = f"**Bạn đang là: {tier_name}**\n⏳ Hết hạn: `{vip_data['expiry']}`\n\nBạn có thể gia hạn hoặc nâng cấp."
            color = VIP_COLORS.get(tier, 0xf1c40f)

        embed = discord.Embed(
            title="💎 Hệ Thống Thành Viên (VIP)",
            description=desc,
            color=color
        )
        view = VIPSubscriptionView(self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==================== SHOP SYSTEM ====================
class DecorShopView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(DecorSelect(user_id))

class DecorSelect(ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id
        options = []
        items_data = SetsDataLoader.get_items()
        sets_data = SetsDataLoader.get_sets()
        
        for key, item in items_data.items():
            set_key = item.get('set_id')
            label = item['name']
            if set_key and set_key in sets_data:
                set_icon = sets_data[set_key].get('icon', '🌟')
                label = f"{set_icon} {label}"
                
            options.append(discord.SelectOption(
                label=label,
                value=key,
                description=f"{item['price_seeds']:,} S + {item['price_leaf']} 🍃",
                emoji=item['icon']
            ))
            
        super().__init__(
            placeholder="🛍️ Chọn vật phẩm...",
            min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        
        items_data = SetsDataLoader.get_items()
        sets_data = SetsDataLoader.get_sets()
            
        item_key = self.values[0]
        item = items_data[item_key]
        
        embed = discord.Embed(
            title=f"{item['icon']} {item['name']}",
            description=f"**Mô tả:** {item['desc']}\n\n"
                        f"💰 **Giá:** {item['price_seeds']:,} Hạt\n"
                        f"🍃 **Xu Lá:** {item['price_leaf']}\n\n"
                        f"✨ **Charm:** +{item.get('charm', 0)}\n"
                        f"Vị trí đặt: `{item['type']}`",
            color=0x2ecc71
        )
        set_key = item.get('set_id')
        if set_key and set_key in sets_data:
             set_data = sets_data[set_key]
             bonus_text = ", ".join([f"+{v*100:.0f}% {k}" if isinstance(v, float) else f"+{v} {k}" for k, v in set_data.get('bonus', {}).items()])
             embed.add_field(name=f"🌟 Thuộc Set: {set_data['name']}", value=f"Bonus (2 mảnh): {bonus_text}", inline=False)
        
        view = DecorConfirmView(self.user_id, item_key)
        await interaction.response.edit_message(embed=embed, view=view)

class DecorConfirmView(ui.View):
    def __init__(self, user_id: int, item_key: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_key = item_key
        
        items_data = SetsDataLoader.get_items()
        item = items_data.get(item_key)
        if not item:
            return
        cost_magic = item.get('price_magic_fruit', 0)
        
        if cost_magic > 0:
            # Special Item (Seeds + Fruit)
            cost_seeds = item.get('price_seeds', 0)
            btn = ui.Button(
                label=f"Đổi ({cost_seeds:,} Hạt + {cost_magic} Quả)", 
                style=discord.ButtonStyle.danger, 
                emoji="🍎"
            )
            btn.callback = self.buy_special
            self.add_item(btn)
        else:
            # Standard Item
            btn_seeds = ui.Button(label="Mua bằng Hạt", style=discord.ButtonStyle.green, emoji="💰")
            btn_seeds.callback = self.buy_seeds
            self.add_item(btn_seeds)

            btn_leaf = ui.Button(label="Mua bằng Xu Lá", style=discord.ButtonStyle.blurple, emoji="🍃")
            btn_leaf.callback = self.buy_leaf
            self.add_item(btn_leaf)

        # Back Button always present
        btn_back = ui.Button(label="Quay lại", style=discord.ButtonStyle.secondary, emoji="↩️")
        btn_back.callback = self.back
        self.add_item(btn_back)

    async def buy_seeds(self, interaction: discord.Interaction):
        await self._buy(interaction, 'seeds')

    async def buy_leaf(self, interaction: discord.Interaction):
        await self._buy(interaction, 'leaf')
        
    async def buy_special(self, interaction: discord.Interaction):
        await self._buy(interaction, 'magic_fruit')

    async def back(self, interaction: discord.Interaction):
         if interaction.user.id != self.user_id: return
         embed = discord.Embed(title="🏪 Cửa Hàng Nội Thất", description="Chọn món khác nào...", color=0xe67e22)
         await interaction.response.edit_message(embed=embed, view=DecorShopView(self.user_id))

    async def _buy(self, interaction, currency):
        if interaction.user.id != self.user_id: return
        await interaction.response.defer()
        
        success, msg = await MarketEngine.buy_decor(self.user_id, self.item_key, currency)
        
        if success:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="✅ Giao dịch thành công", value=msg)
            # Disable all
            for child in self.children: child.disabled = True
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
        else:
            await interaction.followup.send(msg, ephemeral=True)

# ==================== PLACEMENT SYSTEM ====================
class DecorPlacementView(ui.View):
    def __init__(self, user_id: int, inventory: dict, slots: list):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_slot = 0
        self.page = 0
        self.items_per_page = 23 # Reserve 1 for 'Empty', buttons take row 2
        
        self.full_inventory = inventory
        self.slots = slots
        
        self._refresh_components()

    def _refresh_components(self):
        """Re-builds components based on state."""
        self.clear_items()
        
        # 1. Slot Select (Row 0)
        self.slot_select = SlotSelect(self.user_id, self.selected_slot)
        self.add_item(self.slot_select)
        
        # 2. Inventory Select (Row 1)
        # Slice Inventory
        items = list(self.full_inventory.items())
        total_pages = (len(items) - 1) // self.items_per_page + 1
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_page_items = dict(items[start:end])
        
        self.inv_select = InventorySelect(self.user_id, self.selected_slot, current_page_items)
        self.add_item(self.inv_select)
        
        # 3. Controls (Row 2)
        # Prev Button
        if self.page > 0:
            btn_prev = ui.Button(label="Trang trước", style=discord.ButtonStyle.secondary, emoji="⬅️", row=2)
            btn_prev.callback = self.prev_page
            self.add_item(btn_prev)
            
        # Save Button (Center)
        self.add_item(SaveLayoutButton(self.user_id))
        
        # Next Button
        if (self.page + 1) < total_pages:
            btn_next = ui.Button(label="Trang sau", style=discord.ButtonStyle.secondary, emoji="➡️", row=2)
            btn_next.callback = self.next_page
            self.add_item(btn_next)

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        self.page = max(0, self.page - 1)
        await self.update_view(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        self.page += 1
        await self.update_view(interaction)

    async def update_view(self, interaction: discord.Interaction):
        # Allow callback to be defer or edit
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        # Fetch fresh data
        self.slots = await HousingEngine.get_slots(self.user_id)
        self.full_inventory = await HousingEngine.get_inventory(self.user_id)
        visuals = RenderEngine.generate_view(self.slots)
        
        embed = interaction.message.embeds[0]
        # Calculate Page Info
        total_items = len(self.full_inventory)
        total_pages = (total_items - 1) // self.items_per_page + 1
        page_info = f"(Trang {self.page + 1}/{total_pages})" if total_pages > 1 else ""
        
        embed.description = f"👇 **Đang chọn nội thất cho: VỊ TRÍ {self.selected_slot + 1}**\n{page_info}\n\n{visuals}"
        embed.set_footer(text=f"Kho: {total_items} loại vật phẩm")
        
        # Re-render components
        self._refresh_components()
        
        await interaction.edit_original_response(embed=embed, view=self)

class SlotSelect(ui.Select):
    def __init__(self, user_id: int, current: int):
        options = []
        labels = ["Tầng Giữa - Trái", "Tầng Nước - Cao", "Trung Tâm", "Tầng Giữa - Phải", "Góc Phải"]
        for i in range(5):
            options.append(discord.SelectOption(
                label=f"Vị trí {i+1}: {labels[i]}", value=str(i), default=(i==current)
            ))
        super().__init__(placeholder="Chọn vị trí...", options=options, row=0)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        self.view.selected_slot = int(self.values[0])
        # Reset page on slot change? No, keep it.
        await self.view.update_view(interaction)

class InventorySelect(ui.Select):
    def __init__(self, user_id: int, slot_idx: int, inventory: dict):
        options = [discord.SelectOption(label="❌ Gỡ Bỏ", value="EMPTY_SLOT", emoji="🗑️")]
        
        items_data = SetsDataLoader.get_items()
        for k, qty in inventory.items():
            item = items_data.get(k, {})
            options.append(discord.SelectOption(
                label=f"{item.get('name', k)} (x{qty})", value=k, emoji=item.get('icon', '📦')
            ))
            
        super().__init__(placeholder="Chọn nội thất để đặt...", options=options, row=1)
        self.user_id = user_id
        self.slot_idx = slot_idx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        val = self.values[0]
        target = None if val == "EMPTY_SLOT" else val
        
        success, msg = await HousingEngine.update_slot(self.user_id, self.slot_idx, target)
        if success:
            await self.view.update_view(interaction)
        else:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

class SaveLayoutButton(ui.Button):
    def __init__(self, user_id: int):
        super().__init__(style=discord.ButtonStyle.primary, label="Lưu & Cập Nhật Nhà", emoji="💾", row=2)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        await interaction.response.defer(ephemeral=True)
        
        from ..utils import refresh_aquarium_dashboard # Lazy import
        
        success = await refresh_aquarium_dashboard(self.user_id, interaction.client)
        if success:
            await interaction.followup.send("✅ Đã cập nhật nhà thành công!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Lỗi cập nhật (Có thể chưa tạo thread?)", ephemeral=True)

# ==================== VIP VIEWS ====================
class VIPSubscriptionView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(VIPSelect(user_id))

class VIPSelect(ui.Select):
    def __init__(self, user_id: int):
        options = []
        for tier, price in VIP_PRICES.items():
            name = VIP_NAMES.get(tier, f"Tier {tier}")
            options.append(discord.SelectOption(
                label=name, value=str(tier), description=f"{price:,} Hạt/tháng"
            ))
        super().__init__(placeholder="Chọn gói VIP...", options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        tier = int(self.values[0])
        
        embed = discord.Embed(
            title=f"👑 Xác nhận: {VIP_NAMES[tier]}",
            description=f"Giá: **{VIP_PRICES[tier]:,} Hạt**\nThời hạn: 30 ngày.",
            color=VIP_COLORS.get(tier, 0)
        )
        view = VIPConfirmView(self.user_id, tier)
        await interaction.response.edit_message(embed=embed, view=view)

class VIPConfirmView(ui.View):
    def __init__(self, user_id: int, tier: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.tier = tier

    @ui.button(label="Xác Nhận Đăng Ký", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id: return
        await interaction.response.defer()
        
        success, msg = await VIPEngine.subscribe(self.user_id, self.tier)
        if success:
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

# ==================== AUTO VISIT VIEW ====================
class AutoVisitView(ui.View):
    """View manage Auto-Visit Subscription."""
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @ui.button(label="Đăng Ký (50k/tháng)", style=discord.ButtonStyle.success, emoji="✅")
    async def subscribe(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id: return
        
        await interaction.response.defer(ephemeral=True)
        
        # 1. Payment
        COST = 50000
        DURATION_DAYS = 30
        
        from database_manager import get_user_balance, add_seeds, db_manager
        
        balance = await get_user_balance(interaction.user.id)
        if balance < COST:
            await interaction.followup.send(f"❌ Không đủ hạt! Cần {COST:,} hạt.", ephemeral=True)
            return
            
        await add_seeds(interaction.user.id, -COST, "vip_autovisit", "service")
        
        # 2. Register
        from datetime import datetime, timedelta
        now = datetime.now()
        expiry = (now + timedelta(days=DURATION_DAYS)).isoformat()
        
        await db_manager.execute(
            """
            INSERT INTO vip_auto_tasks (user_id, task_type, expires_at, last_run_at)
            VALUES (?, 'auto_visit', ?, ?)
            ON CONFLICT(user_id, task_type) DO UPDATE SET
                expires_at = ?,
                last_run_at = ?
            """,
            (interaction.user.id, expiry, now.isoformat(), expiry, now.isoformat())
        )
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.description = f"✅ **Đăng ký thành công!**\n\nBot sẽ tự động thăm 5 nhà hàng xóm mỗi ngày.\nNhận 100 seeds/ngày.\nThời hạn: 30 ngày."
        embed.clear_fields()
        
        # Update view to disable button
        for child in self.children: child.disabled = True
        
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
