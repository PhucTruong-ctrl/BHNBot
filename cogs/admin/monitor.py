
import asyncio
import discord
from discord.ext import commands, tasks
import importlib
import sys
import logging
from database_manager import db_manager
import configs.settings as settings

class SystemMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SystemMonitor")
        self.db = db_manager
        self.last_config_time = 0
        self._reload_lock = asyncio.Lock()
        self.monitor_config_changes.start()

    def cog_unload(self):
        self.monitor_config_changes.cancel()

    @tasks.loop(seconds=10)
    async def monitor_config_changes(self):
        """Poll database for config changes."""
        try:
            # Check last_config_update timestamp
            # Using global_event_state table (key='last_config_update')
            row = await self.db.fetchone("SELECT state_data FROM global_event_state WHERE event_key = 'last_config_update'")
                
            if not row:
                return

            try:
                current_db_time = int(row[0])
            except (ValueError, TypeError):
                return
            
            # Initial run: just sync state
            if self.last_config_time == 0:
                self.last_config_time = current_db_time
                return
            
            # If changed, trigger reload
            if current_db_time > self.last_config_time:
                self.logger.info(f"Detected Config Change ({self.last_config_time} -> {current_db_time}). Reloading...")
                await self.reload_system()
                self.last_config_time = current_db_time
                
        except Exception as e:
            self.logger.error(f"Monitor error: {e}")

    async def reload_system(self):
        """Reload configuration and modules (non-blocking)."""
        async with self._reload_lock:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, importlib.reload, settings)
                self.logger.info("✓ Reloaded configs.settings")

                target_cogs = ['cogs.fishing.cog', 'cogs.shop']
                
                for cog_name in target_cogs:
                    try:
                        await self.bot.reload_extension(cog_name)
                        self.logger.info(f"✓ Reloaded {cog_name}")
                    except Exception as e:
                        self.logger.error(f"Failed to reload {cog_name}: {e}")
                
            except Exception as e:
                self.logger.error(f"Hot Reload Failed: {e}")

    @monitor_config_changes.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(SystemMonitor(bot))
