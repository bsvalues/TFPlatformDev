import os
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RedisBus:
    """
    Redis-based event bus for inter-service communication
    """
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        channel: str = "terrafusion_events"
    ):
        """
        Initialize the Redis event bus
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            channel: Redis channel for pub/sub
        """
        self.host = host
        self.port = port
        self.password = password
        self.channel = channel
        self.redis_client = None
        self.pubsub = None
    
    async def connect(self):
        """
        Connect to Redis
        """
        try:
            logger.info(f"Connecting to Redis at {self.host}:{self.port}")
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Create PubSub
            self.pubsub = self.redis_client.pubsub()
            
            logger.info("Connected to Redis successfully")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            return False
    
    async def disconnect(self):
        """
        Disconnect from Redis
        """
        try:
            if self.pubsub:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
            
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info("Disconnected from Redis")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {str(e)}")
            return False
    
    async def publish(self, message: Dict[str, Any]) -> bool:
        """
        Publish a message to the event bus
        
        Args:
            message: Message to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                if not await self.connect():
                    return False
            
            # Convert message to JSON
            message_str = json.dumps(message)
            
            # Publish message
            await self.redis_client.publish(self.channel, message_str)
            
            return True
        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")
            return False
    
    async def subscribe(self) -> AsyncGenerator[str, None]:
        """
        Subscribe to messages from the event bus
        
        Yields:
            Messages from the event bus
        """
        try:
            if not self.redis_client:
                if not await self.connect():
                    raise ConnectionError("Failed to connect to Redis")
            
            # Subscribe to channel
            await self.pubsub.subscribe(self.channel)
            
            # Listen for messages
            while True:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message:
                    # Yield message data
                    yield message["data"]
                
                # Sleep briefly to prevent tight loop
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Error in subscribe: {str(e)}")
            raise
    
    async def set_key(self, key: str, value: str, expiration: Optional[int] = None) -> bool:
        """
        Set a key in Redis
        
        Args:
            key: Key to set
            value: Value to set
            expiration: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                if not await self.connect():
                    return False
            
            # Set key
            await self.redis_client.set(key, value)
            
            # Set expiration if provided
            if expiration:
                await self.redis_client.expire(key, expiration)
            
            return True
        except Exception as e:
            logger.error(f"Error setting key: {str(e)}")
            return False
    
    async def get_key(self, key: str) -> Optional[str]:
        """
        Get a key from Redis
        
        Args:
            key: Key to get
            
        Returns:
            Value if found, None otherwise
        """
        try:
            if not self.redis_client:
                if not await self.connect():
                    return None
            
            # Get key
            value = await self.redis_client.get(key)
            
            return value
        except Exception as e:
            logger.error(f"Error getting key: {str(e)}")
            return None
    
    async def delete_key(self, key: str) -> bool:
        """
        Delete a key from Redis
        
        Args:
            key: Key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                if not await self.connect():
                    return False
            
            # Delete key
            await self.redis_client.delete(key)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting key: {str(e)}")
            return False
