# Deployment Guide: RAG Gemini Chatbot on Internet-Accessible VM

This guide explains how to deploy your RAG Gemini Chatbot on a Virtual Machine, making it accessible over the internet.

## Prerequisites

- A Virtual Machine with internet access (e.g., AWS EC2, Google Compute Engine, Azure VM, DigitalOcean Droplet)
- SSH access to your VM
- A GitHub repository for storing your company documentation
- A Google API key for Gemini

## Step 1: Prepare Your Documentation Repository

1. Create a GitHub repository to store your company documentation (if you haven't already).
2. Upload your PDF, DOCX, TXT, and MD files to this repository.
3. Make sure the repository is either public or you have a GitHub Personal Access Token if it's private.

## Step 2: Set Up the VM

1. SSH into your VM:
   ```
   ssh username@your-vm-ip
   ```

2. Install Git:
   ```
   sudo apt-get update && sudo apt-get install -y git
   ```

3. Clone this repository:
   ```
   git clone https://github.com/YOUR_USERNAME/rag-chatbot.git
   cd rag-chatbot
   ```

## Step 3: Deploy the Chatbot

1. Make the setup script executable:
   ```
   chmod +x setup.sh
   ```

2. Run the setup script:
   ```
   ./setup.sh
   ```

3. Follow the prompts:
   - Enter your Google API key
   - Enter the GitHub repository URL containing your company documentation
   - Indicate if it's a private repository and provide a GitHub token if needed

The script will:
- Install Docker and Docker Compose if not already installed
- Configure the firewall to allow traffic on port 8080
- Set up environment variables
- Build and start the Docker container

## Step 4: Test the Deployment

The API endpoints will be accessible at:

- Start a new chat session: 
  ```
  curl -X POST http://YOUR_VM_IP:8080/api/chat/start
  ```

- Send a message (replace SESSION_ID with the ID returned from the start endpoint):
  ```
  curl -X POST http://YOUR_VM_IP:8080/api/chat/SESSION_ID \
      -H "Content-Type: application/json" \
      -d '{"query": "What does your company offer?"}'
  ```

## Managing the Deployment

### Update Documentation

When you update your GitHub repository with new documentation:

1. SSH into your VM
2. Navigate to the project directory
3. Rebuild the container:
   ```
   docker-compose down
   docker-compose up --build -d
   ```

### View Logs

To check the container logs:
```
docker-compose logs
```

To follow the logs in real-time:
```
docker-compose logs -f
```

### Backup Data

The application stores conversation logs and vector database data in Docker volumes. To back them up:

1. Create a backup directory:
   ```
   mkdir -p ~/backups
   ```

2. Find the volume names:
   ```
   docker volume ls
   ```

3. Create a backup:
   ```
   docker run --rm -v rag-chatbot_vector_db_data:/data -v ~/backups:/backup alpine tar -czf /backup/vector_db_backup.tar.gz /data
   docker run --rm -v rag-chatbot_conversation_logs:/data -v ~/backups:/backup alpine tar -czf /backup/conversation_logs_backup.tar.gz /data
   ```

## Security Considerations

1. **API Security**: This deployment does not include authentication. For production use, consider adding an API key system or OAuth.

2. **HTTPS**: The current setup uses HTTP. For production, set up HTTPS using a reverse proxy like Nginx with Let's Encrypt.

3. **Firewall**: The setup script opens port 8080. Ensure your VM's security group or network security settings also allow this port.

## Troubleshooting

1. **Container not starting**:
   ```
   docker-compose logs
   ```

2. **API not accessible**:
   - Check if port 8080 is open: `sudo ufw status` or `sudo firewall-cmd --list-all`
   - Verify the container is running: `docker ps`

3. **Document processing issues**:
   - Check if the repository was cloned correctly: `ls -la /app/company_docs` inside the container
   - Review logs for document loading errors

For any other issues, feel free to check the container logs or contact support.