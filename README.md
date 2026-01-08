# BHNBot
## admin dashboard
./scripts/start_admin.sh
or
.venv/bin/python3 -m uvicorn web.main:app --host 0.0.0.0 --port 8080

## bot
pkill -f "python3 main.py"; sleep 1; cd /home/phuctruong/Work/BHNBot && .venv/bin/python3 main.py

## restore database from backup
cp ./data/backups/auto/database_auto_YYYYMMDD_HHMMSS.db ./data/database.db
sudo systemctl restart discordbot

# Health check (run every 2-4h)
bash scripts/monitor_health.sh

# Check for locks manually
sudo journalctl -u discordbot --since "1 hour ago" | grep -i "database is locked"

# Check lock balance
acquired=$(sudo journalctl -u discordbot --since "1 hour ago" | grep "Lock acquired" | wc -l)
released=$(sudo journalctl -u discordbot --since "1 hour ago" | grep "Lock released" | wc -l)
echo "Balance: $((acquired - released))"