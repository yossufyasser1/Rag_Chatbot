#!/bin/bash

# Setup script for RAG Gemini Chatbot deployment

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up RAG Gemini Chatbot deployment...${NC}"

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
read -p "GitHub Repository URL: " GITHUB_DOCS_REPO

# Ask if it's a private repository
echo -e "${YELLOW}Is this a private repository? (yes/no)${NC}"
read -p "Private repository: " IS_PRIVATE

if [[ $IS_PRIVATE == "yes" || $IS_PRIVATE == "y" ]]; then
    echo -e "${YELLOW}Please enter your GitHub Personal Access Token:${NC}"
    read -p "GitHub Token: " GITHUB_TOKEN
    echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> .env
fi

# Create .env file
echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" > .env
echo "GITHUB_DOCS_REPO=$GITHUB_DOCS_REPO" >> .env

# Update docker-compose.yml with the GitHub repository
sed -i "s|https://github.com/yourusername/company-docs.git|$GITHUB_DOCS_REPO|g" docker-compose.yml

echo -e "${GREEN}Starting the container...${NC}"
docker-compose up -d

echo -e "${GREEN}RAG Gemini Chatbot is now running!${NC}"
echo -e "${GREEN}Access the API at http://$(curl -s ifconfig.me):8080/api/chat/start${NC}"
echo -e "${YELLOW}Note: Make sure port 8080 is open in your firewall/security group${NC}"