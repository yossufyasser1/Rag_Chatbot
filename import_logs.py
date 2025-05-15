#!/usr/bin/env python3
"""
Import JSON logs to SQLite database
==================================

This script imports existing JSON conversation logs into the SQLite database.
"""

import os
import json
import glob
import argparse
import logging
import sqlite3
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("import_logs")

def create_database_structure(db_path):
    """Create database tables if they don't exist."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    
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
    
    conn.commit()
    logger.info("Database structure created or verified.")
    return conn

def import_json_log(db_conn, json_file):
    """Import a single JSON log file into the database."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        session_id = data.get("session_id", os.path.basename(json_file))
        start_time = data.get("start_time", data["messages"][0]["timestamp"] if data["messages"] else None)
        end_time = data.get("end_time", None)
        
        if not start_time:
            logger.warning(f"No start time found in {json_file}, skipping.")
            return False
        
        cursor = db_conn.cursor()
        
        # Check if this conversation already exists
        cursor.execute("SELECT id FROM conversations WHERE session_id = ?", (session_id,))
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"Conversation {session_id} already exists in database, skipping.")
            return False
        
        # Insert conversation
        cursor.execute(
            "INSERT INTO conversations (session_id, start_time, end_time) VALUES (?, ?, ?)",
            (session_id, start_time, end_time)
        )
        conversation_id = cursor.lastrowid
        
        # Insert messages
        for message in data["messages"]:
            timestamp = message.get("timestamp", start_time)
            role = message.get("role", "unknown")
            content = message.get("content", "")
            
            cursor.execute(
                "INSERT INTO messages (conversation_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
                (conversation_id, timestamp, role, content)
            )
        
        db_conn.commit()
        logger.info(f"Successfully imported {json_file} with {len(data['messages'])} messages.")
        return True
    
    except Exception as e:
        logger.error(f"Error importing {json_file}: {e}")
        db_conn.rollback()
        return False

def main():
    parser = argparse.ArgumentParser(description="Import JSON conversation logs to SQLite database")
    parser.add_argument("--logs-dir", type=str, default="conversation_logs", help="Directory containing JSON log files")
    parser.add_argument("--db-path", type=str, default="conversations.db", help="Path to SQLite database file")
    args = parser.parse_args()
    
    logs_dir = os.path.abspath(args.logs_dir)
    db_path = os.path.abspath(args.db_path)
    
    if not os.path.exists(logs_dir):
        logger.error(f"Logs directory not found: {logs_dir}")
        return
    
    # Create or connect to database
    conn = create_database_structure(db_path)
    
    # Find all JSON log files
    json_files = glob.glob(os.path.join(logs_dir, "*.json"))
    logger.info(f"Found {len(json_files)} JSON log files.")
    
    # Import each file
    success_count = 0
    for json_file in json_files:
        if import_json_log(conn, json_file):
            success_count += 1
    
    logger.info(f"Import complete. Successfully imported {success_count} of {len(json_files)} files.")
    conn.close()

if __name__ == "__main__":
    main() 