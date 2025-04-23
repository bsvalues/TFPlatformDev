"""
TerraFusion AI Agent Manager - Coordinates specialized AI agents and integrates with MCP.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from services.ai_agents import AgentType, BaseAgent
from services.ai_agents.openai_agent import create_openai_agent
from services.ai_agents.anthropic_agent import create_anthropic_agent

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Manager for AI agents in the TerraFusion platform.
    Creates, coordinates, and provides access to all AI agents.
    """
    
    def __init__(self):
        """Initialize the agent manager"""
        self.agents: Dict[str, BaseAgent] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize all AI agents
        """
        if self._initialized:
            return
            
        try:
            # Initialize OpenAI agents
            self._register_agent(create_openai_agent(AgentType.GEOSPATIAL_ANALYSIS))
            self._register_agent(create_openai_agent(AgentType.IMAGE_RECOGNITION))
            self._register_agent(create_openai_agent(AgentType.VISUALIZATION))
            
            # Initialize Anthropic agents
            self._register_agent(create_anthropic_agent(AgentType.DOCUMENT_ANALYSIS))
            self._register_agent(create_anthropic_agent(AgentType.DECISION_SUPPORT))
            self._register_agent(create_anthropic_agent(AgentType.DATA_EXTRACTION))
            
            logger.info(f"Initialized {len(self.agents)} AI agents")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI agents: {e}")
            raise
    
    def _register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the manager
        
        Args:
            agent: AI agent instance to register
        """
        if agent.agent_id in self.agents:
            logger.warning(f"Replacing existing agent with ID: {agent.agent_id}")
            
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.agent_type.value})")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by ID
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """
        Get all agents of a specific type
        
        Args:
            agent_type: Type of agents to retrieve
            
        Returns:
            List of matching agent instances
        """
        return [agent for agent in self.agents.values() if agent.agent_type == agent_type]
    
    def get_all_agents(self) -> List[BaseAgent]:
        """
        Get all registered agents
        
        Returns:
            List of all agent instances
        """
        return list(self.agents.values())
    
    def get_agent_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered agents
        
        Returns:
            List of agent information dictionaries
        """
        return [
            {
                "id": agent.agent_id,
                "type": agent.agent_type.value,
                "description": agent.description,
                "capabilities": agent.get_capabilities()
            }
            for agent in self.agents.values()
        ]
    
    async def process_with_agent(self, agent_id: str, 
                               input_data: Union[str, Dict, bytes],
                               options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process data with a specific agent
        
        Args:
            agent_id: ID of the agent to use
            input_data: Data to process
            options: Optional processing parameters
            
        Returns:
            Processing results
            
        Raises:
            ValueError: If agent not found
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
            
        return await agent.process(input_data, options)
    
    async def process_with_agent_type(self, agent_type: AgentType,
                                    input_data: Union[str, Dict, bytes],
                                    options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process data with the first available agent of a specific type
        
        Args:
            agent_type: Type of agent to use
            input_data: Data to process
            options: Optional processing parameters
            
        Returns:
            Processing results
            
        Raises:
            ValueError: If no agents of the specified type are found
        """
        agents = self.get_agents_by_type(agent_type)
        if not agents:
            raise ValueError(f"No agents found of type: {agent_type.value}")
            
        # Use the first agent of the specified type
        return await agents[0].process(input_data, options)
    
    async def process_with_best_agent(self, input_data: Union[str, Dict, bytes],
                                     capability: str,
                                     options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process data with the most suitable agent for the requested capability
        
        Args:
            input_data: Data to process
            capability: Capability needed for processing
            options: Optional processing parameters
            
        Returns:
            Processing results from the selected agent
            
        Raises:
            ValueError: If no suitable agent is found
        """
        # Find agents with the requested capability
        suitable_agents = []
        for agent in self.agents.values():
            agent_capabilities = [cap["name"] for cap in agent.get_capabilities()]
            if capability in agent_capabilities:
                suitable_agents.append(agent)
        
        if not suitable_agents:
            raise ValueError(f"No agents found with capability: {capability}")
        
        # For now, just use the first suitable agent
        # In the future, could implement more sophisticated agent selection
        selected_agent = suitable_agents[0]
        
        # Ensure capability is included in options
        if options is None:
            options = {}
        options["capability"] = capability
        
        return await selected_agent.process(input_data, options)

# Singleton instance
_agent_manager: Optional[AgentManager] = None

async def get_agent_manager() -> AgentManager:
    """
    Get the global agent manager instance, initializing it if necessary
    
    Returns:
        Initialized AgentManager instance
    """
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
        await _agent_manager.initialize()
    return _agent_manager