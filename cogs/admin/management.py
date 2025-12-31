import discord
from discord import app_commands
from discord.ext import commands
import os

from core.logger import setup_logger

logger = setup_logger("AdminCog", "cogs/admin.log")

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Sync Commands ---
    @app_commands.command(name="sync", description="Sync slash commands (Owner Only)")
    @app_commands.describe(
        scope="'guild' = current server only, 'global' = all servers (default: guild)"
    )
    async def sync(self, interaction: discord.Interaction, scope: str = "guild"):
        """Sync all slash commands to specified scope"""
        if interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("Ko có quyền", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        try:
            scope = scope.lower()
            
            # List all commands in bot.tree
            all_commands = self.bot.tree.get_commands()
            cmd_list = "\n".join([f"  - {cmd.name}" for cmd in all_commands])
            logger.info(f"\n[SYNC DEBUG] Tất cả commands trong bot.tree ({len(all_commands)}):\n{cmd_list}\n")
            
            if scope == "guild":
                # Sync to current guild only (for testing)
                synced = await self.bot.tree.sync(guild=interaction.guild)
                synced_list = "\n".join([f"  - {cmd.name}" for cmd in synced])
                msg = f"Synced {len(synced)} commands to **{interaction.guild.name}**\n\n"
                msg += f"```\n{synced_list if synced_list else '(No commands)'}\n```\n\n"
                msg += "**Restart Discord (Ctrl+R) to see changes!**"
                logger.info(f"[SYNC Guild] Guild {interaction.guild.id} ({interaction.guild.name}): {len(synced)} commands synced")
                logger.info(f"[SYNC Guild] Synced commands:\n{synced_list if synced_list else '(No commands)'}\n")
                
            elif scope == "global":
                # Sync globally
                synced = await self.bot.tree.sync()
                synced_list = "\n".join([f"  - {cmd.name}" for cmd in synced])
                msg = f"Synced {len(synced)} commands **GLOBALLY** to all servers\n\n"
                msg += f"```\n{synced_list if synced_list else '(No commands)'}\n```\n\n"
                msg += "**Restart Discord (Ctrl+R) to see changes!**"
                logger.info(f"[SYNC Global] Synced {len(synced)} commands globally")
                logger.info(f"[SYNC Global] Synced commands:\n{synced_list if synced_list else '(No commands)'}\n")
                
            else:
                msg = "Scope phải là 'guild' hoặc 'global'"
            
            await interaction.followup.send(msg)
            
        except Exception as e:
            error_msg = f"Lỗi sync: {str(e)}"
            await interaction.followup.send(error_msg)
            logger.error(f"[SYNC ERROR] {e}", exc_info=True)

    # --- Sync Prefix Command ---
    @commands.command(name="sync", description="Sync slash commands (Owner Only)")
    @commands.is_owner()
    async def sync_prefix(self, ctx, scope: str = "guild"):
        """Sync all slash commands via prefix command"""
        try:
            scope = scope.lower()
            
            # List all commands in bot.tree
            all_commands = self.bot.tree.get_commands()
            cmd_list = "\n".join([f"  - {cmd.name}" for cmd in all_commands])
            logger.info(f"\n[!SYNC DEBUG] Tất cả commands trong bot.tree ({len(all_commands)}):\n{cmd_list}\n")
            
            if scope == "guild":
                # Sync to current guild only (for testing)
                synced = await self.bot.tree.sync(guild=ctx.guild)
                synced_list = "\n".join([f"  - {cmd.name}" for cmd in synced])
                msg = f"Synced {len(synced)} commands to **{ctx.guild.name}**\n\n"
                msg += f"```\n{synced_list if synced_list else '(No commands)'}\n```\n\n"
                msg += "**Restart Discord (Ctrl+R) to see changes!**"
                logger.info(f"[!SYNC Guild] Guild {ctx.guild.id} ({ctx.guild.name}): {len(synced)} commands synced")
                logger.info(f"[!SYNC Guild] Synced commands:\n{synced_list if synced_list else '(No commands)'}\n")
                
            elif scope == "global":
                # Sync globally
                synced = await self.bot.tree.sync()
                synced_list = "\n".join([f"  - {cmd.name}" for cmd in synced])
                msg = f"Synced {len(synced)} commands **GLOBALLY** to all servers\n\n"
                msg += f"```\n{synced_list if synced_list else '(No commands)'}\n```\n\n"
                msg += "**Restart Discord (Ctrl+R) to see changes!**"
                logger.info(f"[!SYNC Global] Synced {len(synced)} commands globally")
                logger.info(f"[!SYNC Global] Synced commands:\n{synced_list if synced_list else '(No commands)'}\n")
                
            else:
                msg = "Scope phải là 'guild' hoặc 'global'"
            
            await ctx.send(msg)
            
        except Exception as e:
            error_msg = f"Lỗi sync: {str(e)}"
            await ctx.send(error_msg)
            logger.error(f"[!SYNC ERROR] {e}", exc_info=True)

    # --- Cogs Manager ---
    @commands.group(name="cog", description="Manage cogs", invoke_without_command=True)
    @commands.is_owner()
    async def manage_cog(self, ctx):
        """Cog management commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Dùng: !cog load/reload/unload <name>")

    @manage_cog.command(name="load", description="Load a cog")
    async def load_cog(self, ctx, cog_name: str):
        """Load a cog file (supports sub-directory cogs like fishing.cog, werewolf.cog)"""
        try:
            # Check if it's a sub-directory cog (e.g., fishing, werewolf)
            import os
            cogs_dir = './cogs'
            subdir_path = os.path.join(cogs_dir, cog_name)
            
            # If it's a directory with cog.py, load as sub-cog
            if os.path.isdir(subdir_path) and os.path.exists(os.path.join(subdir_path, 'cog.py')):
                await self.bot.load_extension(f"cogs.{cog_name}.cog")
                await ctx.send(f"Loaded: cogs.{cog_name}.cog")
                logger.info(f"COG_LOAD: cogs.{cog_name}.cog")
            else:
                # Load as top-level cog
                await self.bot.load_extension(f"cogs.{cog_name}")
                await ctx.send(f"Loaded: {cog_name}")
                logger.info(f"COG_LOAD: {cog_name}")
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f"{cog_name} already loaded")
        except commands.ExtensionNotFound:
            await ctx.send(f"{cog_name} not found")
        except Exception as e:
            await ctx.send(f"Lỗi: {str(e)}")
            logger.error(f"COG_ERROR [{cog_name}]: {e}")

    @manage_cog.command(name="unload", description="Unload a cog")
    async def unload_cog(self, ctx, cog_name: str):
        """Unload a cog file (supports sub-directory cogs like fishing.cog, werewolf.cog)"""
        try:
            # Check if it's a sub-directory cog (e.g., fishing, werewolf)
            import os
            cogs_dir = './cogs'
            subdir_path = os.path.join(cogs_dir, cog_name)
            
            # If it's a directory with cog.py, unload as sub-cog
            if os.path.isdir(subdir_path) and os.path.exists(os.path.join(subdir_path, 'cog.py')):
                await self.bot.unload_extension(f"cogs.{cog_name}.cog")
                await ctx.send(f"Unloaded: cogs.{cog_name}.cog")
                logger.info(f"COG_UNLOAD: cogs.{cog_name}.cog")
            else:
                # Unload as top-level cog
                await self.bot.unload_extension(f"cogs.{cog_name}")
                await ctx.send(f"Unloaded: {cog_name}")
                logger.info(f"COG_UNLOAD: {cog_name}")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{cog_name} not loaded")
        except Exception as e:
            await ctx.send(f"Lỗi: {str(e)}")
            logger.error(f"COG_ERROR [{cog_name}]: {e}")

    @manage_cog.command(name="reload", description="Reload a cog")
    async def reload_cog(self, ctx, cog_name: str):
        """Reload a cog file (supports sub-directory cogs like fishing.cog, werewolf.cog)"""
        try:
            # Check if it's a sub-directory cog (e.g., fishing, werewolf)
            import os
            cogs_dir = './cogs'
            subdir_path = os.path.join(cogs_dir, cog_name)
            
            # If it's a directory with cog.py, reload as sub-cog
            if os.path.isdir(subdir_path) and os.path.exists(os.path.join(subdir_path, 'cog.py')):
                await self.bot.reload_extension(f"cogs.{cog_name}.cog")
                await ctx.send(f"Reloaded: cogs.{cog_name}.cog")
                logger.info(f"COG_RELOAD: cogs.{cog_name}.cog")
            else:
                # Reload as top-level cog
                await self.bot.reload_extension(f"cogs.{cog_name}")
                await ctx.send(f"Reloaded: {cog_name}")
                logger.info(f"COG_RELOAD: {cog_name}")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{cog_name} not loaded")
        except commands.ExtensionNotFound:
            await ctx.send(f"{cog_name} not found")
        except Exception as e:
            await ctx.send(f"Lỗi: {str(e)}")
            logger.error(f"COG_ERROR [{cog_name}]: {e}")

    @manage_cog.command(name="list", description="List all cogs")
    async def list_cogs(self, ctx):
        """List loaded cogs"""
        cogs = list(self.bot.cogs.keys())
        msg = "Loaded cogs:\n" + "\n".join([f"- {c}" for c in cogs])
        await ctx.send(msg)

    # --- Helper: List all commands ---
    @commands.command(name="commands", description="List all available commands")
    @commands.is_owner()
    async def list_all_commands(self, ctx):
        """List all slash and prefix commands"""
        msg = "**TẤT CẢ LỆNH HỢP LỆ**\n\n"
        
        # Slash commands
        msg += "**Slash Commands (/):**\n"
        all_slash = self.bot.tree.get_commands()
        if all_slash:
            for cmd in all_slash:
                msg += f"  - `/{cmd.name}` - {cmd.description or 'No description'}\n"
        else:
            msg += "  (Ko có)\n"
        
        msg += f"\n**Prefix Commands (!):**\n"
        for cmd in self.bot.commands:
            msg += f"  - `!{cmd.name}` - {cmd.description or 'No description'}\n"
        
        msg += f"\n**Total: {len(all_slash)} slash commands, {len(list(self.bot.commands))} prefix commands**"
        await ctx.send(msg)

    # --- Item System Commands ---
    @commands.command(name="reload_items", description="Reload items from JSON (Admin Only)")
    @commands.is_owner()
    async def reload_items(self, ctx):
        """Reload fishing items data from disk"""
        from core.item_system import item_system
        success = item_system.reload()
        
        if success:
            count = len(item_system.get_all_items())
            await ctx.send(f"✅ **Đã reload items thành công!** (Tổng: {count} items)\n\nDữ liệu mới đã được cập nhật vào hệ thống.")
            logger.info(f"ADMIN_ACTION: !reload_items by {ctx.author}")
        else:
            await ctx.send("❌ **Lỗi khi reload items!** Vui lòng kiểm tra log.")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
