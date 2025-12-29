import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add current dir to path
sys.path.append(os.getcwd())

# Mock bot for Cog init if needed (though we only check module imports)
mock_bot = MagicMock()

async def verify_imports():
    errors = []
    
    modules = [
        "cogs.shop",
        "cogs.consumable",
        "cogs.fishing.cog",
        "cogs.relationship.cog",
        "cogs.tree.cog"
    ]
    
    for mod in modules:
        try:
            __import__(mod)
            print(f"✅ Imported {mod}")
        except Exception as e:
            print(f"❌ Failed to import {mod}: {e}")
            errors.append(f"{mod}: {e}")

    if errors:
        sys.exit(1)
    else:
        print("All imports successful.")

if __name__ == "__main__":
    asyncio.run(verify_imports())
