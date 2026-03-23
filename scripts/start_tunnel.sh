#!/bin/bash

# Start Cloudflare Tunnel for Mobile Testing
# This script starts a Cloudflare tunnel to expose local API server

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Starting Cloudflare Tunnel${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}❌ cloudflared is not installed!${NC}"
    echo ""
    echo -e "${YELLOW}Please install it first:${NC}"
    echo -e "  ${BOLD}brew install cloudflare/cloudflare/cloudflared${NC}"
    echo ""
    exit 1
fi

# Check if API server is running on port 8000
if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Warning: No server detected on port 8000${NC}"
    echo ""
    echo -e "Make sure your API server is running first!"
    echo -e "Run in another terminal: ${BOLD}./scripts/start_api_server.sh${NC}"
    echo ""
    echo "Do you want to continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}Exiting. Start the API server first.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ cloudflared is installed${NC}"
echo -e "${GREEN}✅ Creating tunnel to http://localhost:8000${NC}"
echo ""
echo -e "${BOLD}${BLUE}================================================${NC}"
echo -e "${BOLD}${BLUE}  COPY THE URL THAT APPEARS BELOW${NC}"
echo -e "${BOLD}${BLUE}  You'll need it for your Flutter app!${NC}"
echo -e "${BOLD}${BLUE}================================================${NC}"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop the tunnel${NC}"
echo ""

# Start the tunnel
cloudflared tunnel --url http://localhost:8000
