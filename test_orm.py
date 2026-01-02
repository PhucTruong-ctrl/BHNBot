
import asyncio
from dotenv import load_dotenv
load_dotenv()

from core.orm import init_tortoise
from cogs.aquarium.models import UserAquarium, HomeSlot
from tortoise import Tortoise

async def main():
    print("Testing ORM Init...")
    await init_tortoise()
    
    print("Creating User...")
    user, _ = await UserAquarium.get_or_create(user_id=8888, defaults={'leaf_coin': 100})
    print(f"User: {user.user_id}, Leaf: {user.leaf_coin}, Thread: {user.home_thread_id}")
    
    print("Creating Slots...")
    slot, _ = await HomeSlot.get_or_create(user=user, slot_index=0)
    print(f"Slot 0: {slot.item_id}")
    
    print("Closing...")
    await Tortoise.close_connections()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
