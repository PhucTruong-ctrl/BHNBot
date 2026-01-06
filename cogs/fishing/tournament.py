import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from core.database import db_manager, add_seeds
import discord

logger = logging.getLogger("TournamentManager")

class TournamentManager:
    """
    Manages User-Hosted Fishing Tournaments.
    Singleton Pattern.
    """
    _instance = None
    
    def __init__(self):
        # Cache for active tournament IDs to reduce DB hits on every catch
        # Format: {user_id: tournament_id}
        self.active_participants: Dict[int, int] = {}
        self.game_duration_minutes = 10
        self.registration_timeout_minutes = 15

        return cls._instance

    async def restore_active_tournaments(self):
        """Restores active participants from DB after bot restart."""
        try:
            # Get active IDs
            active_tourneys = await db_manager.fetchall("SELECT id FROM vip_tournaments WHERE status = 'active'")
            if not active_tourneys:
                return
                
            count = 0
            for (t_id,) in active_tourneys:
                entries = await db_manager.fetchall("SELECT user_id FROM tournament_entries WHERE tournament_id = ?", (t_id,))
                for (uid,) in entries:
                    self.active_participants[uid] = t_id
                    count += 1
            
            logger.info(f"[TOURNAMENT] Restored {count} active participants from {len(active_tourneys)} tournaments.")
        except Exception as e:
            logger.error(f"[TOURNAMENT] Restore error: {e}")

    async def create_tournament(self, host_id: int, entry_fee: int) -> Optional[int]:
        """Creates a new tournament lobby."""
        try:
            # Check if host already has active/pending tournament
            existing = await db_manager.fetchone(
                "SELECT id FROM vip_tournaments WHERE host_id = ? AND status IN ('pending', 'active')",
                (host_id,)
            )
            if existing:
                return None # Already hosting
            
            # Deduct fee from host (Host pays their own entry fee upfront?) 
            # Design: Host pays entry fee upon creation or upon start?
            # User request: "/giaidau create 5000" -> This sets the fee for others.
            # Does host join automatically? "create" usually implies joining.
            # Let's assume Host joins automatically and pays the fee.
            
            # Use transaction
            async with db_manager.transaction() as conn:
                # 1. Deduct seed from host
                # We reuse logic from market/others, or raw SQL.
                # Assuming host must buy-in.
                current_bal = (await conn.fetchrow("SELECT seeds FROM users WHERE user_id = ?", (host_id,)))['seeds']
                if current_bal < entry_fee:
                    return -1 # Insufficient funds
                
                await conn.execute("UPDATE users SET seeds = seeds - ? WHERE user_id = ?", (entry_fee, host_id))
                await conn.execute("INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES (?, ?, 'tournament_create', 'fishing', CURRENT_TIMESTAMP)", (host_id, -entry_fee))

                # 2. Create Tournament
                # POSTGRES COMPATIBILITY: Use RETURNING id
                row = await conn.fetchrow(
                    "INSERT INTO vip_tournaments (host_id, entry_fee, prize_pool, status) VALUES (?, ?, ?, 'pending') RETURNING id",
                    (host_id, entry_fee, entry_fee)
                )
                tournament_id = row['id']
                
                # 3. Add Host Entry
                await conn.execute(
                    "INSERT INTO tournament_entries (tournament_id, user_id) VALUES (?, ?)",
                    (tournament_id, host_id)
                )
                
            return tournament_id
            
        except Exception as e:
            logger.error(f"[TOURNAMENT] Create error: {e}")
            return None

    async def join_tournament(self, tournament_id: int, user_id: int) -> Tuple[bool, str]:
        """User joins a pending tournament."""
        try:
            txn = await db_manager.fetchrow("SELECT status, entry_fee FROM vip_tournaments WHERE id = ?", (tournament_id,))
            if not txn or txn['status'] != 'pending':
                return False, "Giải đấu không còn nhận đăng ký."
            
            # Check if user already joined
            exists = await db_manager.fetchone("SELECT 1 FROM tournament_entries WHERE tournament_id = ? AND user_id = ?", (tournament_id, user_id))
            if exists:
                return False, "Bạn đã tham gia rồi."

            entry_fee = txn['entry_fee']
            
            async with db_manager.transaction() as conn:
                # Deduct Fee
                row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
                if not row or row['seeds'] < entry_fee:
                    return False, f"Không đủ Hạt (Cần {entry_fee:,})."
                    
                await conn.execute("UPDATE users SET seeds = seeds - ? WHERE user_id = ?", (entry_fee, user_id))
                await conn.execute("INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES (?, ?, 'tournament_join', 'fishing', CURRENT_TIMESTAMP)", (user_id, -entry_fee))
                
                # Add Entry
                await conn.execute("INSERT INTO tournament_entries (tournament_id, user_id) VALUES (?, ?)", (tournament_id, user_id))
                
                # Update Prize Pool
                await conn.execute("UPDATE vip_tournaments SET prize_pool = prize_pool + ? WHERE id = ?", (entry_fee, tournament_id))
                
            return True, "Tham gia thành công!"
        except Exception as e:
            logger.error(f"[TOURNAMENT] Join error: {e}")
            return False, "Lỗi hệ thống."

    async def cancel_tournament(self, tournament_id: int, reason: str = "Host cancelled"):
        """Refunds everyone and marks cancelled."""
        try:
            # Get all entries
            entries = await db_manager.fetchall("SELECT user_id FROM tournament_entries WHERE tournament_id = ?", (tournament_id,))
            tourney = await db_manager.fetchrow("SELECT entry_fee, status FROM vip_tournaments WHERE id = ?", (tournament_id,))
            
            if not tourney or tourney['status'] != 'pending':
                return
            
            fee = tourney['entry_fee']
            
            async with db_manager.transaction() as conn:
                await conn.execute("UPDATE vip_tournaments SET status = 'cancelled' WHERE id = ?", (tournament_id,))
                
                for row in entries:
                    uid = row[0]
                    await conn.execute("UPDATE users SET seeds = seeds + ? WHERE user_id = ?", (fee, uid))
                    await conn.execute("INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES (?, ?, 'tournament_refund', 'fishing', CURRENT_TIMESTAMP)", (uid, fee))
                    
            logger.info(f"[TOURNAMENT] Cancelled {tournament_id}. Refunded {len(entries)} users.")
            return True
        except Exception as e:
            logger.error(f"[TOURNAMENT] Cancel error: {e}")
            return False

    async def start_tournament(self, tournament_id: int) -> bool:
        """Starts the game."""
        try:
            # Check player count
            count_data = await db_manager.fetchrow("SELECT COUNT(*) as c FROM tournament_entries WHERE tournament_id = ?", (tournament_id,))
            if count_data['c'] < 2:
                return False # Need min 2 players
                
            # Update Status & Time
            # SQLite datetime functions: datetime('now') -> UTC string 'YYYY-MM-DD HH:MM:SS'
            # We add minutes for end_time
            start_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.utcnow() + timedelta(minutes=self.game_duration_minutes)
            end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            await db_manager.execute(
                "UPDATE vip_tournaments SET status = 'active', start_time = ?, end_time = ? WHERE id = ?",
                (start_str, end_str, tournament_id)
            )
            
            # Cache active players
            entries = await db_manager.fetchall("SELECT user_id FROM tournament_entries WHERE tournament_id = ?", (tournament_id,))
            for row in entries:
                self.active_participants[row[0]] = tournament_id
                
            # Schedule End Task (Async sleep? or separate scheduled task?)
            # Since bot might restart, we should also separate scheduled task in loop, but async sleep is fine for short duration (10 mins).
            # But reliability... let's rely on the global loop to check 'active' tournaments that passed 'end_time'.
            # However for immediate UX, we can spawn a task.
            asyncio.create_task(self.end_game_delayed(tournament_id, self.game_duration_minutes * 60))
            
            return True
        except Exception as e:
            logger.error(f"[TOURNAMENT] Start error: {e}")
            return False

    async def end_game_delayed(self, tournament_id: int, delay_seconds: int):
        await asyncio.sleep(delay_seconds)
        await self.distribute_prizes(tournament_id)

    async def distribute_prizes(self, tournament_id: int):
        """Ends game and distributes prizes."""
        try:
            tourney = await db_manager.fetchrow("SELECT status, prize_pool FROM vip_tournaments WHERE id = ?", (tournament_id,))
            if not tourney or tourney['status'] != 'active':
                return # Already ended?

            # Calculate Ranking (Score = Fish Value)
            ranks = await db_manager.fetchall(
                "SELECT user_id, score FROM tournament_entries WHERE tournament_id = ? ORDER BY score DESC",
                (tournament_id,)
            )
            
            total_players = len(ranks)
            pool = tourney['prize_pool']
            
            payouts = {}
            # Logic: <4: 100%, 4-9: 70/30, 10+: 60/30/10
            if total_players < 4:
                # Rank 1 takes all
                if ranks:
                    payouts[ranks[0][0]] = pool
            elif total_players < 10:
                # Rank 1: 70%, Rank 2: 30%
                payouts[ranks[0][0]] = int(pool * 0.7)
                if len(ranks) > 1:
                    payouts[ranks[1][0]] = int(pool * 0.3)
            else:
                # Rank 1: 60%, Rank 2: 30%, Rank 3: 10%
                payouts[ranks[0][0]] = int(pool * 0.6)
                if len(ranks) > 1:
                    payouts[ranks[1][0]] = int(pool * 0.3)
                if len(ranks) > 2:
                    payouts[ranks[2][0]] = int(pool * 0.1)
            
            async with db_manager.transaction() as conn:
                await conn.execute("UPDATE vip_tournaments SET status = 'ended' WHERE id = ?", (tournament_id,))
                
                # Distribute
                for uid, amount in payouts.items():
                    await conn.execute("UPDATE users SET seeds = seeds + ? WHERE user_id = ?", (amount, uid))
                    await conn.execute("INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES (?, ?, 'tournament_win', 'fishing', CURRENT_TIMESTAMP)", (uid, amount))
                
            # Clear Cache
            for uid, _ in ranks:
                if uid in self.active_participants:
                    del self.active_participants[uid]
                    
            logger.info(f"[TOURNAMENT] Ended {tournament_id}. Payouts: {payouts}")
            
        except Exception as e:
            logger.error(f"[TOURNAMENT] End error: {e}")

    async def on_fish_catch(self, user_id: int, fish_value: int, conn=None):
        """Called by Fishing System when a fish is caught.
        
        Args:
            user_id: User who caught fish
            fish_value: Base sell value of fish
            conn: Optional database connection (from outer transaction)
        """
        if user_id not in self.active_participants:
            return
            
        tournament_id = self.active_participants[user_id]
        
        # Verify tournament is actually still active (double check)
        # Or trust the cache management. 
        # Update Score
        try:
            if conn:
                await conn.execute(
                    "UPDATE tournament_entries SET score = score + ? WHERE tournament_id = ? AND user_id = ?",
                    (fish_value, tournament_id, user_id)
                )
            else:
                await db_manager.execute(
                    "UPDATE tournament_entries SET score = score + ? WHERE tournament_id = ? AND user_id = ?",
                    (fish_value, tournament_id, user_id)
                )
        except Exception as e:
            logger.error(f"[TOURNAMENT] Score update error: {e}")

    async def check_registration_timeouts(self):
        """Called periodically to cancel pending tournaments that timed out."""
        try:
            # Find pending tournaments older than 15 minutes
            # SQLite specific time calculation
            cutoff = (datetime.utcnow() - timedelta(minutes=self.registration_timeout_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            
            pending = await db_manager.fetchall(
                "SELECT id FROM vip_tournaments WHERE status = 'pending' AND created_at < ?",
                (cutoff,)
            )
            
            for row in pending:
                t_id = row[0]
                # Check player count
                count_data = await db_manager.fetchrow("SELECT COUNT(*) as c FROM tournament_entries WHERE tournament_id = ?", (t_id,))
                
                if count_data['c'] < 2:
                    await self.cancel_tournament(t_id, reason="Not enough players (Timeout)")
                else:
                    # Auto start if enough players
                    await self.start_tournament(t_id)

        except Exception as e:
            logger.error(f"[TOURNAMENT] Timeout check error: {e}")
