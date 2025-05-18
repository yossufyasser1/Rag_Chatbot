#!/usr/bin/env python3

"""
Data Sync Client Example
========================

This script demonstrates how to use the Data Sync API to synchronize
conversation data with an external system for data analysis.
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_sync_client.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data_sync_client")

class DataSyncClient:
    """Client for syncing data from the RAG Chatbot API."""
    
    def __init__(self, api_url: str, sync_interval: int = 300):
        """
        Initialize the data sync client.
        
        Args:
            api_url: Base URL of the Data Sync API
            sync_interval: Interval in seconds between sync operations
        """
        self.api_url = api_url.rstrip('/')
        self.sync_interval = sync_interval
        self.last_sync_time = None
        self.sync_file = "last_sync.json"
        
        # Load last sync time if available
        self._load_sync_state()
    
    def _load_sync_state(self) -> None:
        """Load last synchronization state from file."""
        try:
            if os.path.exists(self.sync_file):
                with open(self.sync_file, 'r') as f:
                    data = json.load(f)
                    self.last_sync_time = data.get('last_sync_time')
                    logger.info(f"Loaded last sync time: {self.last_sync_time}")
            else:
                logger.info("No previous sync state found. Starting fresh.")
        except Exception as e:
            logger.error(f"Error loading sync state: {e}")
    
    def _save_sync_state(self) -> None:
        """Save current synchronization state to file."""
        try:
            with open(self.sync_file, 'w') as f:
                json.dump({
                    'last_sync_time': self.last_sync_time,
                    'updated_at': datetime.now().isoformat()
                }, f)
            logger.info(f"Saved sync state with time: {self.last_sync_time}")
        except Exception as e:
            logger.error(f"Error saving sync state: {e}")
    
    def check_connection(self) -> bool:
        """Check if the Data Sync API is available."""
        try:
            response = requests.get(f"{self.api_url}/api/sync/health", timeout=10)
            if response.status_code == 200:
                logger.info("Successfully connected to Data Sync API")
                return True
            else:
                logger.error(f"API connection failed with status code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to API: {e}")
            return False
    
    def sync_data(self) -> Dict[str, Any]:
        """
        Synchronize data since the last sync time.
        
        Returns:
            Dictionary containing sync results
        """
        try:
            # Use last_sync_time if available, otherwise default to 24 hours ago
            since_param = {}
            if self.last_sync_time:
                since_param = {'since': self.last_sync_time}
            
            # Get delta updates
            response = requests.get(
                f"{self.api_url}/api/sync/delta",
                params=since_param,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Sync failed with status code: {response.status_code}")
                return {'success': False, 'error': f"HTTP error: {response.status_code}"}
            
            # Process the data
            data = response.json()
            conversations = data.get('conversations', [])
            messages = data.get('messages', [])
            
            logger.info(f"Synced {len(conversations)} conversations and {len(messages)} messages")
            
            # Update last sync time
            self.last_sync_time = datetime.now().isoformat()
            self._save_sync_state()
            
            # Here you would typically process and store the data in your own system
            # For example:
            # - Insert into a database
            # - Send to another API
            # - Process for analytics
            
            return {
                'success': True,
                'conversations_synced': len(conversations),
                'messages_synced': len(messages),
                'sync_time': self.last_sync_time
            }
            
        except Exception as e:
            logger.error(f"Error during sync: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics from the API.
        
        Returns:
            Dictionary containing database statistics
        """
        try:
            response = requests.get(f"{self.api_url}/api/sync/statistics", timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to get statistics: {response.status_code}")
                return {'success': False, 'error': f"HTTP error: {response.status_code}"}
            
            stats = response.json()
            logger.info(f"Retrieved statistics: {len(stats)} metrics")
            return {'success': True, 'statistics': stats}
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_continuous_sync(self) -> None:
        """Run a continuous sync process at the specified interval."""
        logger.info(f"Starting continuous sync with interval: {self.sync_interval} seconds")
        
        try:
            while True:
                if not self.check_connection():
                    logger.error("API connection failed. Retrying in 30 seconds...")
                    time.sleep(30)
                    continue
                
                logger.info("Starting sync operation...")
                result = self.sync_data()
                if result.get('success'):
                    logger.info(f"Sync completed successfully. Next sync in {self.sync_interval} seconds.")
                else:
                    logger.error(f"Sync failed: {result.get('error')}. Retrying in {self.sync_interval} seconds.")
                
                # Sleep until next sync
                time.sleep(self.sync_interval)
                
        except KeyboardInterrupt:
            logger.info("Sync process interrupted by user. Exiting.")
        except Exception as e:
            logger.error(f"Unexpected error in sync process: {e}")

def process_synced_data_example(conversations, messages):
    """
    Example function to process synced data.
    
    This is where you would implement your own data processing logic.
    For example, inserting into your data warehouse, generating reports, etc.
    
    Args:
        conversations: List of conversation data
        messages: List of message data
    """
    print(f"Processing {len(conversations)} conversations and {len(messages)} messages")
    
    # Example: Calculate simple statistics
    user_msgs = [m for m in messages if m.get('role') == 'user']
    assistant_msgs = [m for m in messages if m.get('role') == 'assistant']
    
    print(f"User messages: {len(user_msgs)}")
    print(f"Assistant messages: {len(assistant_msgs)}")
    
    # Example: Process conversation lengths
    for conv in conversations:
        conv_messages = [m for m in messages if m.get('conversation_id') == conv.get('id')]
        print(f"Conversation {conv.get('id')} has {len(conv_messages)} messages")

def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Data Sync Client Example')
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8082',
        help='Base URL of the Data Sync API'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Sync interval in seconds'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run in continuous sync mode'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Retrieve and display database statistics'
    )
    
    args = parser.parse_args()
    
    # Create client
    client = DataSyncClient(args.api_url, args.interval)
    
    # Check connection
    if not client.check_connection():
        logger.error("Failed to connect to the Data Sync API. Exiting.")
        sys.exit(1)
    
    # Get statistics if requested
    if args.stats:
        stats_result = client.get_statistics()
        if stats_result.get('success'):
            stats = stats_result.get('statistics', {})
            print("\nDatabase Statistics:")
            print("=====================")
            print(f"Total conversations: {stats.get('conversation_count', 'N/A')}")
            print(f"Total messages: {stats.get('message_count', 'N/A')}")
            print(f"Average messages per conversation: {stats.get('avg_messages_per_conversation', 'N/A')}")
            print("\nMessage distribution by role:")
            for role, count in stats.get('role_counts', {}).items():
                print(f"  - {role}: {count}")
            print("\nTime range:")
            print(f"  - Earliest: {stats.get('earliest_conversation', 'N/A')}")
            print(f"  - Latest: {stats.get('latest_conversation', 'N/A')}")
        else:
            print(f"Error retrieving statistics: {stats_result.get('error')}")
    
    # Run sync
    if args.continuous:
        client.run_continuous_sync()
    else:
        print("\nRunning one-time sync...")
        result = client.sync_data()
        if result.get('success'):
            print(f"Sync completed successfully!")
            print(f"Synced {result.get('conversations_synced')} conversations and {result.get('messages_synced')} messages")
        else:
            print(f"Sync failed: {result.get('error')}")

if __name__ == "__main__":
    main() 