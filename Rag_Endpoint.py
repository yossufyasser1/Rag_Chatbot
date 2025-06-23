#!/usr/bin/env python3

"""
Flask API for RAG Gemini Chatbot
================================

This script implements a Flask API for the RAG Gemini Chatbot, allowing
multiple users to interact with the chatbot simultaneously through HTTP endpoints.

Requirements:
- Python 3.8+
- Google API key for Gemini
- Company documentation (PDF, DOCX, TXT files)
- Flask and related dependencies
- SQLite database for conversation logging
"""

import os
import uuid
import json
import logging
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# Import the RAG Gemini Chatbot
from RAG_Chatbot_final import RAGGeminiChatbot

# Load environment variables
load_dotenv()

# Configure logging with more detailed information
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("rag_gemini_flask_api")

# Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    # Fall back to hardcoded key if environment variable not set
    API_KEY = "AIzaSyDFXt1BEwo10-K-GjuOl-ZmCucj6aQwHp4"  # Replace with your actual API key
    logger.warning("Using hardcoded API key. Consider setting GOOGLE_API_KEY environment variable.")

DOCS_DIR = os.environ.get("DOCS_DIR", "Y:/projects/Qayedeny/company_docs")
MODEL_NAME = os.environ.get("MODEL_NAME", "models/gemini-2.0-flash")
CACHE_DIR = os.environ.get("CACHE_DIR", "/app/vector_db")

# Database configuration
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversations.db"))

# Ensure directories exist
os.makedirs(CACHE_DIR, exist_ok=True)

# Dictionary to store user sessions
sessions = {}
# Lock for thread-safe access to the sessions dictionary
sessions_lock = threading.Lock()

def initialize_chatbot():
    """Initialize and prepare the chatbot with documents."""
    try:
        chatbot = RAGGeminiChatbot(
            api_key=API_KEY,
            docs_dir=DOCS_DIR,
            model_name=MODEL_NAME,
            cache_dir=CACHE_DIR,
            use_db=True,
            db_path=DB_PATH
        )
        
        # Try to load existing DB first
        db_loaded = chatbot.load_existing_db()
        
        if not db_loaded:
            success = chatbot.load_documents()
            if not success:
                return None
        else:
            pass
        
        return chatbot
    except Exception as e:
        return None

# Initialize the shared vector database (only once)
master_chatbot = initialize_chatbot()
if not master_chatbot:
    exit(1)

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/chat/start', methods=['POST'])
def start_session():
    """Start a new chat session."""
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Create new chatbot for this session
        new_chatbot = RAGGeminiChatbot(
            api_key=API_KEY,
            docs_dir=DOCS_DIR,
            model_name=MODEL_NAME,
            cache_dir=CACHE_DIR,
            use_db=True,
            db_path=DB_PATH
        )
        
        # Copy vector database and embeddings from master
        if master_chatbot and master_chatbot.vector_db and master_chatbot.embeddings:
            new_chatbot.vector_db = master_chatbot.vector_db
            new_chatbot.embeddings = master_chatbot.embeddings
            
            # Store session data
            sessions[session_id] = {
                "chatbot": new_chatbot,
                "created_at": str(datetime.now()),
                "last_active": str(datetime.now())
            }
            
            return jsonify({
                "session_id": session_id,
                "message": "Chat session started successfully"
            }), 201
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error creating session: {str(e)}")
        logger.error(error_details)
        return jsonify({
            "error": "Failed to create chat session",
            "details": str(e)
        }), 500

@app.route('/api/chat/<session_id>', methods=['POST'])
def chat(session_id):
    """Process a chat message."""
    try:
        # Check if session exists in memory
        with sessions_lock:
            if session_id not in sessions:
                # Create new chatbot instance for this session
                new_chatbot = RAGGeminiChatbot(
                    api_key=API_KEY,
                    docs_dir=DOCS_DIR,
                    model_name=MODEL_NAME,
                    cache_dir=CACHE_DIR,
                    use_db=True,
                    db_path=DB_PATH
                )
                
                # Copy vector database and embeddings from master
                if master_chatbot and master_chatbot.vector_db and master_chatbot.embeddings:
                    new_chatbot.vector_db = master_chatbot.vector_db
                    new_chatbot.embeddings = master_chatbot.embeddings
                    
                    # Try to load conversation history from database
                    try:
                        history_loaded = new_chatbot.load_conversation_history(session_id)
                        if history_loaded:
                            sessions[session_id] = {
                                'chatbot': new_chatbot,
                                'last_activity': time.time()
                            }
                        else:
                            return jsonify({
                                'success': False,
                                'error': 'Session not found'
                            }), 404
                    except Exception as db_error:
                        return jsonify({
                            'success': False,
                            'error': 'Database error loading session'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': 'System not ready'
                    }), 503
        
        # Get the chatbot instance for this session
        session = sessions[session_id]
        chatbot = session["chatbot"]
        
        # Update last activity time
        session["last_active"] = str(datetime.now())
        
        # Get query from request
        data = request.json
        if not data or 'query' not in data:
            logger.warning(f"Bad request for session {session_id}: Missing query parameter")
            return jsonify({
                "error": "Bad request",
                "message": "Query parameter is required"
            }), 400
        
        query = data['query']
        
        # Process the query with better error handling
        try:
            response = chatbot.process_query(query)
            
            return jsonify({
                "session_id": session_id,
                "response": response,
                "timestamp": str(datetime.now())
            }), 200
            
        except Exception as specific_error:
            error_details = traceback.format_exc()
            logger.error(f"Error processing query for session {session_id}: {str(specific_error)}")
            logger.error(error_details)
            
            # Return more specific error information
            return jsonify({
                "error": "Query processing error",
                "details": str(specific_error),
                "session_id": session_id,
                "timestamp": str(datetime.now())
            }), 500
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        logger.error(error_details)
        return jsonify({
            "error": "Failed to process query",
            "details": str(e)
        }), 500

@app.route('/api/chat/<session_id>', methods=['DELETE'])
def end_session(session_id):
    """End a chat session."""
    try:
        logger.info(f"Request to end session: {session_id}")
        
        with sessions_lock:
            if session_id not in sessions:
                logger.warning(f"Session not found for deletion: {session_id}")
                return jsonify({
                    "error": "Session not found"
                }), 404
            
            # Get chatbot for this session and save conversation log
            chatbot = sessions[session_id]["chatbot"]
            chatbot.save_conversation_log()
            
            # Remove session
            del sessions[session_id]
            logger.info(f"Session {session_id} ended successfully")
        
        return jsonify({
            "message": "Session ended successfully",
            "session_id": session_id
        }), 200
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error ending session {session_id}: {str(e)}")
        logger.error(error_details)
        return jsonify({
            "error": "Failed to end session",
            "details": str(e)
        }), 500

@app.route('/api/chat/<session_id>/history', methods=['GET'])
def get_history(session_id):
    """Get conversation history for a session."""
    try:
        logger.info(f"Fetching history for session: {session_id}")
        
        with sessions_lock:
            if session_id not in sessions:
                logger.warning(f"Session not found for history request: {session_id}")
                return jsonify({
                    "error": "Session not found"
                }), 404
            
            # Get chatbot for this session
            chatbot = sessions[session_id]["chatbot"]
            
            # Return the conversation history
            logger.info(f"Successfully retrieved history for session {session_id}")
            return jsonify({
                "session_id": session_id,
                "history": chatbot.conversation_log
            }), 200
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error fetching history for session {session_id}: {str(e)}")
        logger.error(error_details)
        return jsonify({
            "error": "Failed to fetch conversation history",
            "details": str(e)
        }), 500

def cleanup_idle_sessions():
    """Cleanup idle sessions periodically."""
    logger.info("Starting cleanup thread for idle sessions")
    while True:
        try:
            # Sleep for 10 minutes
            time.sleep(600)
            
            current_time = datetime.now()
            sessions_to_remove = []
            
            # Find idle sessions (more than 30 minutes inactive)
            with sessions_lock:
                for session_id, session_data in sessions.items():
                    last_active = datetime.fromisoformat(session_data["last_active"])
                    if current_time - last_active > timedelta(minutes=30):
                        sessions_to_remove.append(session_id)
                
                # Remove idle sessions
                for session_id in sessions_to_remove:
                    logger.info(f"Cleaning up idle session: {session_id}")
                    try:
                        sessions[session_id]["chatbot"].save_conversation_log()
                    except Exception as save_error:
                        logger.error(f"Error saving log for session {session_id}: {str(save_error)}")
                    del sessions[session_id]
                
                if sessions_to_remove:
                    logger.info(f"Cleaned up {len(sessions_to_remove)} idle sessions")
        
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Error in cleanup thread: {str(e)}")
            logger.error(error_details)

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Shutdown signal received, saving all conversation logs...")
    
    with sessions_lock:
        for session_id, session_data in sessions.items():
            try:
                logger.info(f"Saving conversation log for session {session_id}")
                session_data["chatbot"].save_conversation_log()
            except Exception as e:
                logger.error(f"Error saving conversation log for session {session_id}: {str(e)}")
    
    logger.info("All conversation logs saved. Shutting down.")
    sys.exit(0)

if __name__ == "__main__":
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_idle_sessions, daemon=True)
    cleanup_thread.start()
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=5000)