"""Legendary fish hall of fame command.

Displays all legendary fish with their catchers and unlock conditions.
"""
import logging
import discord

from database_manager import db_manager
from ..constants import LEGENDARY_FISH

logger = logging.getLogger("fishing")


class LegendaryHallView(discord.ui.View):
    """Paginated view for legendary fish hall of fame."""
    
    def __init__(self, legendary_list, current_index=0):
        super().__init__(timeout=300)
        self.legendary_list = legendary_list
        self.current_index = current_index
        self.message = None
    
    @discord.ui.button(label="← Cá Trước", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_buttons()
            await self.update_message(interaction)
    
    @discord.ui.button(label="Cá Tiếp →", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index < len(self.legendary_list) - 1:
            self.current_index += 1
            self.update_buttons()
            await self.update_message(interaction)
    
    def update_buttons(self):
        """Update button states based on current page."""
        prev_btn = None
        next_btn = None
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label and "← " in child.label:
                    prev_btn = child
                elif child.label and " →" in child.label:
                    next_btn = child
        if prev_btn:
            prev_btn.disabled = self.current_index == 0
        if next_btn:
            next_btn.disabled = self.current_index == len(self.legendary_list) - 1
    
    async def update_message(self, interaction: discord.Interaction):
        """Update the message with new page content."""
        fish, catchers = self.legendary_list[self.current_index]
        embed = self.build_embed(fish, catchers)
        await interaction.response.edit_message(embed=embed, view=self)
    
    def build_embed(self, fish, catchers):
        """Build embed for a legendary fish."""
        emoji = fish['emoji']
        fish_key = fish['key']
        price = fish.get('sell_price', 0)
        
        # Determine conditions for each legendary fish
        conditions = self._get_conditions(fish_key)
        
        if catchers:
            # Fish has been caught - show full info with conditions
            catcher_text = "\n".join([f"⭐ **{c['username']}**" for c in catchers])
            
            embed = discord.Embed(
                title=f"🏆 {emoji} Huyền Thoại #{self.current_index + 1}",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="💎 Giá Bán", value=f"{price} Hạt", inline=True)
            embed.add_field(name="📊 Số Người Bắt", value=f"{len(catchers)}", inline=True)
            embed.add_field(name="📋 Nhiệm Vụ", value=conditions, inline=False)
            embed.add_field(name="🏅 Những Người Chinh Phục", value=catcher_text, inline=False)
            # Set image for caught legendary fish
            fish_image_url = fish.get('image_url')
            if fish_image_url:
                embed.set_image(url=fish_image_url)
        else:
            # Fish not caught yet - show ??? with hidden info
            embed = discord.Embed(
                title=f"❓ ??? Huyền Thoại #{self.current_index + 1}",
                description="Cá huyền thoại bí ẩn chưa được khám phá...",
                color=discord.Color.greyple()
            )
            
            embed.add_field(name="💎 Giá Bán", value="??? Hạt", inline=True)
            embed.add_field(name="📊 Số Người Bắt", value="0", inline=True)
            embed.add_field(name="📋 Nhiệm Vụ", value=conditions, inline=False)
            embed.add_field(name="🏅 Những Người Chinh Phục", value="Chưa có ai bắt được...\n🎯 Bạn có thể là người đầu tiên!", inline=False)
        
        page_num = self.current_index + 1
        total_pages = len(self.legendary_list)
        embed.set_footer(text=f"Trang {page_num}/{total_pages} • 🎣 Hãy hoàn thành nhiệm vụ để gặp huyền thoại!")
        
        return embed
    
    def _get_conditions(self, fish_key: str) -> str:
        """Get condition/task description for each legendary fish."""
        conditions_map = {
            "thuong_luong": "🌊 **Nghi Thức Hiến Tế**\n📌 Dùng `/hiente` để hiến tế 3 sinh vật to lớn (> 150 hạt)\n📌 Nhận bùa chú để dẫn dụ \"Bóng Ma Dưới Đáy Sông\" xuất hiện",
            "ca_ngan_ha": "🌌 **Kết Nối Tinh Tú**\n📌 Săn Mảnh Sao Băng từ sự kiện lúc 21:00 hằng ngày\n📌 Chế tạo **Tinh Cầu Không Gian** (5 Mảnh + 1 Ngọc Trai)\n📌 Sử dụng Tinh Cầu để giải mã tín hiệu vũ trụ bí ẩn",
            "ca_phuong_hoang": "🔥 **Nghi Lễ Ấp Trứng Phượng Hoàng**\n📌 Tìm **Lông Vũ Lửa** (Tỉ lệ rớt khi câu hụt Boss)\n📌 Sử dụng Lông Vũ để bắt đầu mini-game ấp trứng\n📌 Tích năng lượng 80-100% (Push-Your-Luck)\n📌 Tỉ lệ triệu hồi = % năng lượng (100% = chắc chắn)",
            "cthulhu_con": "🗺️ **Bản Đồ Hắc Ám**\n📌 Thu thập 4 Mảnh Bản Đồ rách nát từ rương kho báu\n📌 Ghép lại thành Bản Đồ hoàn chỉnh\n📌 Kích hoạt để tìm hang ổ của \"Cổ Thần Say Ngủ\" (Hiệu lực 10 lần câu)",
            "ca_voi_52hz": "📡 **Tần Số Cô Đơn**\n📌 Sở hữu **Máy Dò Sóng** chuyên dụng\n📌 Dùng lệnh `/dosong` để quét tín hiệu đại dương\n📌 Tìm ra tần số **52Hz** để kết nối với sinh vật cô độc nhất thế giới",
        }
        return conditions_map.get(fish_key, "❌ Chưa xác định điều kiện")


async def legendary_hall_of_fame_action(cog, ctx_or_interaction, is_slash: bool):
    """Hall of fame logic with pagination - one fish per page, show tasks & conditions.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        is_slash: Whether this is a slash command
    """
    channel = ctx_or_interaction.channel
    guild_id = ctx_or_interaction.guild.id
    # Handle both Interaction (slash) and Context (prefix) objects
    client = ctx_or_interaction.client if is_slash else ctx_or_interaction.bot
    
    # Fetch all legendary catches
    legendary_catches = {}
    try:
        # 1. Fetch standard legislative fish from fish_collection
        # Use fetch and $n placeholders
        rows = await db_manager.fetch(
            "SELECT user_id, fish_id FROM fish_collection WHERE fish_id IN ($1, $2, $3, $4, $5)",
            'thuong_luong', 'ca_ngan_ha', 'ca_phuong_hoang', 'cthulhu_con', 'ca_voi_52hz'
        )
        
        for user_id, fish_key in rows:
            if fish_key not in legendary_catches:
                legendary_catches[fish_key] = []
            
            try:
                user = await client.fetch_user(user_id)
                legendary_catches[fish_key].append({
                    "user_id": user_id,
                    "username": user.name,
                    "avatar_url": user.avatar.url if user.avatar else None
                })
            except Exception as e:
                legendary_catches[fish_key].append({
                    "user_id": user_id,
                    "username": f"User {user_id}",
                    "avatar_url": None
                })
        
        # 2. Fetch "Cá Isekai" from inventory (it's an item, not in fish_collection)
        isekai_rows = await db_manager.fetch(
            "SELECT user_id FROM inventory WHERE item_id = 'ca_isekai' AND quantity > 0"
        )
        
        if isekai_rows:
            legendary_catches['ca_isekai'] = []
            for (user_id,) in isekai_rows:
                try:
                    user = await client.fetch_user(user_id)
                    legendary_catches['ca_isekai'].append({
                        "user_id": user_id,
                        "username": user.name,
                        "avatar_url": user.avatar.url if user.avatar else None
                    })
                except:
                    legendary_catches['ca_isekai'].append({
                        "user_id": user_id,
                        "username": f"User {user_id}",
                        "avatar_url": None
                    })

    except Exception as e:
        logger.error(f"[LEGENDARY] Error fetching hall of fame: {e}")
    
    # Create list of ALL legendary fish
    # CONDITION: Show 'ca_isekai' ONLY if at least one person has caught it (is in legendary_catches)
    visible_legendaries = []
    for fish in LEGENDARY_FISH:
        if fish['key'] == 'ca_isekai':
            # Only show if discovered
            if 'ca_isekai' in legendary_catches and legendary_catches['ca_isekai']:
                visible_legendaries.append(fish)
        else:
            visible_legendaries.append(fish)

    all_legendaries = [(fish, legendary_catches.get(fish['key'], []))
                       for fish in visible_legendaries]
    
    # Send first page
    view = LegendaryHallView(all_legendaries)
    view.update_buttons()
    first_fish, first_catchers = all_legendaries[0]
    embed = view.build_embed(first_fish, first_catchers)
    
    if is_slash:
        message = await ctx_or_interaction.followup.send(embed=embed, view=view)
    else:
        message = await ctx_or_interaction.reply(embed=embed, view=view)
    
    view.message = message
    
    logger.info(f"[LEGENDARY] Hall of fame displayed for guild {guild_id}")
