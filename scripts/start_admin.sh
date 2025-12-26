#!/bin/bash

# Define paths
ROOT_DIR="$HOME/BHNBot"
WEB_DIR="$ROOT_DIR/web"
FRONTEND_DIR="$WEB_DIR/frontend"

echo "🔄 Checking for existing processes..."
# Kill existing processes
pkill -f "uvicorn main:app"
pkill -f "vite"
sleep 2

echo "🚀 Starting Admin Panel..."

# Start Backend
cd "$WEB_DIR"
nohup python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID $BACKEND_PID) -> http://0.0.0.0:8000"

# Start Frontend
cd "$FRONTEND_DIR"
nohup npm run dev -- --host > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID $FRONTEND_PID) -> http://0.0.0.0:5173"

echo "---------------------------------------------------"
echo "🌐 Access via Tailscale: http://100.118.206.30:5173"
echo "📜 Logs are being written to web/backend.log and web/frontend/frontend.log"
echo "---------------------------------------------------"
