#!/bin/bash
# Bot Health Monitor - PostgreSQL Upgrade
# Created: 2025-12-31
# Usage: bash scripts/monitor_health.sh

echo "=== BOT HEALTH CHECK $(date) ==="
echo ""

# 1. Bot Status
echo "1. Bot Status:"
if sudo systemctl is-active --quiet discordbot; then
    echo "   ✅ Active"
else
    echo "   ❌ INACTIVE!"
fi

# 2. Database Connection (PostgreSQL)
echo "2. Database Connection:"
# Check active connections to discord_bot_db
pg_conns=$(sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'discord_bot_db';" -t 2>/dev/null | xargs)
if [ -n "$pg_conns" ] && [ "$pg_conns" -gt 0 ]; then
    echo "   ✅ Connected (Active sessions: $pg_conns)"
else
    # Try simple connection check
    if sudo -u postgres psql -c "\l" >/dev/null 2>&1; then
        echo "   ⚠️  Postgres running but 0 bot connections (Idle/Down?)"
    else
        echo "   ❌ POSTGRESQL DOWN!"
    fi
fi

# 3. Recent Errors (Last 30 mins)
errors=$(sudo journalctl -u discordbot --since "30 minutes ago" 2>/dev/null | grep -iE "error|critical" | grep -v "ClientConnectorDNSError" | wc -l)
if [ "$errors" -eq 0 ]; then
    echo "3. Recent Errors: ✅ 0"
elif [ "$errors" -le 5 ]; then
    echo "3. Recent Errors: ⚠️  $errors (Monitor logs)"
else
    echo "3. Recent Errors: ❌ $errors FOUND!"
fi

# 4. Memory Usage
mem=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $6}')
if [ -z "$mem" ]; then
    mem=0
fi
mem_mb=$((mem / 1024))
echo "4. Memory Usage: ${mem_mb}MB"

# 5. Connection Pool Status (Log scraping)
pool_ok=$(sudo journalctl -u discordbot --since "10 minutes ago" | grep "DB_POOL" | tail -n 1)
if [ -n "$pool_ok" ]; then
    echo "5. DB Pool: ✅ Alive"
else
    echo "5. DB Pool: ❓ No recent logs"
fi

echo ""
if [ "$errors" -gt 5 ]; then
    echo "🚨 STATUS: ATTENTION NEEDED!"
else
    echo "✅ STATUS: SYSTEM HEALTHY"
fi
echo "================================"
