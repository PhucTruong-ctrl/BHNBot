"""Health monitoring cog for bot diagnostics.

Provides /healthcheck command for admins to monitor:
- Memory usage
- Active Views count (detect leaks)
- Background tasks
- Open files (resource leaks)
- Uptime
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import gc
import time
import datetime
import psutil
import os

from core.logging import setup_logger

logger = setup_logger("HealthCheck", "logs/cogs/health.log")


class HealthCheckCog(commands.Cog):
    """Admin-only health monitoring commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        logger.info("[HEALTH] HealthCheck cog loaded")
    
    @app_commands.command(name="healthcheck", description="🏥 Kiểm tra sức khỏe Bot (Admin Only)")
    @app_commands.default_permissions(administrator=True)
    async def health_check(self, interaction: discord.Interaction):
        """Display comprehensive bot health metrics."""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get process info
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            
            # Force garbage collection before counting
            gc.collect()
            
            # Count active Views
            all_objects = gc.get_objects()
            all_views = [obj for obj in all_objects if isinstance(obj, discord.ui.View)]
            
            # Count background tasks (exclude current task)
            current_task = asyncio.current_task()
            all_tasks = [t for t in asyncio.all_tasks() if not t.done() and t is not current_task]
            
            # Open files (Linux only)
            try:
                open_files = len(process.open_files())
            except (AttributeError, psutil.AccessDenied):
                open_files = "N/A"
            
            # CPU usage
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # Uptime
            uptime_seconds = time.time() - self.start_time
            uptime_str = str(datetime.timedelta(seconds=int(uptime_seconds)))
            
            # Latency (handle NaN/inf case)
            latency_ms = self.bot.latency * 1000 if self.bot.latency not in (float('inf'), float('nan')) else 0
            
            # View breakdown by cog
            view_counts = {}
            for v in all_views:
                try:
                    module = type(v).__module__
                    if '.' in module:
                        cog_name = module.split('.')[1]
                    else:
                        cog_name = 'core'
                    view_counts[cog_name] = view_counts.get(cog_name, 0) + 1
                except Exception:
                    view_counts['unknown'] = view_counts.get('unknown', 0) + 1
            
            # Build embed
            embed = discord.Embed(
                title="🏥 Bot Health Report",
                description=f"📊 Monitoring data collected at <t:{int(time.time())}:T>",
                color=discord.Color.green()
            )
            
            # System metrics
            embed.add_field(
                name="💾 Memory Usage",
                value=f"{mem_mb:.1f} MB",
                inline=True
            )
            embed.add_field(
                name="🖥️ CPU Usage",
                value=f"{cpu_percent:.1f}%",
                inline=True
            )
            embed.add_field(
                name="⏱️ Uptime",
                value=uptime_str,
                inline=True
            )
            
            # Discord metrics
            embed.add_field(
                name="📡 Latency",
                value=f"{latency_ms:.0f}ms",
                inline=True
            )
            embed.add_field(
                name="🌐 Servers",
                value=str(len(self.bot.guilds)),
                inline=True
            )
            embed.add_field(
                name="👥 Users",
                value=str(len(self.bot.users)),
                inline=True
            )
            
            # Resource leak indicators
            embed.add_field(
                name="👀 Active Views",
                value=f"**{len(all_views)}** views",
                inline=True
            )
            embed.add_field(
                name="⚙️ Background Tasks",
                value=f"**{len(all_tasks)}** tasks",
                inline=True
            )
            embed.add_field(
                name="📁 Open Files",
                value=str(open_files),
                inline=True
            )
            
            # View breakdown (if any)
            if view_counts:
                breakdown = "\n".join(
                    f"• **{k}**: {v}" 
                    for k, v in sorted(view_counts.items(), key=lambda x: -x[1])[:10]
                )
                embed.add_field(
                    name="📦 Views by Cog (Top 10)",
                    value=breakdown,
                    inline=False
                )
            
            # Health warnings
            warnings = []
            if len(all_views) > 50:
                warnings.append("⚠️ **High View count!** Potential memory leak.")
            if mem_mb > 200:
                warnings.append("⚠️ **High memory usage!** Check for leaks.")
            if len(all_tasks) > 100:
                warnings.append("⚠️ **Too many background tasks!**")
            if cpu_percent > 50:
                warnings.append("⚠️ **High CPU usage!**")
            
            if warnings:
                embed.add_field(
                    name="🚨 Health Warnings",
                    value="\n".join(warnings),
                    inline=False
                )
                embed.color = discord.Color.orange()
            
            # Footer with recommendation
            embed.set_footer(
                text="💡 Run this command periodically to monitor trends | "
                     "Baseline: ~30-50 views, <100MB memory"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(
                f"[HEALTH] Check run by {interaction.user.name}: "
                f"{len(all_views)} views, {mem_mb:.1f}MB, {len(all_tasks)} tasks"
            )
            
        except Exception as e:
            logger.error(f"[HEALTH] Error in healthcheck: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Lỗi khi kiểm tra sức khỏe: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Load the HealthCheck cog."""
    await bot.add_cog(HealthCheckCog(bot))
