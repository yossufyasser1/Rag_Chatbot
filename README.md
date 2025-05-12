# RAG Gemini Chatbot Docker Setup

This repository contains a Dockerized version of the RAG Gemini Chatbot for deployment on a VM with internet accessibility.

## Prerequisites

- Docker and Docker Compose installed on your VM
- Your Google API key for Gemini
- Your vector_db directory (pre-built vector database)

## Setup Instructions

### 1. Clone this repository

```bash
git clone https://github.com/yourusername/rag-gemini-chatbot.git
cd rag-gemini-chatbot
```

### 2. Create a GitHub repository for your code

1. Create a new repository on GitHub
2. Upload your RAG_Chatbot_final.py and Rag_Endpoint.py files to the repository
3. Update the Dockerfile with your actual GitHub repository URL

### 3. Prepare your VM

1. Install Docker and Docker Compose on your VM
2. Clone your GitHub repository to the VM
3. Create a `.env` file with your Google API key:

```bash
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

### 4. Transfer your vector_db

Transfer your vector_db directory to the VM. You can do this by:

- Including it in your GitHub repository (if not too large)
- Using SCP or SFTP to transfer it directly
- Using a cloud storage service to download it to the VM

Make sure to place the vector_db directory in the same location as your docker-compose.yml file.

### 5. Build and run the container

```bash
docker-compose up -d
```

This will:
- Build the Docker image
- Start the container
- Map port 8080 to be accessible from outside
- Mount your vector_db directory into the container
- Set your Google API key as an environment variable

### 6. Accessing the API

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