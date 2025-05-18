# RAG Gemini Chatbot Docker Setup

This repository contains a Dockerized version of the RAG Gemini Chatbot for deployment on a VM with internet accessibility.

## Prerequisites

- Docker and Docker Compose installed on your VM
- Your Google API key for Gemini
- Your vector_db directory (pre-built vector database)
- SQLite database for conversation logging (automatically set up)

## Setup Instructions

### 1. Clone this repository

```bash
git clone https://github.com/yossufyasser1/Rag_Chatbot.git
cd rag-gemini-chatbot
```

### 2. Prepare your VM

1. Install Docker and Docker Compose on your VM
2. Clone your GitHub repository to the VM
3. Create a `.env` file with your configuration:

```bash
# Basic configuration
GOOGLE_API_KEY=your_api_key_here

# Database Configuration
DB_PATH=conversations.db

# Data Sync API Configuration
DATA_SYNC_PORT=5001
```

### 3. Transfer your vector_db

Transfer your vector_db directory to the VM. You can do this by:

- Including it in your GitHub repository (if not too large)
- Using SCP or SFTP to transfer it directly
- Using a cloud storage service to download it to the VM

Make sure to place the vector_db directory in the same location as your docker-compose.yml file.

### 4. SQLite Database Configuration

The chatbot uses SQLite for storing conversation logs. The database will be automatically created when you run the chatbot. By default, it's stored in a file called `conversations.db` in the same directory as the chatbot.

If you have existing conversation logs in JSON format, you can import them into the database using the included `import_logs.py` script:

```bash
python import_logs.py --logs-dir conversation_logs --db-path conversations.db
```

After importing, you can safely remove the conversation_logs directory as it is no longer needed.

### 5. Configure docker-compose.yml

The docker-compose.yml file includes two services:
- rag-chatbot: The main chatbot API service
- data-sync-api: A service for external data synchronization

```yaml
version: '3'
services:
  rag-chatbot:
    build: .
    ports:
      - "8081:5000"
    volumes:
      - ./vector_db:/app/vector_db
      - ./conversations.db:/app/conversations.db
    env_file:
      - .env
    restart: unless-stopped

  data-sync-api:
    build:
      context: .
      dockerfile: Dockerfile.sync
    ports:
      - "8082:5001"
    volumes:
      - ./conversations.db:/app/conversations.db
      - ./conversation_logs:/app/conversation_logs
    env_file:
      - .env
    restart: unless-stopped
    depends_on:
      - rag-chatbot
```

### 6. Build and run the container

```bash
docker-compose up -d
```

This will:
- Build the Docker images for both services
- Start the containers
- Map ports 8081 and 8082 to be accessible from outside
- Mount your vector_db directory and conversations.db into the containers
- Set your configuration as environment variables

### 7. Data Sync API for External Analysis

The Data Sync API provides a way to synchronize conversation data with external systems for analysis. The API runs on a separate port (default: 8082) and provides several endpoints for accessing the database.

To use the API for data analysis:

1. Access the API at `http://YOUR_VM_IP:8082/api/sync/health` to verify it's running
2. Use the provided endpoints to fetch data as needed
3. For automated synchronization, use the example client script:

```bash
python data_sync_client_example.py --api-url http://YOUR_VM_IP:8082 --continuous
```

This client script demonstrates how to pull data from the API at regular intervals, tracking the last synchronization time to minimize data transfer.

### 8. Accessing the API

Your RAG Gemini Chatbot API will now be accessible at:

```
http://YOUR_VM_IP:8081/api/chat/start
```

## API Endpoints

### Main Chatbot API (Port 8081)

- `POST /api/chat/start` - Start a new chat session
- `POST /api/chat/<session_id>` - Send a message to an existing session
- `GET /api/chat/<session_id>/history` - Get conversation history
- `DELETE /api/chat/<session_id>` - End a chat session
- `GET /health` - Check if the service is running

### Data Sync API (Port 8082)

- `GET /api/sync/health` - Health check for the Data Sync API
- `GET /api/sync/conversations/recent` - Get recent conversations (with optional `hours` parameter)
- `GET /api/sync/conversations/<conversation_id>/messages` - Get messages for a specific conversation
- `GET /api/sync/delta` - Get changes since a specific time (with optional `since` parameter)
- `GET /api/sync/export` - Export the entire database content
- `GET /api/sync/statistics` - Get database statistics

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

## Data Sync Client

The `data_sync_client_example.py` script demonstrates how to use the Data Sync API to pull data for external analysis. It provides several options:

```bash
python data_sync_client_example.py --help
```

Options:
- `--api-url URL` - Base URL of the Data Sync API (default: http://localhost:8082)
- `--interval SECONDS` - Sync interval in seconds (default: 300)
- `--continuous` - Run in continuous sync mode
- `--stats` - Retrieve and display database statistics

## Troubleshooting

If you encounter any issues:

1. Check the container logs:
```bash
docker-compose logs
```

2. Make sure your VM's firewall allows incoming connections on ports 8081 and 8082

3. Verify your vector_db directory is properly mounted by checking:
```bash
docker-compose exec rag-chatbot ls -la /app/vector_db
```

4. Test the Data Sync API connection:
```bash
curl http://YOUR_VM_IP:8082/api/sync/health
```
