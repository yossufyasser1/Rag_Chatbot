# RAG Gemini Chatbot Docker Setup

This repository contains a Dockerized version of the RAG Gemini Chatbot for deployment on a VM with internet accessibility.

## Prerequisites

- Docker and Docker Compose installed on your VM
- Your Google API key for Gemini
- Your vector_db directory (pre-built vector database)
- SQLite database for conversation logging (automatically set up)
- GitHub repository for database synchronization (optional)

## Setup Instructions

### 1. Clone this repository

```bash
git clone https://github.com/yossufyasser1/Rag_Chatbot.git
cd rag-gemini-chatbot
```

### 2. Create a GitHub repository for your code

1. Create a new repository on GitHub
2. Upload your RAG_Chatbot_final.py and Rag_Endpoint.py files to the repository
3. Update the Dockerfile with your actual GitHub repository URL

### 3. Prepare your VM

1. Install Docker and Docker Compose on your VM
2. Clone your GitHub repository to the VM
3. Create a `.env` file with your configuration:

```bash
# Basic configuration
GOOGLE_API_KEY=your_api_key_here

# Database Configuration
DB_PATH=conversations.db

# GitHub Sync Configuration (optional)
GIT_REPO_URL=https://github.com/yourusername/your-repo.git
GIT_USER_NAME="Chatbot Database Sync"
GIT_USER_EMAIL="your-email@example.com"
GIT_SYNC_INTERVAL_MINUTES=60
```

### 4. Set up GitHub authentication

For the database synchronization to work, you need to set up Git authentication:

#### Option 1: SSH key (recommended)

1. Generate an SSH key on your VM:
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"
   ```

2. Add the SSH key to your GitHub account:
   - Display your public key: `cat ~/.ssh/id_ed25519.pub`
   - Copy the output and add it to your GitHub SSH keys in settings

3. Update your .env file to use the SSH URL:
   ```
   GIT_REPO_URL=git@github.com:yourusername/your-repo.git
   ```

#### Option 2: Personal Access Token

1. Create a Personal Access Token on GitHub with repo permissions
2. Use it in your git remote URL:
   ```
   GIT_REPO_URL=https://username:personal_access_token@github.com/yourusername/your-repo.git
   ```

### 5. Transfer your vector_db

Transfer your vector_db directory to the VM. You can do this by:

- Including it in your GitHub repository (if not too large)
- Using SCP or SFTP to transfer it directly
- Using a cloud storage service to download it to the VM

Make sure to place the vector_db directory in the same location as your docker-compose.yml file.

### 6. SQLite Database Configuration

The chatbot uses SQLite for storing conversation logs. The database will be automatically created when you run the chatbot. By default, it's stored in a file called `conversations.db` in the same directory as the chatbot.

If you have existing conversation logs in JSON format, you can import them into the database using the included `import_logs.py` script:

```bash
python import_logs.py --logs-dir conversation_logs --db-path conversations.db
```

After importing, you can safely remove the conversation_logs directory as it is no longer needed.

### 7. Configure docker-compose.yml

Create a docker-compose.yml file:

```yaml
version: '3'
services:
  rag-chatbot:
    build: .
    ports:
      - "8080:5000"
    volumes:
      - ./vector_db:/app/vector_db
      - ./conversations.db:/app/conversations.db
      - ~/.ssh:/root/.ssh  # For GitHub SSH authentication
    env_file:
      - .env
    restart: unless-stopped
```

### 8. Build and run the container

```bash
docker-compose up -d
```

This will:
- Build the Docker image
- Start the container
- Map port 8080 to be accessible from outside
- Mount your vector_db directory into the container
- Set up database synchronization with GitHub (if configured)
- Set your configuration as environment variables

### 9. Database Synchronization Process

When configured properly, the container will:
1. Run a background task that regularly checks for database changes
2. Commit any changes to the conversations.db file to your Git repository
3. Push the changes to GitHub at the interval specified in GIT_SYNC_INTERVAL_MINUTES
4. Log sync activity to the container's stdout (viewable with `docker-compose logs`)

This allows you to access your database from other locations by pulling the latest version from GitHub.

### 10. Accessing the API

Your RAG Gemini Chatbot API will now be accessible at:

```
http://YOUR_VM_IP:8080/api/chat/start
```

## API Endpoints

- `POST /api/chat/start` - Start a new chat session
- `POST /api/chat/<session_id>` - Send a message to an existing session
- `GET /api/chat/<session_id>/history` - Get conversation history
- `DELETE /api/chat/<session_id>` - End a chat session
- `GET /health` - Check if the service is running

## Additional Command-Line Options

When running the chatbot directly (not through the API), you can use these additional options:

```
--db-path PATH        Path to SQLite database file (default: ./conversations.db)
```

## SQLite Database Structure

The database contains the following tables:

- `conversations`: Stores information about each conversation session
  - `id`: Unique identifier for the conversation
  - `session_id`: UUID of the session
  - `start_time`: When the conversation started
  - `end_time`: When the conversation ended
  - `created_at`: When the record was created

- `messages`: Stores each message in the conversations
  - `id`: Unique identifier for the message
  - `conversation_id`: Foreign key to the conversations table
  - `timestamp`: When the message was sent
  - `role`: Either 'user' or 'assistant'
  - `content`: The message content
  - `created_at`: When the record was created

## Troubleshooting

If you encounter any issues:

1. Check the container logs:
```bash
docker-compose logs
```

2. Make sure your VM's firewall allows incoming connections on port 8080

3. Verify your vector_db directory is properly mounted by checking:
```bash
docker-compose exec rag-chatbot ls -la /app/vector_db
```

4. Test the API locally on the VM to rule out network connectivity issues:
```bash
curl -X POST http://localhost:8080/api/chat/start
```

5. Check the SQLite database:
```bash
# List all conversations
sqlite3 conversations.db "SELECT * FROM conversations"

# Count messages in database
sqlite3 conversations.db "SELECT COUNT(*) FROM messages"
```

6. Verify GitHub synchronization is working:
```bash
# Check sync script is running
docker-compose exec rag-chatbot ps aux | grep sync_database

# Check sync logs
docker-compose logs | grep "Syncing database"

# Manually trigger a sync from inside the container
docker-compose exec rag-chatbot /app/sync_database.sh
```
