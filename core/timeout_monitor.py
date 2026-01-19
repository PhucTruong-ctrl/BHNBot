"""Timeout Monitor - Track and alert on Discord API timeouts.

Monitors network timeout errors and provides statistics for debugging.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Optional, Dict, Deque
from core.logging import setup_logger

logger = setup_logger("TimeoutMonitor", "logs/timeout_monitor.log")


class TimeoutMonitor:
    """Monitor and track timeout errors across the bot.
    
    Features:
    - Track timeout frequency per command/cog
    - Alert if timeout rate exceeds threshold
    - Provide stats for debugging
    """
    
    def __init__(self, alert_threshold: int = 5, time_window: int = 300):
        """Initialize timeout monitor.
        
        Args:
            alert_threshold: Number of timeouts to trigger alert
            time_window: Time window in seconds for counting (default 5 min)
        """
        self.alert_threshold = alert_threshold
        self.time_window = time_window
        
        # Track timeouts: {context: deque of timestamps}
        self.timeout_history: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=100))
        
        # Total counters
        self.total_timeouts = 0
        self.start_time = time.time()
    
    def record_timeout(
        self,
        context: str,
        user_id: Optional[int] = None,
        command: Optional[str] = None,
        duration: Optional[float] = None
    ) -> None:
        """Record a timeout event.
        
        Args:
            context: What was timing out (e.g., "channel.send", "interaction.response")
            user_id: User who triggered the command
            command: Command name if applicable
            duration: How long before timeout (seconds)
        """
        current_time = time.time()
        
        # Record to history
        self.timeout_history[context].append(current_time)
        self.total_timeouts += 1
        
        # Log event
        log_msg = f"[TIMEOUT] context={context}"
        if command:
            log_msg += f" command={command}"
        if user_id:
            log_msg += f" user_id={user_id}"
        if duration:
            log_msg += f" duration={duration:.2f}s"
        
        logger.warning(log_msg)
        
        # Check if need to alert
        recent_count = self._count_recent_timeouts(context)
        if recent_count >= self.alert_threshold:
            logger.error(
                f"[TIMEOUT_ALERT] {context} has {recent_count} timeouts "
                f"in last {self.time_window}s - INVESTIGATE NETWORK ISSUES!"
            )
    
    def _count_recent_timeouts(self, context: str) -> int:
        """Count timeouts in recent time window.
        
        Args:
            context: Context to check
            
        Returns:
            Number of timeouts in time window
        """
        current_time = time.time()
        cutoff = current_time - self.time_window
        
        # Remove old entries
        history = self.timeout_history[context]
        while history and history[0] < cutoff:
            history.popleft()
        
        return len(history)
    
    def get_stats(self) -> dict:
        """Get timeout statistics.
        
        Returns:
            Dictionary with timeout stats
        """
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Get recent timeouts per context
        context_stats = {}
        for context, history in self.timeout_history.items():
            recent = self._count_recent_timeouts(context)
            total = len(history)
            context_stats[context] = {
                "recent": recent,
                "total": total
            }
        
        return {
            "total_timeouts": self.total_timeouts,
            "uptime_seconds": int(uptime),
            "uptime_hours": uptime / 3600,
            "timeout_rate_per_hour": (self.total_timeouts / uptime * 3600) if uptime > 0 else 0,
            "contexts": context_stats,
            "alert_threshold": self.alert_threshold,
            "time_window": self.time_window
        }
    
    def print_stats(self) -> str:
        """Get formatted stats string.
        
        Returns:
            Formatted stats for logging/display
        """
        stats = self.get_stats()
        
        lines = [
            "=== TIMEOUT MONITOR STATS ===",
            f"Uptime: {stats['uptime_hours']:.2f} hours",
            f"Total Timeouts: {stats['total_timeouts']}",
            f"Rate: {stats['timeout_rate_per_hour']:.2f} timeouts/hour",
            "",
            "By Context:"
        ]
        
        for context, data in stats['contexts'].items():
            lines.append(
                f"  {context}: {data['recent']} recent / {data['total']} total"
            )
        
        return "\n".join(lines)


# Global instance
_monitor: Optional[TimeoutMonitor] = None


def get_monitor() -> TimeoutMonitor:
    """Get global timeout monitor instance.
    
    Returns:
        TimeoutMonitor singleton
    """
    global _monitor
    if _monitor is None:
        _monitor = TimeoutMonitor()
    return _monitor


def record_timeout(
    context: str,
    user_id: Optional[int] = None,
    command: Optional[str] = None,
    duration: Optional[float] = None
) -> None:
    """Convenience function to record timeout.
    
    Args:
        context: What was timing out
        user_id: User who triggered
        command: Command name
        duration: Duration before timeout
    """
    get_monitor().record_timeout(context, user_id, command, duration)
