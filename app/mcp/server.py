import asyncio
import logging
import os
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.core.config import settings
from app.core.exceptions import MCPServerError
from app.mcp.agents.audit_agent import AuditAgent
from app.mcp.agents.data_convert_agent import DataConvertAgent
from app.mcp.agents.spatial_query_agent import SpatialQueryAgent

logger = logging.getLogger(__name__)

class MCPServer:
    """
    Multi-agent Coordination Protocol (MCP) server for AI agent orchestration.
    """
    
    def __init__(self):
        self.agents = {}
        self.active_connections: List[WebSocket] = []
        self.api_key = settings.MCP_API_KEY
        
    async def initialize(self):
        """
        Initialize MCP server and register agents
        """
        logger.info("Initializing MCP server")
        
        try:
            # Register agents
            await self.register_agents()
            
            # Start the server
            port = settings.MCP_SERVER_PORT
            logger.info(f"MCP server initialized on port {port}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise MCPServerError(f"MCP server initialization failed: {e}")
    
    async def register_agents(self):
        """
        Register AI agents with the MCP server
        """
        try:
            # Register SpatialQueryAgent
            spatial_agent = SpatialQueryAgent()
            self.register_agent("spatial_query", spatial_agent)
            
            # Register DataConvertAgent
            data_convert_agent = DataConvertAgent()
            self.register_agent("data_convert", data_convert_agent)
            
            # Register AuditAgent
            audit_agent = AuditAgent()
            self.register_agent("audit", audit_agent)
            
            logger.info(f"Registered {len(self.agents)} agents with the MCP server")
        except Exception as e:
            logger.error(f"Failed to register agents: {e}")
            raise MCPServerError(f"Agent registration failed: {e}")
    
    def register_agent(self, agent_id: str, agent_instance):
        """
        Register an agent with the MCP server
        """
        if agent_id in self.agents:
            logger.warning(f"Agent with ID {agent_id} already registered, overwriting")
        
        self.agents[agent_id] = agent_instance
        logger.info(f"Registered agent: {agent_id}")
    
    async def connect(self, websocket: WebSocket):
        """
        Connect a client to the MCP server via WebSocket
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected to MCP server, total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a client from the MCP server
        """
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected from MCP server, remaining connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """
        Broadcast a message to all connected clients
        """
        for connection in self.active_connections:
            await connection.send_json(message)
    
    async def run_agent(self, agent_id: str, operation: str, parameters: Dict):
        """
        Run an agent operation with the given parameters
        """
        if agent_id not in self.agents:
            raise MCPServerError(f"Agent not found: {agent_id}")
        
        agent = self.agents[agent_id]
        
        # Validate operation
        if not hasattr(agent, operation) or not callable(getattr(agent, operation)):
            raise MCPServerError(f"Operation not supported by agent {agent_id}: {operation}")
        
        # Run operation
        try:
            operation_func = getattr(agent, operation)
            result = await operation_func(**parameters)
            
            # Broadcast result to connected clients
            await self.broadcast({
                "type": "agent_result",
                "agent_id": agent_id,
                "operation": operation,
                "result": result
            })
            
            return result
        except Exception as e:
            logger.error(f"Agent execution error ({agent_id}.{operation}): {e}")
            raise MCPServerError(f"Agent execution failed: {e}")
    
    async def verify_api_key(self, api_key: str) -> bool:
        """
        Verify that the API key is valid
        """
        return api_key == self.api_key


# Global MCP server instance
mcp_server = MCPServer()

async def start_mcp_server():
    """
    Start the MCP server
    """
    global mcp_server
    await mcp_server.initialize()
    
    # TODO: Start WebSocket server in a separate task
    return mcp_server
