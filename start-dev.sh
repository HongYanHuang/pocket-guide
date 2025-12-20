#!/bin/bash

# Pocket Guide - Start Development Servers
# This script starts both the FastAPI backend and Vue frontend

echo "🚀 Starting Pocket Guide Development Servers..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: venv not found. Please run: python -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start backend in background
echo "📡 Starting FastAPI backend on http://localhost:8000..."
python src/api_server.py &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Start frontend in background
echo "🎨 Starting Vue frontend on http://localhost:5173..."
cd backstage
npm run dev &
FRONTEND_PID=$!

# Go back to root
cd ..

echo ""
echo "✅ Both servers are running!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Set trap to catch Ctrl+C
trap cleanup INT TERM

# Wait for user to press Ctrl+C
wait
