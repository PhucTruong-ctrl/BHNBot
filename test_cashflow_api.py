import asyncio
import sys
import os
import json

# Add root to path
sys.path.append("/home/phuctruong/BHNBot")

from web.routers.stats import get_cashflow_stats

async def test():
    try:
        print("Testing get_cashflow_stats(days=30)...")
        data = await get_cashflow_stats(days=30)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
