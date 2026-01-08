#!/bin/bash
set -e

echo "============================================"
echo "   BHNBot - One-Click Setup Script"
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_requirements() {
    print_status "Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker first."
        echo "  Ubuntu/Debian: sudo apt install docker.io docker-compose"
        echo "  Or visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker found"
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose not found."
        exit 1
    fi
    print_success "Docker Compose found"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found."
        exit 1
    fi
    print_success "Python3 found: $(python3 --version)"
}

setup_env() {
    print_status "Checking .env file..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your Discord token!"
            echo ""
            echo "  Required variables:"
            echo "    DISCORD_TOKEN=your_bot_token_here"
            echo "    DATABASE_URL=postgresql://bhnbot:bhnbot_secure_2026@localhost:5432/bhnbot_db"
            echo ""
            read -p "Press Enter after editing .env, or Ctrl+C to cancel..."
        else
            print_error ".env.example not found. Please create .env manually."
            exit 1
        fi
    fi
    print_success ".env file exists"
}

setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        print_success "Created virtual environment"
    fi
    
    source .venv/bin/activate
    
    print_status "Installing dependencies..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    print_success "Dependencies installed"
}

start_services() {
    print_status "Starting Docker services (PostgreSQL + Lavalink)..."
    
    if docker compose version &> /dev/null; then
        docker compose up -d
    else
        docker-compose up -d
    fi
    
    print_status "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker exec bhnbot-postgres pg_isready -U bhnbot -d bhnbot_db &> /dev/null; then
            print_success "PostgreSQL is ready"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    print_status "Waiting for Lavalink to be ready..."
    for i in {1..60}; do
        if curl -s http://localhost:2333/version &> /dev/null; then
            print_success "Lavalink is ready"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
}

init_database() {
    print_status "Initializing database..."
    source .venv/bin/activate
    python3 scripts/init_postgres.py
    print_success "Database initialized"
}

run_migrations() {
    print_status "Running migrations..."
    source .venv/bin/activate
    
    if [ -f "scripts/add_streak_columns.py" ]; then
        python3 scripts/add_streak_columns.py
    fi
    
    print_success "Migrations complete"
}

show_status() {
    echo ""
    echo "============================================"
    echo "   Setup Complete!"
    echo "============================================"
    echo ""
    
    echo "Docker Services:"
    docker ps --format "  {{.Names}}: {{.Status}}" | grep bhnbot || echo "  (no services running)"
    echo ""
    
    echo "To start the bot:"
    echo "  source .venv/bin/activate"
    echo "  python3 main.py"
    echo ""
    
    echo "To stop services:"
    echo "  docker compose down"
    echo ""
    
    echo "To view logs:"
    echo "  docker compose logs -f lavalink"
    echo "  docker compose logs -f postgres"
    echo ""
}

main() {
    check_requirements
    setup_env
    setup_venv
    start_services
    init_database
    run_migrations
    show_status
}

case "${1:-}" in
    --services-only)
        check_requirements
        start_services
        ;;
    --db-only)
        init_database
        run_migrations
        ;;
    --help)
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (no args)        Full setup"
        echo "  --services-only  Start Docker services only"
        echo "  --db-only        Initialize database only"
        echo "  --help           Show this help"
        ;;
    *)
        main
        ;;
esac
