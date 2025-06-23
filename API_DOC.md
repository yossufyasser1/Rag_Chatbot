# RAG Gemini Chatbot API Documentation

This document describes the REST API endpoints for the RAG Gemini Chatbot Flask server.

## Base URL

```
http://<host>:5000
```

---

## Endpoints

### 1. Health Check

**GET** `/health`

- **Description:** Check if the API is running.
- **Response:**
  - `200 OK`: `{ "status": "healthy" }`

---

### 2. Start a New Chat Session

**POST** `/api/chat/start`

- **Description:** Start a new chat session and get a session ID.
- **Response:**
  - `201 Created`: `{ "session_id": <string>, "message": "Chat session started successfully" }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

### 3. Send a Message to the Chatbot

**POST** `/api/chat/<session_id>`

- **Description:** Send a message to the chatbot in a specific session.
- **Request Body:**
  - JSON: `{ "query": <string> }`
- **Response:**
  - `200 OK`: `{ "session_id": <string>, "response": <string>, "timestamp": <string> }`
  - `400 Bad Request`: `{ "error": "Bad request", "message": "Query parameter is required" }`
  - `404 Not Found`: `{ "success": false, "error": "Session not found" }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

### 4. End a Chat Session

**DELETE** `/api/chat/<session_id>`

- **Description:** End a chat session and save the conversation log.
- **Response:**
  - `200 OK`: `{ "message": "Session ended successfully", "session_id": <string> }`
  - `404 Not Found`: `{ "error": "Session not found" }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

### 5. Get Conversation History

**GET** `/api/chat/<session_id>/history`

- **Description:** Retrieve the conversation history for a session.
- **Response:**
  - `200 OK`: `{ "session_id": <string>, "history": [ ... ] }`
  - `404 Not Found`: `{ "error": "Session not found" }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

## Error Handling
- All endpoints may return `500 Internal Server Error` with details in case of unexpected failures.
- Error responses include an `error` field and may include a `details` field for debugging.

## Notes
- All requests and responses use JSON.
- The `session_id` must be provided for all chat and history endpoints after session creation.
- Sessions are automatically cleaned up after 30 minutes of inactivity.
