
import discord
from typing import Optional
from core.logging import get_logger
from .logic.housing import HousingEngine
from .logic.render import RenderEngine
from .ui.embeds import create_aquarium_dashboard

logger = get_logger("aquarium_utils")

async def refresh_aquarium_dashboard(user_id: int, bot: discord.Client) -> bool:
    """
    Refreshes the Aquarium Dashboard in the user's home thread.
    - Updates existing message if found.
    - Resends if old/deleted.
    - DEBOUNCED: Max 1 refresh per 30 seconds per thread.
    """
    import time
    
    if not hasattr(bot, '_aquarium_last_refresh'):
        bot._aquarium_last_refresh = {}
    
    now = time.time()
    last_refresh = bot._aquarium_last_refresh.get(user_id, 0)
    
    if now - last_refresh < 30:
        return False
    
    bot._aquarium_last_refresh[user_id] = now
    
    try:
        # Lazy import to avoid circular dependency
        from .ui.views import AquariumDashboardView
        
        thread_id = await HousingEngine.get_home_thread_id(user_id)
        if not thread_id: return False

        # Get Thread
        thread = bot.get_channel(thread_id)
        if not thread:
            try:
                thread = await bot.fetch_channel(thread_id)
            except Exception:
                return False

        # Prepare Data
        slots = await HousingEngine.get_slots(user_id)
        inventory = await HousingEngine.get_inventory(user_id)
        stats = await HousingEngine.calculate_home_stats(user_id)
        visuals = RenderEngine.generate_view(slots)
        theme_url = await HousingEngine.get_theme(user_id)
        
        # User Info
        try:
            user = bot.get_user(user_id) or await bot.fetch_user(user_id)
            user_name = user.display_name
            user_avatar = user.display_avatar.url
        except Exception:
            user_name = thread.name.replace('Nhà của ', '')
            user_avatar = None

        # Build Embed & View
        embed = create_aquarium_dashboard(
            user_name=user_name,
            user_avatar=user_avatar,
            view_visuals=visuals,
            stats=stats,
            inventory_count=len(inventory),
            theme_url=theme_url
        )
        view = AquariumDashboardView(user_id)

        # Smart Message Handling
        last_message = None
        async for msg in thread.history(limit=1):
            last_message = msg
            break

        old_dashboard_id = await HousingEngine.get_dashboard_message_id(user_id)
        
        # Scenario 0: Adopt Orphan (If last message looks like valid dashboard)
        if not old_dashboard_id and last_message and last_message.author.id == bot.user.id:
            # Simple check title
            if last_message.embeds and "Nhà của" in (last_message.embeds[0].title or ""):
                old_dashboard_id = last_message.id
                await HousingEngine.set_dashboard_message_id(user_id, old_dashboard_id)

        # Scenario 1: Update Existing
        if old_dashboard_id and last_message and last_message.id == old_dashboard_id:
            try:
                await last_message.edit(embed=embed, view=view)
                return True
            except discord.NotFound:
                pass # Message deleted, fall to resend

        # Scenario 2: Resend (Delete old if exists but buried?)
        # Fix: Check if old message is the STARTER message (ID == Thread ID for Forums).
        # If it is, DO NOT DELETE (preserves thumbnail). Just remove buttons.
        if old_dashboard_id:
            try:
                old_msg = await thread.fetch_message(old_dashboard_id)
                
                is_starter = (old_msg.id == thread.id)
                if is_starter:
                    # Strip buttons, keep embed/content for thumbnail
                    await old_msg.edit(view=None)
                else:
                    await old_msg.delete()
            except Exception:
                pass

        # Send New
        msg = await thread.send(embed=embed, view=view)
        await HousingEngine.set_dashboard_message_id(user_id, msg.id)
        return True

    except Exception as e:
        logger.error(f"Failed to refresh dashboard for {user_id}: {e}", exc_info=True)
        return False
