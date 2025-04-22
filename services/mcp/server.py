import os
import logging
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import redis.asyncio as redis

from services.mcp.agents import AgentRegistry, get_agent_by_name
from services.event_bus.redis_bus import RedisBus

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="MCP (Multi-agent Coordination Protocol) Server",
    description="Coordinates AI agents for the TerraFusion platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize event bus
event_bus = RedisBus(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD", None),
    channel="mcp_events"
)

# Initialize agent registry
agent_registry = AgentRegistry()

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    try:
        # Connect to event bus
        await event_bus.connect()
        
        # Start event listener
        asyncio.create_task(event_listener())
        
        logger.info("MCP server started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await event_bus.disconnect()
    logger.info("MCP server shut down gracefully")

async def event_listener():
    """Listen for events from the event bus and dispatch to agents"""
    try:
        async for message in event_bus.subscribe():
            try:
                # Parse message
                event_data = json.loads(message)
                
                # Process event
                await process_event(event_data)
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}")
    except Exception as e:
        logger.error(f"Error in event listener: {str(e)}")

async def process_event(event_data: Dict[str, Any]):
    """
    Process an event from the event bus
    
    Args:
        event_data: Event data from the event bus
    """
    try:
        event_type = event_data.get("type")
        payload = event_data.get("payload", {})
        
        if event_type == "agent_task":
            # Agent task event
            agent_name = payload.get("agent")
            task_id = payload.get("task_id")
            parameters = payload.get("parameters", {})
            
            # Get agent
            agent = get_agent_by_name(agent_name)
            if not agent:
                logger.error(f"Agent {agent_name} not found")
                await event_bus.publish({
                    "type": "agent_result",
                    "payload": {
                        "task_id": task_id,
                        "status": "error",
                        "error": f"Agent {agent_name} not found"
                    }
                })
                return
            
            # Run agent
            try:
                result = await agent.run(parameters)
                
                # Publish result
                await event_bus.publish({
                    "type": "agent_result",
                    "payload": {
                        "task_id": task_id,
                        "status": "success",
                        "result": result
                    }
                })
                
                # Forward result to WebSocket clients
                await broadcast_to_websockets({
                    "type": "agent_result",
                    "task_id": task_id,
                    "status": "success",
                    "agent": agent_name,
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Error running agent {agent_name}: {str(e)}")
                
                # Publish error
                await event_bus.publish({
                    "type": "agent_result",
                    "payload": {
                        "task_id": task_id,
                        "status": "error",
                        "error": str(e)
                    }
                })
                
                # Forward error to WebSocket clients
                await broadcast_to_websockets({
                    "type": "agent_result",
                    "task_id": task_id,
                    "status": "error",
                    "agent": agent_name,
                    "error": str(e)
                })
        
        elif event_type == "agent_result":
            # Agent result event - forward to WebSocket clients
            task_id = payload.get("task_id")
            status = payload.get("status")
            result = payload.get("result", {})
            error = payload.get("error")
            
            await broadcast_to_websockets({
                "type": "agent_result",
                "task_id": task_id,
                "status": status,
                "result": result,
                "error": error
            })
        
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")

async def broadcast_to_websockets(message: Dict[str, Any]):
    """
    Broadcast a message to all active WebSocket connections
    
    Args:
        message: Message to broadcast
    """
    disconnected = []
    
    for client_id, websocket in active_connections.items():
        try:
            await websocket.send_json(message)
        except Exception:
            disconnected.append(client_id)
    
    # Clean up disconnected clients
    for client_id in disconnected:
        active_connections.pop(client_id, None)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication
    """
    # Accept connection
    await websocket.accept()
    
    # Generate client ID
    client_id = str(uuid.uuid4())
    
    # Store connection
    active_connections[client_id] = websocket
    
    try:
        # Send initial message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to MCP server"
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            # Process client message
            message_type = data.get("type")
            
            if message_type == "ping":
                # Ping/keep-alive
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": data.get("timestamp")
                })
            
            elif message_type == "agent_request":
                # Agent request
                agent_name = data.get("agent")
                parameters = data.get("parameters", {})
                task_id = data.get("task_id", str(uuid.uuid4()))
                
                # Publish to event bus
                await event_bus.publish({
                    "type": "agent_task",
                    "payload": {
                        "agent": agent_name,
                        "task_id": task_id,
                        "parameters": parameters
                    }
                })
                
                # Confirm receipt
                await websocket.send_json({
                    "type": "agent_request_received",
                    "task_id": task_id,
                    "agent": agent_name
                })
            
    except WebSocketDisconnect:
        # Remove connection
        active_connections.pop(client_id, None)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        
        # Remove connection
        active_connections.pop(client_id, None)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp"}

@app.get("/agents")
async def list_agents():
    """
    List available agents
    """
    try:
        agents = agent_registry.list_agents()
        
        return {
            "status": "success",
            "agents": agents
        }
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing agents: {str(e)}")

@app.post("/run/{agent_name}")
async def run_agent(
    agent_name: str, 
    parameters: Dict[str, Any] = Body(...)
):
    """
    Run an agent with the given parameters
    
    Args:
        agent_name: Name of the agent to run
        parameters: Parameters for the agent
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Publish to event bus
        await event_bus.publish({
            "type": "agent_task",
            "payload": {
                "agent": agent_name,
                "task_id": task_id,
                "parameters": parameters
            }
        })
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": f"Agent {agent_name} task submitted successfully"
        }
    except Exception as e:
        logger.error(f"Error submitting agent task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting agent task: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
