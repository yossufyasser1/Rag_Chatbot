#!/usr/bin/env python3

"""
Import/Export Utility for RAG Chatbot Database
==============================================

This script provides functions to:
1. Import JSON data from the /api/sync/export endpoint back into the SQLite database
2. Export data directly from the database to JSON

Usage:
  python import_export_data.py --import-file export_data.json --db-path conversations.db
  python import_export_data.py --import-url http://localhost:8082/api/sync/export --db-path conversations.db
  python import_export_data.py --export-file export_data.json --db-path conversations.db
"""

import os
import json
import sqlite3
import argparse
import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("import_export_data")

def setup_database(db_path: str) -> sqlite3.Connection:
    """
    Set up the SQLite database with required tables if they don't exist.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        SQLite database connection
    """
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    
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
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
    
    connection.commit()
    return connection

def fetch_data_from_api(api_url: str) -> Dict[str, Any]:
    """
    Fetch data from the API export endpoint.
    
    Args:
        api_url: URL of the export API endpoint
        
    Returns:
        Dictionary containing conversations and messages data
    """
    try:
        logger.info(f"Fetching data from {api_url}")
        response = requests.get(api_url, timeout=60)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched {len(data.get('conversations', []))} conversations and {len(data.get('messages', []))} messages")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch data from API: {e}")
        raise

def load_data_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing conversations and messages data
    """
    try:
        logger.info(f"Loading data from {file_path}")
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {len(data.get('conversations', []))} conversations and {len(data.get('messages', []))} messages")
        return data
    except Exception as e:
        logger.error(f"Failed to load data from file: {e}")
        raise

def import_data_to_db(data: Dict[str, Any], connection: sqlite3.Connection, replace_existing: bool = False) -> None:
    """
    Import conversations and messages data into the database.
    
    Args:
        data: Dictionary containing conversations and messages data
        connection: SQLite database connection
        replace_existing: Whether to replace existing records
    """
    cursor = connection.cursor()
    
    try:
        # Start a transaction
        connection.execute("BEGIN TRANSACTION")
        
        # Clear existing data if requested
        if replace_existing:
            logger.warning("Deleting all existing data from the database")
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM conversations")
            connection.commit()
        
        # Dictionary to map original conversation IDs to new ones
        id_mapping = {}
        
        # Import conversations
        conversations = data.get('conversations', [])
        for conv in conversations:
            # Check if conversation with this session_id already exists
            cursor.execute("SELECT id FROM conversations WHERE session_id = ?", (conv['session_id'],))
            existing = cursor.fetchone()
            
            if existing:
                logger.debug(f"Conversation with session_id {conv['session_id']} already exists with id {existing[0]}")
                id_mapping[conv['id']] = existing[0]
                continue
            
            # Insert new conversation
            cursor.execute(
                "INSERT INTO conversations (id, session_id, start_time, end_time, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    conv['id'],
                    conv['session_id'],
                    conv['start_time'],
                    conv['end_time'],
                    conv['created_at']
                )
            )
            
            # Get the ID of the newly inserted conversation
            # SQLite will use the provided ID if available
            id_mapping[conv['id']] = conv['id']
        
        # Import messages
        messages = data.get('messages', [])
        for msg in messages:
            # Map the conversation ID
            new_conv_id = id_mapping.get(msg['conversation_id'])
            if not new_conv_id:
                logger.warning(f"Skipping message {msg['id']} - conversation {msg['conversation_id']} not found")
                continue
            
            # Check if message already exists
            cursor.execute(
                "SELECT id FROM messages WHERE conversation_id = ? AND timestamp = ? AND role = ?",
                (new_conv_id, msg['timestamp'], msg['role'])
            )
            if cursor.fetchone() and not replace_existing:
                logger.debug(f"Message already exists for conversation {new_conv_id} at {msg['timestamp']}")
                continue
            
            # Insert message
            cursor.execute(
                "INSERT INTO messages (id, conversation_id, timestamp, role, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    msg['id'],
                    new_conv_id,
                    msg['timestamp'],
                    msg['role'],
                    msg['content'],
                    msg['created_at']
                )
            )
        
        # Commit the transaction
        connection.commit()
        logger.info(f"Successfully imported {len(conversations)} conversations and {len(messages)} messages")
    
    except Exception as e:
        # Rollback in case of error
        connection.rollback()
        logger.error(f"Error importing data: {e}")
        raise

def export_data_from_db(connection: sqlite3.Connection) -> Dict[str, Any]:
    """
    Export all data from the database.
    
    Args:
        connection: SQLite database connection
        
    Returns:
        Dictionary containing conversations and messages data
    """
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    try:
        # Get all conversations
        cursor.execute("SELECT * FROM conversations")
        conversations = [dict(row) for row in cursor.fetchall()]
        
        # Get all messages
        cursor.execute("SELECT * FROM messages")
        messages = [dict(row) for row in cursor.fetchall()]
        
        return {
            "conversations": conversations,
            "messages": messages,
            "export_timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Import/Export RAG Chatbot Database')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--import-file', help='JSON file to import from')
    group.add_argument('--import-url', help='API URL to import from (e.g., http://localhost:8082/api/sync/export)')
    group.add_argument('--export-file', help='JSON file to export to')
    
    parser.add_argument('--db-path', default='conversations.db', help='Path to the SQLite database file')
    parser.add_argument('--replace', action='store_true', help='Replace existing data in the database')
    
    args = parser.parse_args()
    
    try:
        # Set up the database
        logger.info(f"Using database at {args.db_path}")
        connection = setup_database(args.db_path)
        
        # Import or export based on arguments
        if args.import_file:
            data = load_data_from_file(args.import_file)
            import_data_to_db(data, connection, args.replace)
            
        elif args.import_url:
            data = fetch_data_from_api(args.import_url)
            import_data_to_db(data, connection, args.replace)
            
        elif args.export_file:
            data = export_data_from_db(connection)
            with open(args.export_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported {len(data['conversations'])} conversations and {len(data['messages'])} messages to {args.export_file}")
        
        connection.close()
        logger.info("Operation completed successfully")
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise

if __name__ == "__main__":
    main() 