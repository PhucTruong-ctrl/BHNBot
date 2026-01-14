__all__ = ["SeasonalEventsCog", "setup"]


def setup(bot):
    from .cog import setup as _setup
    return _setup(bot)


def __getattr__(name):
    if name == "SeasonalEventsCog":
        from .cog import SeasonalEventsCog
        return SeasonalEventsCog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
