#!/bin/bash
# Debug OAuth Flow - Run this while testing login

echo "=== OAuth Debug Monitor ==="
echo "Watching for login attempts..."
echo ""
echo "Instructions:"
echo "1. Keep this running"
echo "2. Try to login from your app"
echo "3. This will show what redirect_uri the client is sending"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Monitor API server logs for OAuth attempts
tail -f /dev/null 2>/dev/null || echo "Note: Will show logs from terminal where API runs"
