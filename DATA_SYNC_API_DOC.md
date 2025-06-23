# Data Sync API Documentation

This document describes the REST API endpoints for the Data Sync API of the RAG Chatbot.

## Base URL

```
http://<host>:5001
```

---

## Endpoints

### 1. Health Check

**GET** `/api/sync/health`

- **Description:** Check if the Data Sync API is running and see the database path.
- **Response:**
  - `200 OK`: `{ "status": "healthy", "database": <db_path> }`

---

### 2. Get Recent Conversations

**GET** `/api/sync/conversations/recent?hours=<int>`

- **Description:** Retrieve conversations from the last N hours (default: 24).
- **Query Parameters:**
  - `hours` (optional, int): Number of hours to look back (default: 24)
- **Response:**
  - `200 OK`: `{ "conversations": [...], "count": <int>, "period_hours": <int>, "timestamp": <string> }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

### 3. Get Messages for a Conversation

**GET** `/api/sync/conversations/<conversation_id>/messages`

- **Description:** Retrieve all messages for a specific conversation.
- **Response:**
  - `200 OK`: `{ "conversation_id": <int>, "messages": [...], "count": <int>, "timestamp": <string> }`
  - `404 Not Found`: `{ "error": "No messages found for this conversation ID", "conversation_id": <int> }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

### 4. Get Delta Updates

**GET** `/api/sync/delta?since=<iso_datetime>`

- **Description:** Retrieve all conversations and messages created or updated since a specific ISO datetime (default: 24 hours ago).
- **Query Parameters:**
  - `since` (optional, string): ISO format datetime (e.g., `2024-06-23T12:00:00`)
- **Response:**
  - `200 OK`: `{ "since": <string>, "conversations": [...], "messages": [...], "conversation_count": <int>, "message_count": <int>, "timestamp": <string> }`
  - `400 Bad Request`: `{ "error": "Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS.mmmmmm)." }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

### 5. Export Full Database

**GET** `/api/sync/export`

- **Description:** Export all conversations and messages in the database.
- **Response:**
  - `200 OK`: `{ "conversations": [...], "messages": [...], "conversation_count": <int>, "message_count": <int>, "export_timestamp": <string> }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

### 6. Get Database Statistics

**GET** `/api/sync/statistics`

- **Description:** Get statistics about the database (counts, averages, time range, etc.).
- **Response:**
  - `200 OK`: `{ "conversation_count": <int>, "message_count": <int>, "role_counts": {...}, "avg_messages_per_conversation": <float>, "earliest_conversation": <string>, "latest_conversation": <string>, "timestamp": <string> }`
  - `500 Internal Server Error`: `{ "error": ..., "details": ... }`

---

## Error Handling
- All endpoints may return `500 Internal Server Error` with details in case of unexpected failures.
- Error responses include an `error` field and may include a `details` field for debugging.

## Notes
- All requests and responses use JSON.
- The database path is configurable via the `DB_PATH` environment variable.
