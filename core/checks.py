import discord
from discord.ext import commands
from configs.settings import OWNER_ID, ADMIN_IDS

def is_owner():
    """Decorator to check if the user is the bot owner."""
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        raise commands.NotOwner("You do not own this bot.")
    return commands.check(predicate)

def is_admin():
    """Decorator to check if user is in ADMIN_IDS."""
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID or ctx.author.id in ADMIN_IDS:
            return True
        raise commands.MissingPermissions(["Bot Admin"])
    return commands.check(predicate)

def is_manager_or_higher():
    """Decorator for Manager role or higher (Admin/Owner)."""
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID or ctx.author.id in ADMIN_IDS:
            return True
        # Add logic for Manager role check here if needed in future
        # e.g. if discord.utils.get(ctx.author.roles, name="Manager"): return True
        return False
    return commands.check(predicate)

def bot_has_permissions(**perms):
    """Decorator to check if the bot has specific permissions in the channel."""
    return commands.bot_has_permissions(**perms)
