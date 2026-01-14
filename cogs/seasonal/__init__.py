__all__ = ["SeasonalEventsCog", "EventCommandsCog", "setup"]


async def setup(bot):
    from .cog import setup as cog_setup
    from .event_commands import setup as cmd_setup

    await cog_setup(bot)
    await cmd_setup(bot)


def __getattr__(name):
    if name == "SeasonalEventsCog":
        from .cog import SeasonalEventsCog
        return SeasonalEventsCog
    if name == "EventCommandsCog":
        from .event_commands import EventCommandsCog
        return EventCommandsCog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
