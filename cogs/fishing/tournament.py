from core.logging import get_logger
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from core.database import db_manager, add_seeds
import discord

logger = get_logger("fishing_tournament")

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

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
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
                entries = await db_manager.fetchall("SELECT user_id FROM tournament_entries WHERE tournament_id = $1", (t_id,))
                for (uid,) in entries:
                    self.active_participants[uid] = t_id
                    count += 1
            
            logger.info(f"[TOURNAMENT] Restored {count} active participants from {len(active_tourneys)} tournaments.")
        except Exception as e:
            logger.error(f"[TOURNAMENT] Restore error: {e}")

    async def create_tournament(self, host_id: int, entry_fee: int, channel_id: int) -> Optional[int]:
        """Creates a new tournament lobby."""
        try:
            # Check if host already has active/pending tournament
            existing = await db_manager.fetchone(
                "SELECT id FROM vip_tournaments WHERE host_id = $1 AND status IN ('pending', 'active')",
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
                current_bal = (await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", (host_id,)))['seeds']
                if current_bal < entry_fee:
                    return -1 # Insufficient funds
                
                await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", (entry_fee, host_id))
                await conn.execute("INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, 'tournament_create', 'fishing', CURRENT_TIMESTAMP)", (host_id, -entry_fee))

                # 2. Create Tournament
                # POSTGRES COMPATIBILITY: Use RETURNING id
                row = await conn.fetchrow(
                    "INSERT INTO vip_tournaments (host_id, entry_fee, prize_pool, status, channel_id) VALUES ($1, $2, $3, 'pending', $4) RETURNING id",
                    (host_id, entry_fee, entry_fee, channel_id)
                )
                tournament_id = row['id']
                
                # 3. Add Host Entry
                await conn.execute(
                    "INSERT INTO tournament_entries (tournament_id, user_id) VALUES ($1, $2)",
                    (tournament_id, host_id)
                )
                
            return tournament_id
            
        except Exception as e:
            logger.error(f"[TOURNAMENT] Create error: {e}")
            return None

    async def join_tournament(self, tournament_id: int, user_id: int) -> Tuple[bool, str]:
        """User joins a pending tournament."""
        try:
            # 1. Fetch Entry Fee & Status
            tourney = await db_manager.fetchrow("SELECT status, entry_fee FROM vip_tournaments WHERE id = $1", (tournament_id,))
            if not tourney or tourney['status'] != 'pending':
                return False, "Giải đấu không tồn tại hoặc đã bị khóa."

            entry_fee = tourney['entry_fee']

            async with db_manager.transaction() as conn:
                 # 2. Check Exists
                 check = await conn.fetchrow("SELECT 1 FROM tournament_entries WHERE tournament_id = $1 AND user_id = $2", (tournament_id, user_id))
                 if check:
                     return False, "Bạn đã tham gia giải này rồi."

                 # 3. Check Balance
                 bal = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", (user_id,))
                 if not bal or bal['seeds'] < entry_fee:
                     return False, f"Không đủ Hạt (Cần {entry_fee:,} Hạt)."

                 # 4. Deduct Fee
                 await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", (entry_fee, user_id))
                 await conn.execute("INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, 'tournament_join', 'fishing', CURRENT_TIMESTAMP)", (user_id, -entry_fee))

                 # 5. Add Entry
                 await conn.execute("INSERT INTO tournament_entries (tournament_id, user_id) VALUES ($1, $2)", (tournament_id, user_id))

                 # 6. Update Prize Pool
                 await conn.execute("UPDATE vip_tournaments SET prize_pool = prize_pool + $1 WHERE id = $2", (entry_fee, tournament_id))

            # 7. Update Cache
            self.active_participants[user_id] = tournament_id
            return True, "Tham gia thành công!"

        except Exception as e:
            logger.error(f"[TOURNAMENT] Join error: {e}")
            return False, "Lỗi hệ thống."

    async def get_user_tournament(self, user_id: int) -> Optional[int]:
        """Retrieves active tournament ID for user, with DB fallback (Self-Healing)."""
        if user_id in self.active_participants:
            return self.active_participants[user_id]
            
        # Fallback: Check DB
        try:
            row = await db_manager.fetchrow(
                """
                SELECT te.tournament_id 
                FROM tournament_entries te
                JOIN vip_tournaments vt ON te.tournament_id = vt.id
                WHERE te.user_id = ? AND vt.status = 'active'
                """,
                (user_id,)
            )
            if row:
                t_id = row['tournament_id']
                self.active_participants[user_id] = t_id
                logger.info(f"[TOURNAMENT] [SELF_HEAL] Restored user {user_id} to tournament {t_id}")
                return t_id
        except Exception as e:
            logger.error(f"[TOURNAMENT] Get user tournament error: {e}")
            
        return None

    async def update_score(self, user_id: int, points: int):
        """Updates score for a participant if they are in an active tournament."""
        tournament_id = await self.get_user_tournament(user_id)
        if not tournament_id:
            return

        try:
            # Atomic Update
            await db_manager.execute(
                "UPDATE tournament_entries SET score = score + $1 WHERE tournament_id = $2 AND user_id = $3",
                (points, tournament_id, user_id)
            )
            logger.info(f"[TOURNAMENT] Updated score for {user_id}: +{points}")
        except Exception as e:
            logger.error(f"[TOURNAMENT] Score update failed: {e}")

    async def cancel_tournament(self, tournament_id: int, reason: str = "Host cancelled"):
        """Refunds everyone and marks cancelled."""
        try:
            # Get all entries
            entries = await db_manager.fetchall("SELECT user_id FROM tournament_entries WHERE tournament_id = $1", (tournament_id,))
            tourney = await db_manager.fetchrow("SELECT entry_fee, status FROM vip_tournaments WHERE id = $1", (tournament_id,))
            
            if not tourney or tourney['status'] != 'pending':
                return
            
            fee = tourney['entry_fee']
            
            async with db_manager.transaction() as conn:
                await conn.execute("UPDATE vip_tournaments SET status = 'cancelled' WHERE id = $1", (tournament_id,))
                
                # Batch refund - avoid N+1
                refund_data = [(fee, row[0]) for row in entries]
                log_data = [(row[0], fee) for row in entries]
                
                await conn.executemany(
                    "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                    refund_data
                )
                await conn.executemany(
                    "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, 'tournament_refund', 'fishing', CURRENT_TIMESTAMP)",
                    log_data
                )
                    
            logger.info(f"[TOURNAMENT] Cancelled {tournament_id}. Refunded {len(entries)} users.")
            return True
        except Exception as e:
            logger.error(f"[TOURNAMENT] Cancel error: {e}")
            return False

    async def start_tournament(self, tournament_id: int) -> bool:
        """Starts the game."""
        try:
            # Check player count
            count_data = await db_manager.fetchrow("SELECT COUNT(*) as c FROM tournament_entries WHERE tournament_id = $1", (tournament_id,))
            if count_data['c'] < 2:
                return False # Need min 2 players
                
            # Update Status & Time
            # SQLite datetime functions: datetime('now') -> UTC string 'YYYY-MM-DD HH:MM:SS'
            # We add minutes for end_time
            start_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.utcnow() + timedelta(minutes=self.game_duration_minutes)
            end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            await db_manager.execute(
                "UPDATE vip_tournaments SET status = 'active', start_time = $1, end_time = $2 WHERE id = $3",
                (start_str, end_str, tournament_id)
            )
            
            # Cache active players
            entries = await db_manager.fetchall("SELECT user_id FROM tournament_entries WHERE tournament_id = $1", (tournament_id,))
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

    def set_bot(self, bot):
        self.bot = bot

    async def distribute_prizes(self, tournament_id: int):
        """Ends game and distributes prizes."""
        try:
            tourney = await db_manager.fetchrow("SELECT status, prize_pool, channel_id FROM vip_tournaments WHERE id = $1", (tournament_id,))
            if not tourney or tourney['status'] != 'active':
                return # Already ended?

            # Calculate Ranking (Score = Fish Value)
            ranks = await db_manager.fetchall(
                "SELECT user_id, score FROM tournament_entries WHERE tournament_id = $1 ORDER BY score DESC",
                (tournament_id,)
            )
            
            total_players = len(ranks)
            pool = tourney['prize_pool']
            channel_id = tourney['channel_id']
            
            payouts = {}
            # Logic: <4: 100%, 4-9: 70/30, 10+: 60/30/10
            if total_players < 4:
                # Winner takes all (if valid)
                if ranks:
                    payouts[ranks[0][0]] = pool
            elif total_players < 10:
                # Top 2: 70% - 30%
                payouts[ranks[0][0]] = int(pool * 0.7)
                payouts[ranks[1][0]] = int(pool * 0.3)
            else:
                # Top 3
                payouts[ranks[0][0]] = int(pool * 0.6)
                payouts[ranks[1][0]] = int(pool * 0.3)
                payouts[ranks[2][0]] = int(pool * 0.1)
            
            async with db_manager.transaction() as conn:
                await conn.execute("UPDATE vip_tournaments SET status = 'ended' WHERE id = $1", (tournament_id,))
                
                # Batch payouts - avoid N+1
                payout_data = [(amount, uid) for uid, amount in payouts.items()]
                log_data = [(uid, amount) for uid, amount in payouts.items()]
                
                await conn.executemany(
                    "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                    payout_data
                )
                await conn.executemany(
                    "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, 'tournament_win', 'fishing', CURRENT_TIMESTAMP)",
                    log_data
                )
                
            # Clear Cache
            for uid, _ in ranks:
                if uid in self.active_participants:
                    del self.active_participants[uid]
                    
            logger.info(f"[TOURNAMENT] Ended {tournament_id}. Payouts: {payouts}")

            # ANNOUNCEMENT
            if hasattr(self, 'bot') and self.bot and channel_id:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        embed = discord.Embed(title=f"🏁 GIẢI ĐẤU ĐÃ KẾT THÚC (ID: {tournament_id})", color=discord.Color.gold())
                        desc = f"💰 **Tổng Giải Thưởng:** {pool:,} Hạt\n\n"
                        pass
                        
                        # Formatting Ranks
                        for i, (uid, score) in enumerate(ranks, 1):
                            if i > 5: break # Show top 5
                            medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"
                            prize = f" (+{payouts.get(uid, 0):,} Hạt)" if uid in payouts else ""
                            desc += f"{medal} <@{uid}>: **{score:,}** điểm{prize}\n"
                            
                        embed.description = desc
                        await channel.send(embed=embed)
                except Exception as e:
                     logger.error(f"[TOURNAMENT] Announcement error: {e}")
            
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
                    "UPDATE tournament_entries SET score = score + $1 WHERE tournament_id = $2 AND user_id = $3",
                    (fish_value, tournament_id, user_id)
                )
            else:
                await db_manager.execute(
                    "UPDATE tournament_entries SET score = score + $1 WHERE tournament_id = $2 AND user_id = $3",
                    (fish_value, tournament_id, user_id)
                )
        except Exception as e:
            logger.error(f"[TOURNAMENT] Score update error: {e}")

    async def check_active_timeouts(self):
        """Checks for active tournaments that should have ended."""
        try:
            # Check Active Games
            # Fetch ALL active to avoid SQL string comparison issues with timezones
            active = await db_manager.fetchall("SELECT id, end_time FROM vip_tournaments WHERE status = 'active'")
            if not active:
                return

            from datetime import datetime, timezone
            from dateutil import parser
            
            now = datetime.now(timezone.utc)
            
            for row in active:
                t_id = "Unknown"
                try:
                    t_id = row['id']
                    end_str = row['end_time']
                    
                    # Robust Parsing
                    try:
                        end_dt = parser.parse(end_str)
                    except Exception:
                        # If parsing fails, skip or force end? Let's skip and log.
                        logger.error(f"[TOURNAMENT] Invalid time format for ID {t_id}: {end_str}")
                        continue
                        
                    # Normalize to UTC
                    if end_dt.tzinfo is None:
                        # Assume UTC if naive, or Local?
                        # Best to assume UTC if generated by us.
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                    else:
                        end_dt = end_dt.astimezone(timezone.utc)
                        
                    if now >= end_dt:
                        logger.info(f"[TOURNAMENT] Auto-ending expired tournament {t_id}")
                        await self.distribute_prizes(t_id)
                        
                except Exception as e:
                    logger.error(f"[TOURNAMENT] Error processing {t_id}: {e}")

        except Exception as e:
            logger.error(f"[TOURNAMENT] Active timeout check error: {e}")

    async def check_registration_timeouts(self):
        """Called periodically to cancel pending tournaments that timed out."""
        try:
            # Find pending tournaments older than 15 minutes
            # SQLite specific time calculation
            cutoff = (datetime.utcnow() - timedelta(minutes=self.registration_timeout_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            
            pending = await db_manager.fetchall(
                "SELECT id FROM vip_tournaments WHERE status = 'pending' AND created_at < $1",
                (cutoff,)
            )
            
            for row in pending:
                t_id = row[0]
                # Check player count
                count_data = await db_manager.fetchrow("SELECT COUNT(*) as c FROM tournament_entries WHERE tournament_id = $1", (t_id,))
                
                if count_data['c'] < 2:
                    await self.cancel_tournament(t_id, reason="Not enough players (Timeout)")
                else:
                    # Auto start if enough players
                    await self.start_tournament(t_id)

        except Exception as e:
            logger.error(f"[TOURNAMENT] Timeout check error: {e}")
