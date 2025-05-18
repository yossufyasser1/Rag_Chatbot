#!/usr/bin/env python3

"""
Data Sync API for RAG Chatbot
=============================

This module provides API endpoints for external systems to access 
and synchronize with the conversation database. It allows data analysis
tools to fetch the latest conversation data through HTTP endpoints.
"""

import os
import json
import logging
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_sync_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data_sync_api")

# Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database configuration
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversations.db"))

# Lock for thread-safe database access
db_lock = threading.Lock()

class DatabaseAccessor:
    """Provides thread-safe access to the SQLite database."""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection for conversation access.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self.lock = threading.Lock()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        if self.connection is None:
            # Use check_same_thread=False to allow using the connection across threads
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            # Set to return rows as dictionaries
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def close(self):
        """Close the database connection."""
        with self.lock:
            if self.connection:
                self.connection.close()
                self.connection = None
    
    def get_recent_conversations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get conversations from the past specified hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of conversation dictionaries
        """
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Calculate the timestamp for the specified hours ago
                time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                cursor.execute("""
                    SELECT id, session_id, start_time, end_time, created_at
                    FROM conversations
                    WHERE start_time >= ?
                    ORDER BY start_time DESC
                """, (time_threshold,))
                
                conversations = []
                for row in cursor.fetchall():
                    conversations.append(dict(row))
                
                return conversations
            except Exception as e:
                logger.error(f"Error getting recent conversations: {e}")
                return []
    
    def get_conversation_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """
        Get all messages for a specific conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List of message dictionaries
        """
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, conversation_id, timestamp, role, content, created_at
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY timestamp
                """, (conversation_id,))
                
                messages = []
                for row in cursor.fetchall():
                    messages.append(dict(row))
                
                return messages
            except Exception as e:
                logger.error(f"Error getting conversation messages: {e}")
                return []
    
    def get_conversations_since(self, last_sync_time: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Get conversations and messages created or updated since the specified time.
        
        Args:
            last_sync_time: ISO format timestamp of last synchronization
            
        Returns:
            Tuple of (conversations, messages) lists
        """
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Get conversations created or updated since last_sync_time
                cursor.execute("""
                    SELECT id, session_id, start_time, end_time, created_at
                    FROM conversations
                    WHERE created_at >= ? OR (end_time IS NOT NULL AND end_time >= ?)
                    ORDER BY start_time DESC
                """, (last_sync_time, last_sync_time))
                
                conversations = []
                conversation_ids = []
                for row in cursor.fetchall():
                    conv_dict = dict(row)
                    conversations.append(conv_dict)
                    conversation_ids.append(conv_dict["id"])
                
                # Get messages for these conversations and any created since last_sync_time
                messages = []
                if conversation_ids:
                    # Convert list to format for SQL IN clause
                    conversation_ids_str = ','.join('?' for _ in conversation_ids)
                    cursor.execute(f"""
                        SELECT id, conversation_id, timestamp, role, content, created_at
                        FROM messages
                        WHERE created_at >= ? OR conversation_id IN ({conversation_ids_str})
                        ORDER BY timestamp
                    """, [last_sync_time] + conversation_ids)
                    
                    for row in cursor.fetchall():
                        messages.append(dict(row))
                else:
                    # If no conversations match, just get messages created since last_sync_time
                    cursor.execute("""
                        SELECT id, conversation_id, timestamp, role, content, created_at
                        FROM messages
                        WHERE created_at >= ?
                        ORDER BY timestamp
                    """, (last_sync_time,))
                    
                    for row in cursor.fetchall():
                        messages.append(dict(row))
                
                return conversations, messages
            except Exception as e:
                logger.error(f"Error getting data since {last_sync_time}: {e}")
                return [], []

# Initialize database accessor
db_accessor = DatabaseAccessor(DB_PATH)

@app.route('/api/sync/health')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "database": DB_PATH}), 200

@app.route('/api/sync/conversations/recent', methods=['GET'])
def get_recent_conversations():
    """Get recent conversations."""
    try:
        # Get hours parameter with default of 24
        hours = request.args.get('hours', default=24, type=int)
        
        # Get recent conversations
        conversations = db_accessor.get_recent_conversations(hours)
        
        return jsonify({
            "conversations": conversations,
            "count": len(conversations),
            "period_hours": hours,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in recent conversations endpoint: {e}")
        return jsonify({
            "error": "Failed to retrieve recent conversations",
            "details": str(e)
        }), 500

@app.route('/api/sync/conversations/<int:conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    """Get messages for a specific conversation."""
    try:
        # Get messages for conversation
        messages = db_accessor.get_conversation_messages(conversation_id)
        
        if not messages:
            return jsonify({
                "error": "No messages found for this conversation ID",
                "conversation_id": conversation_id
            }), 404
        
        return jsonify({
            "conversation_id": conversation_id,
            "messages": messages,
            "count": len(messages),
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        return jsonify({
            "error": "Failed to retrieve conversation messages",
            "details": str(e)
        }), 500

@app.route('/api/sync/delta', methods=['GET'])
def get_delta_updates():
    """Get all conversations and messages created or updated since a specific time."""
    try:
        # Get last_sync_time parameter, defaulting to 24 hours ago
        default_time = (datetime.now() - timedelta(hours=24)).isoformat()
        last_sync_time = request.args.get('since', default=default_time)
        
        # Validate ISO format
        try:
            datetime.fromisoformat(last_sync_time)
        except ValueError:
            return jsonify({
                "error": "Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS.mmmmmm)."
            }), 400
        
        # Get delta updates
        conversations, messages = db_accessor.get_conversations_since(last_sync_time)
        
        return jsonify({
            "since": last_sync_time,
            "conversations": conversations,
            "messages": messages,
            "conversation_count": len(conversations),
            "message_count": len(messages),
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error getting delta updates: {e}")
        return jsonify({
            "error": "Failed to retrieve delta updates",
            "details": str(e)
        }), 500

@app.route('/api/sync/export', methods=['GET'])
def export_full_database():
    """Export the entire database content."""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            
            # Get all conversations
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations ORDER BY start_time DESC")
            conversations = [dict(row) for row in cursor.fetchall()]
            
            # Get all messages
            cursor.execute("SELECT * FROM messages ORDER BY conversation_id, timestamp")
            messages = [dict(row) for row in cursor.fetchall()]
            
            # Close connection
            conn.close()
        
        return jsonify({
            "conversations": conversations,
            "messages": messages,
            "conversation_count": len(conversations),
            "message_count": len(messages),
            "export_timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error exporting database: {e}")
        return jsonify({
            "error": "Failed to export database",
            "details": str(e)
        }), 500

@app.route('/api/sync/statistics', methods=['GET'])
def get_statistics():
    """Get database statistics."""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get conversation count
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conversation_count = cursor.fetchone()[0]
            
            # Get message count
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            # Get user/assistant message counts
            cursor.execute("SELECT role, COUNT(*) FROM messages GROUP BY role")
            role_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get average messages per conversation
            cursor.execute("""
                SELECT AVG(message_count) 
                FROM (
                    SELECT conversation_id, COUNT(*) as message_count 
                    FROM messages 
                    GROUP BY conversation_id
                )
            """)
            avg_messages = cursor.fetchone()[0]
            
            # Get time range of data
            cursor.execute("SELECT MIN(start_time), MAX(start_time) FROM conversations")
            min_time, max_time = cursor.fetchone()
            
            # Close connection
            conn.close()
        
        return jsonify({
            "conversation_count": conversation_count,
            "message_count": message_count,
            "role_counts": role_counts,
            "avg_messages_per_conversation": avg_messages,
            "earliest_conversation": min_time,
            "latest_conversation": max_time,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            "error": "Failed to retrieve statistics",
            "details": str(e)
        }), 500

def cleanup_resources():
    """Clean up resources on shutdown."""
    db_accessor.close()
    logger.info("Database connection closed")

if __name__ == "__main__":
    try:
        # Set up port (default 5001 to not conflict with the main chatbot service)
        port = int(os.environ.get("DATA_SYNC_PORT", 5001))
        
        # Start the Flask application
        logger.info(f"Starting Data Sync API on port {port}")
        app.run(host='0.0.0.0', port=port)
    finally:
        cleanup_resources() 