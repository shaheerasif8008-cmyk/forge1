#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
    esac
}

echo "🔍 Forge 1 Development Environment Check"
echo "========================================"
echo

# Check Docker
echo "🐳 Checking Docker..."
if command -v docker >/dev/null 2>&1; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    print_status "OK" "Docker installed: $DOCKER_VERSION"
    
    if docker info >/dev/null 2>&1; then
        print_status "OK" "Docker daemon is running"
    else
        print_status "ERROR" "Docker daemon is not running"
        exit 1
    fi
else
    print_status "ERROR" "Docker is not installed"
    exit 1
fi

# Check Docker Compose
echo
echo "🐙 Checking Docker Compose..."
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version --short)
    print_status "OK" "Docker Compose v2 available: $COMPOSE_VERSION"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    print_status "WARN" "Docker Compose v1 available: $COMPOSE_VERSION (consider upgrading to v2)"
else
    print_status "ERROR" "Docker Compose is not available"
    exit 1
fi

# Check Python
echo
echo "🐍 Checking Python..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "OK" "Python 3 installed: $PYTHON_VERSION"
    
    # Check if version is 3.8 or higher
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_status "OK" "Python version meets requirements (>=3.8)"
    else
        print_status "WARN" "Python version $PYTHON_VERSION may be too old (recommend >=3.8)"
    fi
elif command -v python >/dev/null 2>&1; then
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
    print_status "WARN" "Python installed: $PYTHON_VERSION (consider using python3)"
else
    print_status "ERROR" "Python is not installed"
    exit 1
fi

# Check Node.js
echo
echo "🟢 Checking Node.js..."
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    print_status "OK" "Node.js installed: $NODE_VERSION"
    
    # Check if version is 16 or higher
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -ge 16 ]; then
        print_status "OK" "Node.js version meets requirements (>=16)"
    else
        print_status "WARN" "Node.js version $NODE_VERSION may be too old (recommend >=16)"
    fi
else
    print_status "ERROR" "Node.js is not installed"
    exit 1
fi

# Check npm
echo
echo "📦 Checking npm..."
if command -v npm >/dev/null 2>&1; then
    NPM_VERSION=$(npm --version)
    print_status "OK" "npm installed: $NPM_VERSION"
else
    print_status "ERROR" "npm is not installed"
    exit 1
fi

# Check ports availability
echo
echo "🔌 Checking port availability..."

# Check port 8000 (Backend)
if lsof -i :8000 >/dev/null 2>&1; then
    PROCESS=$(lsof -i :8000 | grep LISTEN | head -1 | awk '{print $1}')
    print_status "WARN" "Port 8000 is in use by: $PROCESS (Backend port)"
else
    print_status "OK" "Port 8000 is available (Backend)"
fi

# Check port 5432 (PostgreSQL)
if lsof -i :5432 >/dev/null 2>&1; then
    PROCESS=$(lsof -i :5432 | grep LISTEN | head -1 | awk '{print $1}')
    print_status "WARN" "Port 5432 is in use by: $PROCESS (PostgreSQL port)"
else
    print_status "OK" "Port 5432 is available (PostgreSQL)"
fi

# Check port 6379 (Redis)
if lsof -i :6379 >/dev/null 2>&1; then
    PROCESS=$(lsof -i :6379 | grep LISTEN | head -1 | awk '{print $1}')
    print_status "WARN" "Port 6379 is in use by: $PROCESS (Redis port)"
else
    print_status "OK" "Port 6379 is available (Redis)"
fi

# Check port 5173 (Frontend dev server)
if lsof -i :5173 >/dev/null 2>&1; then
    PROCESS=$(lsof -i :5173 | grep LISTEN | head -1 | awk '{print $1}')
    print_status "WARN" "Port 5173 is in use by: $PROCESS (Frontend dev server)"
else
    print_status "OK" "Port 5173 is available (Frontend dev server)"
fi

# Check environment files
echo
echo "📁 Checking environment configuration..."
if [ -f "../.env" ]; then
    print_status "OK" "Root .env file found"
elif [ -f "../.env.example" ]; then
    print_status "WARN" "Root .env.example found but no .env (copy .env.example to .env)"
else
    print_status "WARN" "No .env or .env.example found in root directory"
fi

if [ -f "../frontend/.env" ]; then
    print_status "OK" "Frontend .env file found"
elif [ -f "../frontend/.env.example" ]; then
    print_status "WARN" "Frontend .env.example found but no .env"
else
    print_status "WARN" "No frontend .env or .env.example found"
fi

# Check Docker Compose configuration
echo
echo "🐳 Checking Docker Compose configuration..."
if [ -f "../docker-compose.yml" ]; then
    print_status "OK" "Root docker-compose.yml found"
    if docker compose -f ../docker-compose.yml config >/dev/null 2>&1; then
        print_status "OK" "Docker Compose configuration is valid"
    else
        print_status "ERROR" "Docker Compose configuration has errors"
        exit 1
    fi
else
    print_status "WARN" "No docker-compose.yml found in root directory"
fi

# Check backend requirements
echo
echo "�� Checking backend dependencies..."
if [ -f "../backend/requirements.txt" ]; then
    print_status "OK" "Backend requirements.txt found"
    if [ -d "../backend/.venv" ] || [ -d "../backend/venv" ]; then
        print_status "OK" "Backend virtual environment found"
    else
        print_status "WARN" "Backend virtual environment not found (run: cd backend && python -m venv .venv)"
    fi
else
    print_status "WARN" "No backend requirements.txt found"
fi

# Check frontend dependencies
echo
echo "🟢 Checking frontend dependencies..."
if [ -f "../frontend/package.json" ]; then
    print_status "OK" "Frontend package.json found"
    if [ -d "../frontend/node_modules" ]; then
        print_status "OK" "Frontend node_modules found"
    else
        print_status "WARN" "Frontend node_modules not found (run: cd frontend && npm install)"
    fi
else
    print_status "WARN" "No frontend package.json found"
fi

echo
echo "🎯 Summary:"
echo "==========="
echo "All critical checks passed! 🎉"
echo
echo "Next steps:"
echo "1. Start backend: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "2. Start frontend: cd frontend && npm run dev"
echo "3. Start services: docker compose up -d"
echo
echo "Happy coding! 🚀"
