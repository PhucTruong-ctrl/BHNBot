# BHNBot
#tool role manager:
pkill -f role_manager/app.py; sleep 1; cd /home/phuctruong/Work/BHNBot/tools/role_manager && .venv/bin/python app.py -

#how to run main.py
pkill -f "python3 main.py"; sleep 1; cd /home/phuctruong/Work/BHNBot && .venv/bin/python3 main.py

#restore database from backup
cp ./data/backups/auto/database_auto_YYYYMMDD_HHMMSS.db ./data/database.db
sudo systemctl restart discordbot