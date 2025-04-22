import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType

from app.core.exceptions import MCPServerError

logger = logging.getLogger(__name__)

class RabbitMQEventBus:
    """
    Event bus implementation using RabbitMQ
    """
    
    def __init__(
        self,
        exchange_name: str = "terrafusion",
        queue_name: str = "terrafusion_events",
        routing_key: str = "terrafusion.events"
    ):
        """
        Initialize RabbitMQ event bus
        
        Args:
            exchange_name: Name of the RabbitMQ exchange
            queue_name: Name of the RabbitMQ queue
            routing_key: Default routing key for messages
        """
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        self.processing_task = None
        logger.info(f"RabbitMQ event bus initialized with exchange '{exchange_name}'")
    
    async def connect(self) -> None:
        """
        Connect to RabbitMQ server
        """
        try:
            # Get connection parameters from environment or use defaults
            host = os.environ.get("RABBITMQ_HOST", "localhost")
            port = int(os.environ.get("RABBITMQ_PORT", "5672"))
            user = os.environ.get("RABBITMQ_USER", "guest")
            password = os.environ.get("RABBITMQ_PASSWORD", "guest")
            vhost = os.environ.get("RABBITMQ_VHOST", "/")
            
            # Create connection
            connection_string = f"amqp://{user}:{password}@{host}:{port}/{vhost}"
            self.connection = await aio_pika.connect_robust(connection_string)
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare queue
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                auto_delete=False
            )
            
            logger.info(f"Connected to RabbitMQ at {host}:{port}")
        except Exception as e:
            logger.error(f"Error connecting to RabbitMQ: {str(e)}")
            raise MCPServerError(f"Failed to connect to RabbitMQ: {str(e)}")
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publish an event to the RabbitMQ exchange
        
        Args:
            event_type: Type of event
            data: Event data
        """
        try:
            if not self.exchange:
                await self.connect()
            
            # Prepare message
            message_data = {
                "event_type": event_type,
                "data": data
            }
            
            # Create message
            message = Message(
                body=json.dumps(message_data).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                headers={"event_type": event_type}
            )
            
            # Use event type as routing key suffix
            routing_key = f"{self.routing_key}.{event_type}"
            
            # Publish message
            await self.exchange.publish(message, routing_key=routing_key)
            logger.debug(f"Published event '{event_type}' with routing key {routing_key}")
        except Exception as e:
            logger.error(f"Error publishing event to RabbitMQ: {str(e)}")
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
        
        # Bind queue to exchange with routing key if connected
        if self.queue and self.exchange:
            routing_key = f"{self.routing_key}.{event_type}"
            await self.queue.bind(self.exchange, routing_key=routing_key)
            logger.debug(f"Bound queue to exchange with routing key {routing_key}")
    
    async def start_processing(self) -> None:
        """
        Start processing events from RabbitMQ
        """
        if self.running:
            return
            
        self.running = True
        
        try:
            if not self.queue:
                await self.connect()
                
            # Start consuming messages
            await self.queue.consume(self._process_message)
            logger.info("Started event processing")
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
        
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            self.exchange = None
            self.queue = None
            
        logger.info("Stopped event processing")
    
    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        """
        Process a message from RabbitMQ
        
        Args:
            message: Incoming message
        """
        async with message.process():
            try:
                # Decode message
                body = message.body.decode()
                message_data = json.loads(body)
                
                event_type = message_data.get("event_type")
                data = message_data.get("data", {})
                
                # Call subscribers
                if event_type in self.subscribers:
                    for callback in self.subscribers[event_type]:
                        try:
                            await callback(data)
                        except Exception as e:
                            logger.error(f"Error in event subscriber callback: {str(e)}")
                
                logger.debug(f"Processed message of type '{event_type}'")
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")


# Global event bus instance
event_bus: Optional[RabbitMQEventBus] = None

async def init_rabbitmq() -> RabbitMQEventBus:
    """
    Initialize RabbitMQ connection and event bus
    
    Returns:
        RabbitMQ event bus instance
    """
    global event_bus
    
    try:
        # Initialize event bus
        event_bus = RabbitMQEventBus()
        await event_bus.connect()
        await event_bus.start_processing()
        
        logger.info("RabbitMQ initialized successfully")
        return event_bus
    except Exception as e:
        logger.error(f"Failed to initialize RabbitMQ: {str(e)}")
        logger.warning("System will continue without RabbitMQ messaging")
        return None

async def get_event_bus() -> Optional[RabbitMQEventBus]:
    """
    Get the global event bus instance
    
    Returns:
        RabbitMQ event bus instance or None if not initialized
    """
    global event_bus
    return event_bus
