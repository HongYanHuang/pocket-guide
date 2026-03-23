#!/bin/bash

# Pocket Guide - Mobile Testing Setup in tmux
# This creates a split terminal with API server on left, Cloudflare tunnel on right

SESSION_NAME="pocket-guide-mobile"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Pocket Guide Mobile Testing${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}❌ tmux not installed.${NC}"
    echo -e "   Install with: ${BOLD}brew install tmux${NC}"
    echo ""
    echo "   Or use manual method:"
    echo "   Terminal 1: ./scripts/start_api_server.sh"
    echo "   Terminal 2: ./scripts/start_tunnel.sh"
    exit 1
fi

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}❌ cloudflared not installed.${NC}"
    echo -e "   Install with: ${BOLD}brew install cloudflare/cloudflare/cloudflared${NC}"
    echo ""
    exit 1
fi

# Check if session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Session '$SESSION_NAME' already exists${NC}"
    echo ""
    echo "Options:"
    echo "  1. Attach: tmux attach -t $SESSION_NAME"
    echo "  2. Kill:   tmux kill-session -t $SESSION_NAME"
    echo ""
    exit 1
fi

# Check if port 8000 is in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use!${NC}"
    echo ""
    echo "Kill the process? (y/n)"
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

echo -e "${GREEN}✅ tmux installed${NC}"
echo -e "${GREEN}✅ cloudflared installed${NC}"
echo ""
echo -e "${BLUE}Creating tmux session...${NC}"
echo ""

# Create new session with API server (set working directory to project root)
tmux new-session -d -s $SESSION_NAME -n "mobile-test" -c "$PWD"

# Run API server in left pane
tmux send-keys -t $SESSION_NAME:0.0 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo '========================================'" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo '  API Server (Left Pane)'" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo '========================================'" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo 'Starting API server...'" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo ''" C-m
sleep 1
tmux send-keys -t $SESSION_NAME:0.0 "export PYTHONPATH=\"\${PYTHONPATH}:\$(pwd)/src\"" C-m
tmux send-keys -t $SESSION_NAME:0.0 "pocket-guide-3.11/bin/python -m uvicorn src.api_server:app --reload --port 8000" C-m

# Split window vertically for Cloudflare tunnel
tmux split-window -h -c "$PWD" -t $SESSION_NAME:0

# Wait for API server to start
sleep 3

# Run Cloudflare tunnel in right pane
tmux send-keys -t $SESSION_NAME:0.1 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '========================================'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '  Cloudflare Tunnel (Right Pane)'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '========================================'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '⏳ Waiting for API server to be ready...'" C-m
sleep 3
tmux send-keys -t $SESSION_NAME:0.1 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '🚀 Starting Cloudflare tunnel...'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '================================================'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '  📋 COPY THE URL THAT APPEARS BELOW'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '  You need it for your Flutter app!'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '================================================'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo ''" C-m
sleep 1
tmux send-keys -t $SESSION_NAME:0.1 "cloudflared tunnel --url http://localhost:8000" C-m

# Select left pane (API server)
tmux select-pane -t $SESSION_NAME:0.0

# Print instructions
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ Started tmux session: $SESSION_NAME${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BOLD}Layout:${NC}"
echo "   Left pane:  API Server (http://localhost:8000)"
echo "   Right pane: Cloudflare Tunnel (watch for URL)"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "   1. ${YELLOW}Look at the RIGHT pane${NC}"
echo "   2. ${YELLOW}Copy the tunnel URL${NC} (https://xxx.trycloudflare.com)"
echo "   3. ${YELLOW}Update your Flutter app${NC} with that URL"
echo "   4. Build app on iPhone"
echo "   5. Go walk! 🚶‍♂️"
echo ""
echo -e "${BOLD}Attaching to session...${NC}"
echo ""
echo -e "${BLUE}Tmux commands (once attached):${NC}"
echo "   Ctrl+b then →/← - Switch between panes"
echo "   Ctrl+b then d   - Detach (keeps running)"
echo "   Ctrl+c (both)   - Stop both servers"
echo "   exit (both)     - Exit tmux session"
echo ""
echo -e "${BLUE}To reattach later:${NC}"
echo "   tmux attach -t $SESSION_NAME"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""
sleep 2

# Attach to session
tmux attach -t $SESSION_NAME
