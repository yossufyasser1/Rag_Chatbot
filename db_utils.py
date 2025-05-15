#!/usr/bin/env python3
"""
Database utilities for the RAG Chatbot
======================================

This module provides database functionality for storing conversation logs
in SQLite database.
"""

import os
import logging
import sqlite3
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("db_utils")

class ConversationLogger:
    """Handles conversation log storage in SQLite."""
    
    def __init__(
        self,
        db_path: Optional[str] = None
    ):
        """
        Initialize database connection for conversation logging.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "conversations.db"
        )
        
        self.connection = None
        self.lock = threading.Lock()  # Add lock for thread safety
        self._init_sqlite()
    
    def _init_sqlite(self) -> None:
        """Initialize SQLite connection and ensure tables exist."""
        try:
            # Use check_same_thread=False to allow using the connection across threads
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            logger.info(f"Successfully connected to SQLite database at {self.db_path}")
            
            # Create tables if they don't exist
            self._create_tables()
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        with self.lock:  # Use lock for thread-safety
            cursor = self.connection.cursor()
            
            # Create conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    timestamp TIMESTAMP NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            
            self.connection.commit()
            logger.info("Database tables created or already exist")
    
    def start_conversation(self, session_id: str) -> int:
        """
        Start a new conversation and return its ID.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Conversation ID
        """
        start_time = datetime.now()
        
        try:
            with self.lock:  # Use lock for thread-safety
                cursor = self.connection.cursor()
                cursor.execute(
                    "INSERT INTO conversations (session_id, start_time) VALUES (?, ?)",
                    (session_id, start_time)
                )
                self.connection.commit()
                conversation_id = cursor.lastrowid
                return conversation_id
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            return -1
    
    def log_message(self, conversation_id: int, role: str, content: str) -> bool:
        """
        Log a message in the conversation.
        
        Args:
            conversation_id: ID of the conversation
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            True if successful, False otherwise
        """
        timestamp = datetime.now()
        
        try:
            with self.lock:  # Use lock for thread-safety
                cursor = self.connection.cursor()
                cursor.execute(
                    "INSERT INTO messages (conversation_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
                    (conversation_id, timestamp, role, content)
                )
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
            return False
    
    def end_conversation(self, conversation_id: int) -> bool:
        """
        End a conversation by setting its end time.
        
        Args:
            conversation_id: ID of the conversation to end
            
        Returns:
            True if successful, False otherwise
        """
        end_time = datetime.now()
        
        try:
            with self.lock:  # Use lock for thread-safety
                cursor = self.connection.cursor()
                cursor.execute(
                    "UPDATE conversations SET end_time = ? WHERE id = ?",
                    (end_time, conversation_id)
                )
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to end conversation: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: int) -> List[Dict[str, Any]]:
        """
        Get the full history of a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List of message dictionaries
        """
        try:
            with self.lock:  # Use lock for thread-safety
                messages = []
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT id, conversation_id, timestamp, role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp",
                    (conversation_id,)
                )
                rows = cursor.fetchall()
                
                for row in rows:
                    messages.append({
                        "id": row[0],
                        "conversation_id": row[1],
                        "timestamp": row[2],
                        "role": row[3],
                        "content": row[4]
                    })
                
                return messages
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def close(self) -> None:
        """Close database connection if open."""
        with self.lock:  # Use lock for thread-safety
            if self.connection:
                self.connection.close()
                logger.info("Database connection closed") 