#!/bin/bash

# Pocket Guide - Start Development Servers in tmux
# This creates a split terminal with backend on left, frontend on right

SESSION_NAME="pocket-guide"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux not installed. Install with: brew install tmux"
    echo "   Or use ./start-dev.sh instead"
    exit 1
fi

# Check if session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "⚠️  Session '$SESSION_NAME' already exists"
    echo "   Attach with: tmux attach -t $SESSION_NAME"
    echo "   Or kill it with: tmux kill-session -t $SESSION_NAME"
    exit 1
fi

echo "🚀 Starting Pocket Guide in tmux..."

# Create new session with backend
tmux new-session -d -s $SESSION_NAME -n "servers"

# Run backend in left pane
tmux send-keys -t $SESSION_NAME:0.0 "source venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo '📡 Starting Backend...'" C-m
tmux send-keys -t $SESSION_NAME:0.0 "python src/api_server.py" C-m

# Split window vertically
tmux split-window -h -t $SESSION_NAME:0

# Run frontend in right pane
tmux send-keys -t $SESSION_NAME:0.1 "cd backstage" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo '🎨 Starting Frontend...'" C-m
tmux send-keys -t $SESSION_NAME:0.1 "npm run dev" C-m

# Select left pane
tmux select-pane -t $SESSION_NAME:0.0

echo ""
echo "✅ Started tmux session: $SESSION_NAME"
echo ""
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""
echo "Attach to session with:"
echo "   tmux attach -t $SESSION_NAME"
echo ""
echo "Tmux commands (once attached):"
echo "   Ctrl+b then →/← - Switch between panes"
echo "   Ctrl+b then d   - Detach (servers keep running)"
echo "   Ctrl+c (both)   - Stop servers"
echo "   exit (both)     - Exit tmux session"

# Attach to session
tmux attach -t $SESSION_NAME
