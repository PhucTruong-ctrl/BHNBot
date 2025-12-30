#!/bin/bash
# Bot Health Monitor - Database Deadlock Fix Verification
# Created: 2025-12-30
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

# 2. Database Locks (last 30min)
locks=$(sudo journalctl -u discordbot --since "30 minutes ago" 2>/dev/null | grep -i "database is locked" | wc -l)
if [ "$locks" -eq 0 ]; then
    echo "2. Database Locks: ✅ 0"
else
    echo "2. Database Locks: ❌ $locks FOUND!"
fi

# 3. Lock Balance
acquired=$(sudo journalctl -u discordbot --since "30 minutes ago" 2>/dev/null | grep "Lock acquired" | wc -l)
released=$(sudo journalctl -u discordbot --since "30 minutes ago" 2>/dev/null | grep "Lock released" | wc -l)
balance=$((acquired - released))

if [ "$balance" -le 1 ] && [ "$balance" -ge -1 ]; then
    echo "3. Lock Balance: ✅ $balance (A:$acquired R:$released)"
else
    echo "3. Lock Balance: ⚠️  $balance (A:$acquired R:$released)"
fi

# 4. Recent Errors
errors=$(sudo journalctl -u discordbot --since "30 minutes ago" 2>/dev/null | grep -iE "error|critical" | grep -v "ClientConnectorDNSError" | wc -l)
if [ "$errors" -le 5 ]; then
    echo "4. Recent Errors: ✅ $errors"
else
    echo "4. Recent Errors: ⚠️  $errors"
fi

# 5. WAL File Size
wal_size=$(ls -lh data/database.db-wal 2>/dev/null | awk '{print $5}')
echo "5. WAL File Size: $wal_size"

# 6. Memory
mem=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $6}')
mem_mb=$((mem / 1024))
echo "6. Memory Usage: ${mem_mb}MB"

echo ""
if [ "$locks" -gt 0 ] || [ "$balance" -gt 2 ]; then
    echo "🚨 STATUS: ATTENTION NEEDED!"
else
    echo "✅ STATUS: ALL SYSTEMS HEALTHY"
fi
echo "================================"
