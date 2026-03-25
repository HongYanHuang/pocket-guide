#!/bin/bash
# Test what OAuth URL is generated

echo "=== Testing OAuth URL Generation ==="
echo ""
echo "This will show the EXACT URL and parameters sent to Google"
echo ""

# Start API server in background if not running
if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Starting API server..."
    ./scripts/start_api_server.sh &
    sleep 3
fi

# Test with localhost:3000 (what client is using)
echo "Testing with redirect_uri: http://localhost:3000/auth/callback"
echo ""
curl -s "http://localhost:8000/auth/debug/oauth-config?redirect_uri=http://localhost:3000/auth/callback" | python3 -m json.tool

echo ""
echo "=== Check the output above ==="
echo "- Does client_id exist in Google Cloud Console?"
echo "- Is it a 'Web application' type?"
echo "- Is it enabled?"
echo ""
