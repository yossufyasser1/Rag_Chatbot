#!/usr/bin/env python3
"""
RAG Gemini 2.0 Chatbot for Company Documentation
================================================

This script implements a command-line Retrieval-Augmented Generation (RAG) chatbot 
using Google's Gemini 2.0 model. It processes company documentation to answer 
customer questions with context-aware responses.

Requirements:
- Python 3.8+
- Google API key for Gemini
- Company documentation (PDF, DOCX, TXT files)

Features:
- Document ingestion and chunking
- Vector embeddings for efficient retrieval
- Conversation history maintenance
- Natural language responses with context from documentation
"""

import os
import re
import sys
import glob
import time
import json
import argparse
import logging
from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Third-party libraries
try:
    import google.generativeai as genai
    from langchain_community.vectorstores import FAISS
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import (
        PyPDFLoader,
        Docx2txtLoader,
        TextLoader,
        UnstructuredMarkdownLoader
    )
    import numpy as np
except ImportError as e:
    print(f"Error: Missing required libraries. Please install with: pip install langchain langchain-community faiss-cpu google-generativeai pypdf docx2txt unstructured markdown numpy")
    print(f"Specific error: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("rag_gemini_chatbot")

class RAGGeminiChatbot:
    """RAG chatbot using Gemini 2.0 for company documentation."""
    
    def __init__(
        self, 
        api_key: str, 
        docs_dir: str,
        model_name: str = "models/gemini-2.0-flash",
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        top_k: int = 40,
        top_p: float = 0.95,
        cache_dir: str = "/home/abdelrahmanessamwork/vector_db/vector_db",
        conversation_log_dir: str = "conversation_logs"
    ):
        """
        Initialize the RAG Gemini chatbot.
        
        Args:
            api_key: Google API key for Gemini access
            docs_dir: Directory containing company documentation
            model_name: Gemini model to use
            temperature: Controls randomness in responses
            max_output_tokens: Maximum tokens in model response
            top_k: Number of highest probability tokens to consider
            top_p: Total probability mass of tokens to consider
            cache_dir: Directory to store vector database
            conversation_log_dir: Directory to store conversation logs
        """
        self.api_key = api_key
        self.docs_dir = os.path.abspath(docs_dir)
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_k = top_k
        self.top_p = top_p
        
        # Create cache directory if it doesn't exist
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Create logs directory if it doesn't exist
        self.conversation_log_dir = os.path.abspath(conversation_log_dir)
        os.makedirs(self.conversation_log_dir, exist_ok=True)
        
        # DB paths
        self.db_path = self.cache_dir
        
        # Initialize components
        self._init_genai()
        self.conversation_history = []
        self.vector_db = None
        self.embeddings = None
        self.session_id = str(uuid.uuid4())
        self.conversation_log = []
        
        # System prompts
        self.system_prompt = """
        You are a helpful customer support assistant for our company.
        Your task is to provide accurate, helpful responses based on the company documentation provided.
        
        Guidelines:
        - Answer questions based on the context provided from the company documentation
        - If the documentation doesn't cover the question, acknowledge that and offer to help with what you do know
        - Keep responses professional, concise, and focused on the question
        - Never make up information that isn't in the provided context
        - If you're unsure, say so rather than guessing
        - Be friendly and helpful throughout the conversation
        """
    
    def _init_genai(self) -> None:
        """Initialize Google Generative AI with API key."""
        genai.configure(api_key=self.api_key)
        
        # Configure safety settings to be appropriate for customer service
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
        
        # Generate model parameters
        self.generation_config = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.max_output_tokens,
        }
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
        
        # Initialize chat session
        self.chat = self.model.start_chat(history=[])
    
    def _init_embeddings(self) -> None:
        """Initialize embeddings model for vector store."""
        logger.info("Initializing embeddings model...")
        try:
            # Using Gemini's own embedding model
            self.embeddings = GoogleGenerativeAIEmbeddings(
                google_api_key=self.api_key,
                model="models/embedding-001"  # Gemini's embedding model
            )
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
    
    def _get_document_loader(self, file_path: str):
        """Get appropriate document loader based on file type."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return PyPDFLoader(file_path)
        elif ext == '.docx':
            return Docx2txtLoader(file_path)
        elif ext == '.txt':
            return TextLoader(file_path)
        elif ext == '.md':
            return UnstructuredMarkdownLoader(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}. Skipping {file_path}")
            return None
    
    def load_documents(self) -> bool:
        """
        Load documents from the specified directory and create vector embeddings.
        Returns True if successful, False otherwise.
        """
        logger.info(f"Loading documents from: {self.docs_dir}")
        
        # Check if the directory exists
        if not os.path.exists(self.docs_dir):
            logger.error(f"Document directory does not exist: {self.docs_dir}")
            return False
        
        # Get all document files
        all_files = []
        for ext in ['.pdf', '.docx', '.txt', '.md']:
            all_files.extend(glob.glob(os.path.join(self.docs_dir, f"**/*{ext}"), recursive=True))
        
        if not all_files:
            logger.error(f"No supported documents found in {self.docs_dir}")
            return False
        
        logger.info(f"Found {len(all_files)} documents to process")
        
        # Process each document
        documents = []
        for file_path in all_files:
            try:
                loader = self._get_document_loader(file_path)
                if loader:
                    logger.info(f"Loading {file_path}")
                    docs = loader.load()
                    documents.extend(docs)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        if not documents:
            logger.error("Failed to load any documents")
            return False
        
        # Split documents into chunks
        logger.info("Splitting documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} document chunks")
        
        # Initialize embeddings if needed
        if not self.embeddings:
            self._init_embeddings()
        
        # Create vector store
        logger.info("Creating vector database...")
        try:
            self.vector_db = FAISS.from_documents(chunks, self.embeddings)
            # Save for future use
            self.vector_db.save_local(self.db_path)
            logger.info(f"Vector database created and saved to {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating vector database: {e}")
            return False
    
    def load_existing_db(self) -> bool:
        """
        Load existing vector database if available.
        Returns True if successful, False otherwise.
        """
        if os.path.exists(self.db_path):
            logger.info(f"Loading existing vector database from {self.db_path}")
            try:
                # Initialize embeddings if needed
                if not self.embeddings:
                    self._init_embeddings()
                
                self.vector_db = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
                logger.info("Vector database loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Error loading vector database: {e}")
                return False
        else:
            logger.info("No existing vector database found")
            return False
    
    def search_documents(self, query: str, k: int = 5) -> List[str]:
        """
        Search for relevant document chunks based on query.
        
        Args:
            query: The user query to search for
            k: Number of results to return
            
        Returns:
            List of relevant document chunks
        """
        if not self.vector_db:
            logger.error("Vector database not initialized")
            return []
        
        try:
            results = self.vector_db.similarity_search(query, k=k)
            return [doc.page_content for doc in results]
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def build_prompt(self, query: str, relevant_docs: List[str]) -> str:
        """
        Build prompt for Gemini with relevant context.
        
        Args:
            query: User query
            relevant_docs: List of relevant document chunks
            
        Returns:
            Formatted prompt string
        """
        # Combine relevant docs into a single context string
        context = "\n\n".join(relevant_docs)
        
        # Include conversation history for context (up to last 5 turns)
        conversation_context = ""
        history_to_include = self.conversation_history[-10:-1] if len(self.conversation_history) > 1 else []
        
        if history_to_include:
            conversation_context = "Previous conversation:\n"
            for msg in history_to_include:
                role = "Customer" if msg["role"] == "user" else "Assistant"
                conversation_context += f"{role}: {msg['content']}\n"
            conversation_context += "\n"
        
        prompt = f"""
        Based on the following company documentation:
        
        {context}
        
        {conversation_context}
        Please answer the user's question:
        {query}
        
        Important guidelines:
        - Be conversational and maintain context from previous messages
        - Address the user by name if they've provided it earlier in the conversation
        - Never say you "don't have memory" or "as an AI" - you're representing the company
        - If the documentation doesn't contain information relevant to the question, 
          please say so and offer to help with related information that is available.
        """
        
        return prompt
    
    def update_conversation_history(self, role: str, content: str) -> None:
        """
        Update conversation history with new message.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        self.conversation_history.append({"role": role, "content": content})
        
        # Also update the conversation log for saving
        timestamp = datetime.now().isoformat()
        self.conversation_log.append({
            "timestamp": timestamp,
            "role": role,
            "content": content
        })
    
    def save_conversation_log(self) -> None:
        """Save conversation log to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(
            self.conversation_log_dir, 
            f"conversation_{self.session_id}_{timestamp}.json"
        )
        
        try:
            with open(log_file, 'w') as f:
                json.dump({
                    "session_id": self.session_id,
                    "start_time": self.conversation_log[0]["timestamp"] if self.conversation_log else timestamp,
                    "end_time": timestamp,
                    "messages": self.conversation_log
                }, f, indent=2)
            logger.info(f"Conversation log saved to {log_file}")
        except Exception as e:
            logger.error(f"Error saving conversation log: {e}")
    
    def process_query(self, query: str) -> str:
        """
        Process user query and generate response using RAG.
        
        Args:
            query: User query
            
        Returns:
            Assistant response
        """
        # Update conversation history with user query first
        self.update_conversation_history("user", query)
        
        # Handle generic model responses that should be caught and replaced
        if any(phrase in query.lower() for phrase in ["my name", "told you", "remember me", "i said earlier"]):
            # Search in conversation history for potential name mentions
            name = self._extract_name_from_history()
            if name:
                response = f"Yes, you mentioned your name is {name}. How can I help you today?"
                self.update_conversation_history("assistant", response)
                return response
                
        # Search for relevant document chunks
        relevant_docs = self.search_documents(query)
        
        if not relevant_docs:
            logger.warning("No relevant documents found for query")
            # Try to give a more personalized response even without docs
            if len(self.conversation_history) > 2:
                response = "I don't have specific information about that in my knowledge base. Based on our conversation, is there something else about our products or services I can help with?"
            else:
                response = "I don't have specific information about that in my knowledge base. Could you ask something else about our products or services?"
            self.update_conversation_history("assistant", response)
            return response
        
        try:
            response = "Relevant documents found, preparing to send to Gemini..."
            # Build prompt with context and query
            content = self.build_prompt(query, relevant_docs)
            response = "Prompt built, sending to Gemini model..."
            # Send to Gemini model
            gemini_response = self.chat.send_message(content)
            response = gemini_response.text
            
            # Check for generic "no memory" or "as an AI" phrases and replace them
            generic_phrases = [
                "as a language model", "as an ai", "as an assistant", 
                "i have no memory", "i don't have access", "i cannot recall", 
                "i don't have the ability to remember", "i don't have personal memory"
            ]
            
            if any(phrase in response.lower() for phrase in generic_phrases):
                # Replace with a better response
                response = "Based on our conversation, I think you're asking about information you shared earlier. Could you please remind me what specific details you're referring to, so I can better assist you?"
            
            # Update conversation history
            self.update_conversation_history("assistant", response)
            
            return response
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I'm sorry, I encountered an error while processing your request. Please try again."
    
    def _extract_name_from_history(self) -> Optional[str]:
        """Extract user name from conversation history if available."""
        # Look for name patterns in user messages
        for msg in self.conversation_history:
            if msg["role"] == "user":
                content = msg["content"].lower()
                
                # Pattern: "my name is X" or "I'm X" or "call me X"
                name_patterns = [
                    r"my name is (\w+)",
                    r"i am (\w+)",
                    r"i'm (\w+)",
                    r"call me (\w+)",
                    r"name['s]* (\w+)"
                ]
                
                for pattern in name_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        return matches[0].capitalize()
                        
        return None
    
    def chat_loop(self) -> None:
        """Run the chat loop for interactive conversations."""
        print("\n" + "="*50)
        print("Welcome to the Company Documentation Chatbot")
        print("Type 'exit', 'quit', or 'bye' to end the conversation")
        print("="*50 + "\n")
        
        while True:
            try:
                query = input("\nYou: ").strip()
                
                # Check for exit commands
                if query.lower() in ['exit', 'quit', 'bye']:
                    print("\nThank you for using our chatbot. Goodbye!")
                    self.save_conversation_log()
                    break
                
                if not query:
                    continue
                
                # Process user query
                start_time = time.time()
                response = self.process_query(query)
                end_time = time.time()
                
                # Print response with processing time
                print(f"\nAssistant: {response}")
                logger.debug(f"Response time: {end_time - start_time:.2f} seconds")
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Saving conversation log and exiting...")
                self.save_conversation_log()
                break
            except Exception as e:
                logger.error(f"Error in chat loop: {e}")
                print("\nI apologize, but I encountered an unexpected error. Let's continue our conversation.")
        
def main():
    """Main function to parse arguments and run the chatbot."""
    parser = argparse.ArgumentParser(description="RAG Gemini Chatbot for Company Documentation")
    parser.add_argument("--docs-dir", type=str,  default="Y:\\projects\\Qayedeny\\Rag_Chatbot\\company_docs", help="Directory containing company documentation")
    parser.add_argument("--api-key", type=str,help="Google API key for Gemini (or set GOOGLE_API_KEY env var)")
    parser.add_argument("--model", type=str, default="models/gemini-2.0-flash", help="Gemini model name")
    parser.add_argument("--temperature", type=float, default=0.2, help="Temperature for generation")
    parser.add_argument("--force-reload", action="store_true", help="Force reload documents even if DB exists")
    parser.add_argument("--cache-dir", type=str, default="vector_db", help="Directory to store the vector database")
    parser.add_argument("--log-dir", type=str, default="conversation_logs", help="Directory to store conversation logs")
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Google API key is required. Please provide it with --api-key or set GOOGLE_API_KEY environment variable.")
        sys.exit(1)
    
    # Create chatbot instance
    chatbot = RAGGeminiChatbot(
        api_key=api_key,
        docs_dir=args.docs_dir,
        model_name=args.model,
        temperature=args.temperature,
        cache_dir=args.cache_dir,
        conversation_log_dir=args.log_dir
    )
    
    # Load or create vector database
    db_loaded = chatbot.load_existing_db()
    
    if not db_loaded:
        success = chatbot.load_documents()
        if not success:
            print("Error: Failed to load documents or create vector database. Please check the logs.")
            sys.exit(1)
    
    # Start chat loop
    chatbot.chat_loop()

if __name__ == "__main__":
    main()