
import discord
from discord import ui
from ..core.shop import aquarium_shop
from ..constants import DECOR_ITEMS, FENG_SHUI_SETS

class DecorShopView(ui.View):
    """View for browsing and buying Decor Items."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(DecorSelect(user_id))

class DecorSelect(ui.Select):
    """Dropdown to select a decor item to view details/buy."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        
        options = []
        for key, item in DECOR_ITEMS.items():
            # Add Set Icon if applicable
            set_key = item.get('set')
            label = item['name']
            if set_key and set_key in FENG_SHUI_SETS:
                set_icon = FENG_SHUI_SETS[set_key]['icon']
                label = f"{set_icon} {label}"
                
            options.append(discord.SelectOption(
                label=label,
                value=key,
                description=f"{item['price_seeds']:,} S + {item['price_leaf']} 🍃 | {item['desc'][:50]}",
                emoji=item['icon']
            ))
            
        super().__init__(
            placeholder="🛍️ Chọn vật phẩm để xem chi tiết & mua...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Menu này không dành cho bạn!", ephemeral=True)
            
        item_key = self.values[0]
        item = DECOR_ITEMS[item_key]
        
        # Create confirmation embed
        embed = discord.Embed(
            title=f"{item['icon']} {item['name']}",
            description=f"**Mô tả:** {item['desc']}\n\n"
                        f"💰 **Giá:** {item['price_seeds']:,} Seeds\n"
                        f"🍃 **Xu Lá:** {item['price_leaf']}\n\n"
                        f"Vị trí đặt: `{item['type']}`",
            color=0x2ecc71
        )
        
        # Show Set Info
        set_key = item.get('set')
        if set_key and set_key in FENG_SHUI_SETS:
            set_data = FENG_SHUI_SETS[set_key]
            embed.add_field(
                name=f"🌟 Thuộc Set: {set_data['name']}", 
                value=f"Thu thập đủ {len(set_data['required'])} món để kích hoạt:\n*{set_data['bonus_desc']}*",
                inline=False
            )
            
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/123/store.png") # Placeholder
        
        # Update view with Buy Button for this specific item
        view = DecorConfirmView(self.user_id, item_key)
        await interaction.response.edit_message(embed=embed, view=view)

class DecorConfirmView(ui.View):
    """View to confirm purchase."""
    
    def __init__(self, user_id: int, item_key: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_key = item_key
    
    @ui.button(label="Mua Ngay", style=discord.ButtonStyle.green, emoji="🛒")
    async def buy_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return
            
        await interaction.response.defer()
        
        # Call Shop Logic
        success, msg = await aquarium_shop.buy_decor(self.user_id, self.item_key)
        
        if success:
             # Disable buttons
            for child in self.children:
                child.disabled = True
            
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="Trạng thái", value=msg)
            
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
        else:
            await interaction.followup.send(msg, ephemeral=True)

    @ui.button(label="Quay lại", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return
            
        # Return to main shop View
        embed = discord.Embed(title="🏪 Cửa Hàng Nội Thất", description="Chào mừng! Bạn muốn mua gì hôm nay?", color=0xe67e22)
        view = DecorShopView(self.user_id)
        await interaction.response.edit_message(embed=embed, view=view)


# ==================== PLACEMENT VIEWS ====================
from ..core.housing import housing_manager
from .render import render_engine

class DecorPlacementView(ui.View):
    """View to arrange decor in 5 slots."""
    
    def __init__(self, user_id: int, inventory: dict, slots: list):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_slot = 0 # Default Slot 1
        
        # 1. Slot Selector
        self.slot_select = SlotSelect(user_id, self.selected_slot)
        self.add_item(self.slot_select)
        
        # 2. Inventory Selector (Pre-loaded)
        self.current_inv_select = InventorySelect(user_id, self.selected_slot, inventory)
        self.add_item(self.current_inv_select)
        
        # 3. Save Button (Updates Forum Thread)
        self.add_item(SaveLayoutButton(user_id))
        
        # 4. Done Button
        self.add_item(DoneButton(user_id))

    async def update_view(self, interaction: discord.Interaction):
        """Refreshes the view content."""
        await interaction.response.defer()
        
        # Re-fetch data
        slots = await housing_manager.get_slots(self.user_id)
        inventory = await housing_manager.get_inventory(self.user_id)
        
        # Re-render ASCII
        visuals = render_engine.generate_view(slots)
        embed = interaction.message.embeds[0]
        # Update Description to show active slot
        embed = discord.Embed(
            title=f"🛋️ Thiết Kế Nội Thất",
            description=f"👇 **Đang chọn nội thất cho: VỊ TRÍ {self.selected_slot + 1}**\n\n*Chọn 'Lưu' để cập nhật thread.*",
            color=0x9b59b6
        )
        embed.set_footer(text=f"Kho: {len(inventory)} loại vật phẩm")
        embed.add_field(name="🖼️ Bể Cá & Nội Thất", value=visuals, inline=False)
        
        # Update Slot Select (to show current selection)
        self.remove_item(self.slot_select)
        self.slot_select = SlotSelect(self.user_id, self.selected_slot)
        self.add_item(self.slot_select)
        
        # Update Inventory Select
        self.remove_item(self.current_inv_select) # Remove old
        self.current_inv_select = InventorySelect(self.user_id, self.selected_slot, inventory)
        self.add_item(self.current_inv_select)
        
        await interaction.edit_original_response(embed=embed, view=self)


class SlotSelect(ui.Select):
    """Select which slot (1-5) to modify."""
    def __init__(self, user_id: int, current_slot: int):
        # Map indices to descriptions based on render.py layout
        # 0: Mid Left, 1: Top Center (Water), 2: Mid Center, 3: Mid Right, 4: Far Right
        slot_descriptions = [
            "Tầng Giữa - Trái",        # Slot 1
            "Tầng Nước - Cao (Bơi)",   # Slot 2
            "Tầng Giữa - Trung Tâm",   # Slot 3
            "Tầng Giữa - Phải",        # Slot 4
            "Tầng Giữa - Góc"          # Slot 5
        ]
        
        options = []
        for i in range(5):
            desc = slot_descriptions[i] if i < len(slot_descriptions) else "Vị trí mở rộng"
            options.append(discord.SelectOption(
                label=f"Vị trí {i+1}: {desc}", 
                value=str(i),
                description=f"Sửa nội thất {desc}",
                default=(i == current_slot),
            ))
            
        super().__init__(placeholder="Chọn vị trí...", min_values=1, max_values=1, options=options, row=0)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: 
            return await interaction.response.send_message("❌ Không phải nhà của bạn!", ephemeral=True)
            
        view: DecorPlacementView = self.view
        view.selected_slot = int(self.values[0])
        
        # Refresh View
        await view.update_view(interaction)

class InventorySelect(ui.Select):
    """Select item from inventory to place."""
    def __init__(self, user_id: int, slot_index: int, inventory: dict):
        options = []
        
        # Option to Clear Slot
        options.append(discord.SelectOption(
            label="❌ Gỡ Bỏ / Trống",
            value="EMPTY_SLOT",
            description="Làm trống vị trí này",
            emoji="🗑️"
        ))
        
        # Logic to limit options (Discord max 25)
        count = 1
        for item_key, quantity in inventory.items():
            if count >= 24: break # Reserve 1 for EMPTY option
            item_data = DECOR_ITEMS.get(item_key, {})
            name = item_data.get('name', item_key)
            icon = item_data.get('icon', '📦')
            
            options.append(discord.SelectOption(
                label=f"{name} (x{quantity})",
                value=item_key,
                description=f"Đặt {name} vào vị trí {slot_index+1}",
                emoji=icon
            ))
            count += 1
            
        super().__init__(placeholder="Chọn nội thất để đặt...", min_values=1, max_values=1, options=options, row=1)
        self.user_id = user_id
        self.slot_index = slot_index
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        
        item_key = self.values[0]
        target_item = None if item_key == "EMPTY_SLOT" else item_key
        
        view: DecorPlacementView = self.view
        
        # Execute Update (Interaction handled inside updated_view/defer)
        success, msg = await housing_manager.update_slot(self.user_id, self.slot_index, target_item)
        
        if success:
            await view.update_view(interaction)
        else:
            await interaction.response.send_message(f"❌ Lỗi: {msg}", ephemeral=True)

class SaveLayoutButton(ui.Button):
    def __init__(self, user_id: int):
        super().__init__(style=discord.ButtonStyle.primary, label="Lưu & Cập Nhật Nhà", emoji="💾", row=2)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        await interaction.response.defer(ephemeral=True)

        # Trigger Smart Dashboard Refresh
        success = await housing_manager.refresh_dashboard(self.user_id, interaction.client)
        
        if success:
            await interaction.followup.send("✅ Đã cập nhật giao diện ngoài Thread!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Lỗi cập nhật hoặc chưa có nhà.", ephemeral=True)

class DoneButton(ui.Button):
    def __init__(self, user_id: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="Xong", emoji="✅", row=2)
        self.user_id = user_id
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        await interaction.response.edit_message(content="✅ Đã lưu thiết kế!", view=None)
