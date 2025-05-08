#!/bin/bash

# Script to test the RAG Gemini Chatbot API

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the public IP address
PUBLIC_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || curl -s icanhazip.com)
BASE_URL="http://$PUBLIC_IP:8080"

echo -e "${YELLOW}Testing RAG Gemini Chatbot API at $BASE_URL${NC}"

# Test 1: Health check
echo -e "${YELLOW}Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s $BASE_URL/health)
if [[ "$HEALTH_RESPONSE" == *"healthy"* ]]; then
    echo -e "${GREEN}Health check passed!${NC}"
else
    echo -e "${RED}Health check failed. Response: $HEALTH_RESPONSE${NC}"
    exit 1
fi

# Test 2: Start a chat session
echo -e "${YELLOW}Creating a new chat session...${NC}"
START_RESPONSE=$(curl -s -X POST $BASE_URL/api/chat/start)
SESSION_ID=$(echo $START_RESPONSE | grep -o '"session_id":"[^"]*' | sed 's/"session_id":"//')

if [[ -z "$SESSION_ID" ]]; then
    echo -e "${RED}Failed to create chat session. Response: $START_RESPONSE${NC}"
    exit 1
else
    echo -e "${GREEN}Successfully created chat session with ID: $SESSION_ID${NC}"
fi

# Test 3: Send a query
echo -e "${YELLOW}Sending a test query...${NC}"
QUERY_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"query":"What does your company offer?"}' \
    $BASE_URL/api/chat/$SESSION_ID)

if [[ "$QUERY_RESPONSE" == *"error"* ]]; then
    echo -e "${RED}Query failed. Response: $QUERY_RESPONSE${NC}"
else
    echo -e "${GREEN}Query successful!${NC}"
    echo -e "${GREEN}Response: ${NC}"
    echo $QUERY_RESPONSE | grep -o '"response":"[^"]*' | sed 's/"response":"//'
fi

# Test 4: Get conversation history
echo -e "${YELLOW}Getting conversation history...${NC}"
HISTORY_RESPONSE=$(curl -s -X GET $BASE_URL/api/chat/$SESSION_ID/history)

if [[ "$HISTORY_RESPONSE" == *"error"* ]]; then
    echo -e "${RED}Getting history failed. Response: $HISTORY_RESPONSE${NC}"
else
    echo -e "${GREEN}Successfully retrieved conversation history!${NC}"
fi

# Test 5: End the session
echo -e "${YELLOW}Ending chat session...${NC}"
END_RESPONSE=$(curl -s -X DELETE $BASE_URL/api/chat/$SESSION_ID)

if [[ "$END_RESPONSE" == *"error"* ]]; then
    echo -e "${RED}Ending session failed. Response: $END_RESPONSE${NC}"
else
    echo -e "${GREEN}Successfully ended session!${NC}"
fi

echo -e "${GREEN}All tests completed!${NC}"