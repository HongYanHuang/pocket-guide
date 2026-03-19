#!/bin/bash
# Startup script for Pocket Guide API Server

# Get the directory where this script is located (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Project directory: $SCRIPT_DIR"
echo ""

# Activate the correct virtual environment
if [ ! -d "pocket-guide-3.11/bin" ]; then
    echo "❌ Error: Virtual environment 'pocket-guide-3.11' not found!"
    echo "   Please run this script from the project root directory."
    exit 1
fi

source pocket-guide-3.11/bin/activate

# Check if port 8000 is in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is already in use. Killing existing server..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 2
fi

# Start the server
echo "🚀 Starting Pocket Guide API Server..."
echo "   Python: $(which python)"
echo "   Version: $(python --version)"
echo ""
echo "Server will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server (foreground mode so you can see logs)
python src/api_server.py
