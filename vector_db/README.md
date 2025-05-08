# RAG Gemini Chatbot Docker Deployment

This repository contains the necessary files to deploy the RAG Gemini Chatbot in a Docker container, making it accessible over the internet.

## Prerequisites

- A VM with internet access
- Docker and Docker Compose installed (or use the setup script)
- A Google API key for Gemini
- A GitHub repository containing your company documents

## Setup Instructions

### 1. Create GitHub Repository for Company Documents

Create a GitHub repository to store your company documentation. This repository should contain all the documents (PDF, DOCX, TXT, MD files) that you want the chatbot to use.

Example structure:
```
/
├── policies/
│   ├── privacy_policy.pdf
│   ├── terms_of_service.docx
├── products/
│   ├── product_catalog.pdf
│   ├── pricing.txt
├── faqs/
│   ├── technical_faq.md
│   ├── general_faq.txt
```

Push all your company documents to this repository.

### 2. Clone This Repository

Clone this repository to your VM:

```bash
git clone https://github.com/yourusername/rag-gemini-chatbot.git
cd rag-gemini-chatbot
```

### 3. Run the Setup Script

Make the setup script executable and run it:

```bash
chmod +x setup.sh
./setup.sh
```

The script will:
- Install Docker and Docker Compose if not already installed
- Ask for your Google API key
- Ask for your company documents GitHub repository URL
- Build and start the Docker container

### 4. Manual Setup (if not using the script)

If you prefer to set things up manually:

1. Create a `.env` file with the following variables:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   GITHUB_DOCS_REPO=https://github.com/yourusername/company-docs.git
   # Optional: for private repositories
   GITHUB_TOKEN=your_github_personal_access_token
   ```

2. Update the `docker-compose.yml` file with your GitHub repository URL.

3. Build and start the container:
   ```bash
   docker-compose up -d
   ```

## Accessing the Chatbot API

Once the container is running, the API will be accessible at:

```
http://your_vm_ip:8080/api/chat/start
```

Make sure port 8080 is open in your VM's firewall/security group.

## API Endpoints

### Start a new chat session
- **URL**: `/api/chat/start`
- **Method**: `POST`
- **Response**: 
  ```json
  {
    "session_id": "uuid",
    "message": "Chat session started successfully"
  }
  ```

### Send a message
- **URL**: `/api/chat/{session_id}`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "query": "Your question here"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "response": "Chatbot response",
    "timestamp": "datetime"
  }
  ```

### End a chat session
- **URL**: `/api/chat/{session_id}`
- **Method**: `DELETE`
- **Response**:
  ```json
  {
    "message": "Session ended successfully",
    "session_id": "uuid"
  }
  ```

### Get conversation history
- **URL**: `/api/chat/{session_id}/history`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "history": [
      {
        "timestamp": "datetime",
        "role": "user|assistant",
        "content": "message"
      }
    ]
  }
  ```

## Updating Company Documents

To update your company documents:

1. Push the updated files to your GitHub repository.
2. Restart the container to pull the latest changes:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Troubleshooting

- **Container not starting**: Check Docker logs with `docker-compose logs`
- **API not accessible**: Make sure port 8080 is open in your VM's firewall
- **Document processing issues**: Check the logs for errors related to document loading

## Security Considerations

- The API is exposed to the internet, so ensure your VM has proper security configurations
- Consider adding API authentication if needed for production use
- If using a private GitHub repository, ensure your GitHub token has limited permissions