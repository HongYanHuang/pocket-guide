#!/bin/bash

# Pocket Guide - Stop Development Servers

echo "🛑 Stopping Pocket Guide Development Servers..."

# Kill FastAPI backend (Python on port 8000)
BACKEND_PID=$(lsof -ti:8000)
if [ ! -z "$BACKEND_PID" ]; then
    kill $BACKEND_PID
    echo "✓ Backend stopped (PID: $BACKEND_PID)"
else
    echo "⚠ Backend not running on port 8000"
fi

# Kill Vite frontend (Node on port 5173)
FRONTEND_PID=$(lsof -ti:5173)
if [ ! -z "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID
    echo "✓ Frontend stopped (PID: $FRONTEND_PID)"
else
    echo "⚠ Frontend not running on port 5173"
fi

echo "✅ Done!"
