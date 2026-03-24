#!/bin/bash

# Start API Server with caffeinate (keeps Mac awake)
# This script starts the FastAPI server and prevents Mac from sleeping

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Starting API Server (Keep Awake)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "src/api_server.py" ]; then
    echo -e "${YELLOW}⚠️  Error: Must be run from project root directory${NC}"
    exit 1
fi

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use!${NC}"
    echo ""
    echo "Do you want to kill the existing process? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${BLUE}Killing process on port 8000...${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 1
    else
        echo -e "${YELLOW}Exiting. Please stop the process on port 8000 first.${NC}"
        exit 1
    fi
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

echo -e "${GREEN}✅ Starting API server on http://localhost:8000${NC}"
echo -e "${GREEN}✅ API docs available at http://localhost:8000/docs${NC}"
echo -e "${GREEN}✅ Mac will stay awake while server is running${NC}"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop the server${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""

# Start the server with caffeinate (keeps Mac awake)
# Try virtual environment first, fall back to system python
if [ -f "pocket-guide-3.11/bin/python" ]; then
    echo -e "${BLUE}Using virtual environment: pocket-guide-3.11${NC}"
    echo -e "${BLUE}☕ caffeinate: Mac will not sleep${NC}"
    echo ""
    caffeinate -i pocket-guide-3.11/bin/python -m uvicorn src.api_server:app --reload --port 8000
elif command -v python3 &> /dev/null; then
    echo -e "${BLUE}Using system python3${NC}"
    echo -e "${BLUE}☕ caffeinate: Mac will not sleep${NC}"
    echo ""
    caffeinate -i python3 -m uvicorn src.api_server:app --reload --port 8000
else
    echo -e "${RED}❌ No Python found!${NC}"
    exit 1
fi
