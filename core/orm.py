from tortoise import Tortoise
import os
import logging

logger = logging.getLogger("Tortoise")

TORTOISE_ORM = {
    "connections": {
        "default": os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
    },
    "apps": {
        "models": {
            "models": ["cogs.aquarium.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}

async def init_tortoise():
    """Initialize Tortoise ORM connection"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment!")
        return

    logger.info(f"Connecting to database via Tortoise...")
    try:
        await Tortoise.init(
            db_url=db_url,
            modules={'models': ['cogs.aquarium.models']}
        )
        logger.info("Tortoise ORM connected successfully.")
        
        # Safe schema generation for development
        # In production, use aerich
        logger.info("Generating schemas...")
        await Tortoise.generate_schemas()
        logger.info("Schemas generated.")
        
    except Exception as e:
        logger.error(f"Failed to init Tortoise: {e}", exc_info=True)

async def close_tortoise():
    """Close Tortoise ORM connection"""
    await Tortoise.close_connections()
    logger.info("Tortoise ORM disconnected.")
