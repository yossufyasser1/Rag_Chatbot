#!/bin/bash

# Setup script for RAG Gemini Chatbot deployment on a VM

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up RAG Gemini Chatbot for internet access...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}Please log out and log back in for Docker group changes to take effect.${NC}"
    echo -e "${YELLOW}After logging back in, run this script again.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Installing Docker Compose...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Ask for Google API Key
echo -e "${YELLOW}Please enter your Google API Key for Gemini:${NC}"
read -p "API Key: " GOOGLE_API_KEY

# Ask for GitHub repository URL
echo -e "${YELLOW}Please enter the GitHub repository URL for your company documents:${NC}"
read -p "GitHub Repository URL (e.g., https://github.com/username/company-docs): " GITHUB_DOCS_REPO

# Ask if it's a private repository
echo -e "${YELLOW}Is this a private repository? (yes/no)${NC}"
read -p "Private repository: " IS_PRIVATE

if [[ $IS_PRIVATE == "yes" || $IS_PRIVATE == "y" ]]; then
    echo -e "${YELLOW}Please enter your GitHub Personal Access Token:${NC}"
    read -s -p "GitHub Token: " GITHUB_TOKEN
    echo ""
    echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> .env
fi

# Create .env file
echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" > .env
echo "GITHUB_DOCS_REPO=$GITHUB_DOCS_REPO" >> .env

# Check if port 8080 is open in the firewall
echo -e "${YELLOW}Ensuring port 8080 is open in the firewall...${NC}"

# Try to detect the OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    OS=$(uname -s)
fi

# Open port based on detected OS
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo apt-get update
    sudo apt-get install -y ufw
    sudo ufw allow 8080/tcp
    sudo ufw --force enable
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo yum install -y firewalld
    sudo systemctl start firewalld
    sudo systemctl enable firewalld
    sudo firewall-cmd --zone=public --add-port=8080/tcp --permanent
    sudo firewall-cmd --reload
else
    echo -e "${YELLOW}Could not automatically configure firewall. Please ensure port 8080 is open manually.${NC}"
fi

# Get public IP address
PUBLIC_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || curl -s icanhazip.com)

echo -e "${GREEN}Building and starting the container...${NC}"
docker-compose down
docker-compose up --build -d

echo -e "${GREEN}RAG Gemini Chatbot is now running!${NC}"
echo -e "${GREEN}The API is accessible at http://$PUBLIC_IP:8080/api/chat/start${NC}"
echo -e "${YELLOW}Note: You should use this URL in your frontend application.${NC}"
echo -e "${YELLOW}API Endpoints:${NC}"
echo -e "${YELLOW}- Start a new chat: POST http://$PUBLIC_IP:8080/api/chat/start${NC}"
echo -e "${YELLOW}- Send a message: POST http://$PUBLIC_IP:8080/api/chat/{session_id}${NC}"
echo -e "${YELLOW}- End a session: DELETE http://$PUBLIC_IP:8080/api/chat/{session_id}${NC}"
echo -e "${YELLOW}- Get history: GET http://$PUBLIC_IP:8080/api/chat/{session_id}/history${NC}"