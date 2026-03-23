#!/bin/bash

# Test Tunnel Connection
# Validates that your tunnel is working correctly before you go walk

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Testing Tunnel Connection${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Ask for tunnel URL
echo -e "${YELLOW}Enter your Cloudflare tunnel URL:${NC}"
echo -e "${BLUE}(e.g., https://abc-xyz-123.trycloudflare.com)${NC}"
read -r TUNNEL_URL

# Remove trailing slash if present
TUNNEL_URL="${TUNNEL_URL%/}"

echo ""
echo -e "${BLUE}Testing connection to: ${BOLD}${TUNNEL_URL}${NC}"
echo ""

# Test 1: Check if URL is reachable
echo -e "${BLUE}[1/4] Testing if tunnel is reachable...${NC}"
if curl -s -o /dev/null -w "%{http_code}" "${TUNNEL_URL}/docs" | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✅ Tunnel is reachable!${NC}"
else
    echo -e "${RED}❌ Tunnel is not reachable${NC}"
    echo -e "${YELLOW}   Make sure the tunnel is running: ./scripts/start_tunnel.sh${NC}"
    exit 1
fi

# Test 2: Check API docs
echo -e "${BLUE}[2/4] Testing API documentation endpoint...${NC}"
if curl -s "${TUNNEL_URL}/docs" | grep -q "Pocket Guide"; then
    echo -e "${GREEN}✅ API docs accessible!${NC}"
else
    echo -e "${RED}❌ API docs not accessible${NC}"
    echo -e "${YELLOW}   Make sure the API server is running: ./scripts/start_api_server.sh${NC}"
    exit 1
fi

# Test 3: Check OpenAPI schema
echo -e "${BLUE}[3/4] Testing OpenAPI schema...${NC}"
if curl -s "${TUNNEL_URL}/openapi.json" | grep -q "progress"; then
    echo -e "${GREEN}✅ Map mode endpoints detected!${NC}"
else
    echo -e "${RED}❌ Map mode endpoints not found${NC}"
    exit 1
fi

# Test 4: Check authentication (should return 401/403)
echo -e "${BLUE}[4/4] Testing authentication requirement...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${TUNNEL_URL}/tours/test-tour/progress")
if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ]; then
    echo -e "${GREEN}✅ Authentication is working! (got ${HTTP_CODE} as expected)${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected status code: ${HTTP_CODE}${NC}"
    echo -e "${YELLOW}   (Expected 401 or 403 for unauthenticated request)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ All Tests Passed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BOLD}Your tunnel is ready for mobile testing!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Update your Flutter app with this URL:"
echo -e "   ${BOLD}${TUNNEL_URL}${NC}"
echo ""
echo "2. Build and install app on iPhone"
echo ""
echo "3. Login to the app"
echo ""
echo "4. Go walk and test! 🚶‍♂️"
echo ""
