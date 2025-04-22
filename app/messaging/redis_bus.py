import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis pool
redis_pool: Optional[redis.ConnectionPool] = None

class RedisEventBus:
    """
    Event bus implementation using Redis Streams
    """
    
    def __init__(self, stream_name: str = "terrafusion_events"):
        """
        Initialize Redis event bus
        
        Args:
            stream_name: Name of the Redis stream to use
        """
        self.stream_name = stream_name
        self.consumer_group = "terrafusion_consumers"
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        self.processing_task = None
        logger.info(f"Redis event bus initialized with stream '{stream_name}'")
    
    async def connect(self) -> redis.Redis:
        """
        Get a Redis connection from the pool
        
        Returns:
            Redis connection
        """
        global redis_pool
        
        if not redis_pool:
            raise ValueError("Redis connection pool is not initialized")
            
        return redis.Redis(connection_pool=redis_pool)
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        Publish an event to the Redis stream
        
        Args:
            event_type: Type of event
            data: Event data
            
        Returns:
            ID of the published message
        """
        try:
            r = await self.connect()
            
            # Prepare message
            message = {
                "event_type": event_type,
                "data": json.dumps(data)
            }
            
            # Publish to stream
            message_id = await r.xadd(self.stream_name, message)
            logger.debug(f"Published event '{event_type}' with ID {message_id}")
            
            return message_id
        except Exception as e:
            logger.error(f"Error publishing event to Redis: {str(e)}")
            raise
    
    async def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to events of a specific type
        
        Args:
            event_type: Type of events to subscribe to
            callback: Callback function to be called when events are received
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
            
        self.subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to events of type '{event_type}'")
    
    async def start_processing(self) -> None:
        """
        Start processing events from the Redis stream
        """
        if self.running:
            return
            
        self.running = True
        
        # Create consumer group if it doesn't exist
        try:
            r = await self.connect()
            try:
                await r.xgroup_create(self.stream_name, self.consumer_group, mkstream=True)
                logger.info(f"Created consumer group '{self.consumer_group}' for stream '{self.stream_name}'")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    # Group already exists
                    pass
                else:
                    raise
                    
            # Start processing task
            self.processing_task = asyncio.create_task(self._process_events())
            logger.info("Started event processing task")
        except Exception as e:
            self.running = False
            logger.error(f"Error starting event processing: {str(e)}")
            raise
    
    async def stop_processing(self) -> None:
        """
        Stop processing events
        """
        if not self.running:
            return
            
        self.running = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            self.processing_task = None
            
        logger.info("Stopped event processing")
    
    async def _process_events(self) -> None:
        """
        Process events from the Redis stream
        """
        consumer_name = f"consumer-{os.getpid()}"
        
        try:
            while self.running:
                try:
                    r = await self.connect()
                    
                    # Read new messages from the stream
                    streams = {self.stream_name: ">"}
                    messages = await r.xreadgroup(self.consumer_group, consumer_name, streams, count=10, block=1000)
                    
                    if not messages:
                        # No messages, try again
                        continue
                        
                    # Process messages
                    for stream_name, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            try:
                                # Process message
                                event_type = fields.get(b"event_type", b"").decode("utf-8")
                                data_json = fields.get(b"data", b"{}").decode("utf-8")
                                data = json.loads(data_json)
                                
                                # Call subscribers
                                if event_type in self.subscribers:
                                    for callback in self.subscribers[event_type]:
                                        try:
                                            await callback(data)
                                        except Exception as e:
                                            logger.error(f"Error in event subscriber callback: {str(e)}")
                                
                                # Acknowledge message
                                await r.xack(self.stream_name, self.consumer_group, message_id)
                            except Exception as e:
                                logger.error(f"Error processing message: {str(e)}")
                except Exception as e:
                    logger.error(f"Error in event processing loop: {str(e)}")
                    await asyncio.sleep(1)  # Wait before retrying
        except asyncio.CancelledError:
            logger.info("Event processing task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in event processing: {str(e)}")
            self.running = False


# Global event bus instance
event_bus: Optional[RedisEventBus] = None

async def init_redis() -> RedisEventBus:
    """
    Initialize Redis connection and event bus
    
    Returns:
        Redis event bus instance
    """
    global redis_pool, event_bus
    
    try:
        # Initialize connection pool
        redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=False  # Need raw bytes for xread/xreadgroup
        )
        
        # Test connection
        r = redis.Redis(connection_pool=redis_pool)
        await r.ping()
        
        # Initialize event bus
        event_bus = RedisEventBus()
        await event_bus.start_processing()
        
        logger.info(f"Redis initialized successfully at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return event_bus
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {str(e)}")
        logger.warning("System will continue without Redis messaging")
        return None

async def get_event_bus() -> Optional[RedisEventBus]:
    """
    Get the global event bus instance
    
    Returns:
        Redis event bus instance or None if not initialized
    """
    global event_bus
    return event_bus
