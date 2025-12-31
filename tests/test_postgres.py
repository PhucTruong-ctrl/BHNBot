import asyncio
import logging
import random
import time
from core.database import db_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestPostgres")

async def worker(worker_id):
    """Simulate a worker performing DB operations."""
    for i in range(10):
        # Transaction usage
        async with db_manager.transaction() as conn:
            # Insert log
            await conn.execute(
                "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, $3, $4, NOW())",
                worker_id, i, f"test_worker_{worker_id}", "test"
            )
            
            # Read back
            row = await conn.fetchrow("SELECT COUNT(*) FROM transaction_logs")
            count = row[0]
            
        # logger.info(f"Worker {worker_id} iter {i} done. Count: {count}")

async def main():
    logger.info("Starting Postgres Concurrency Test...")
    start_time = time.time()
    
    # Init Check
    await db_manager.connect()
    ver = await db_manager.fetchone("SELECT version();")
    logger.info(f"Connected to: {ver[0]}")
    
    # Create Workers
    tasks = []
    for i in range(50):
        tasks.append(worker(i))
        
    # Run Concurrently
    await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    logger.info(f"Finished 50 workers x 10 txns in {duration:.2f}s")
    
    # Verify Total
    row = await db_manager.fetchone("SELECT COUNT(*) FROM transaction_logs WHERE category='test'")
    logger.info(f"Total Test Rows: {row[0]}")
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
