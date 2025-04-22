import os
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from abc import ABC, abstractmethod
import aiohttp
import langchain
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import langchain.llms

from services.mcp.tools import (
    SpatialQueryTool,
    DataConversionTool,
    FeatureRetrievalTool,
    SQLServerQueryTool
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize LLM
API_KEY = os.getenv("OPENAI_API_KEY", "")
if API_KEY:
    llm = langchain.llms.OpenAI(temperature=0)
else:
    # Fallback to a mock LLM for development without API key
    logger.warning("No OpenAI API key found. Using mock LLM.")
    llm = None

class Agent(ABC):
    """
    Base class for all agents in the system
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.tools = []
    
    @abstractmethod
    async def run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent with the given parameters
        
        Args:
            parameters: Agent parameters
            
        Returns:
            Agent result
        """
        pass

class SpatialQueryAgent(Agent):
    """
    Agent for performing spatial queries and operations
    """
    def __init__(self):
        super().__init__(
            name="spatial_query_agent",
            description="Agent for performing spatial queries and operations on geographic data"
        )
        
        # Initialize tools
        self.spatial_query_tool = SpatialQueryTool()
        self.feature_retrieval_tool = FeatureRetrievalTool()
        
        # Set up tools
        self.tools = [
            Tool(
                name="get_feature",
                func=self.feature_retrieval_tool.get_feature,
                description="Get a feature by ID"
            ),
            Tool(
                name="buffer_feature",
                func=self.spatial_query_tool.buffer,
                description="Create a buffer around a geometry"
            ),
            Tool(
                name="intersect_features",
                func=self.spatial_query_tool.intersect,
                description="Find the intersection of two geometries"
            ),
            Tool(
                name="calculate_distance",
                func=self.spatial_query_tool.distance,
                description="Calculate the distance between two geometries"
            ),
            Tool(
                name="calculate_area",
                func=self.spatial_query_tool.area,
                description="Calculate the area of a geometry"
            )
        ]
    
    async def run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the spatial query agent
        
        Args:
            parameters: Agent parameters
            
        Returns:
            Agent result
        """
        try:
            # Extract parameters
            operation = parameters.get("operation", "buffer")
            feature_id = parameters.get("feature_id")
            
            if not feature_id:
                raise ValueError("feature_id is required")
            
            # Direct operation execution based on operation type
            if operation == "buffer":
                distance = float(parameters.get("distance", 100))
                result = await self.spatial_query_tool.buffer(feature_id, distance)
                return result
            
            elif operation == "intersect":
                target_feature_id = parameters.get("target_feature_id")
                if not target_feature_id:
                    raise ValueError("target_feature_id is required for intersection operation")
                
                result = await self.spatial_query_tool.intersect(feature_id, target_feature_id)
                return result
            
            elif operation == "distance":
                target_feature_id = parameters.get("target_feature_id")
                if not target_feature_id:
                    raise ValueError("target_feature_id is required for distance calculation")
                
                result = await self.spatial_query_tool.distance(feature_id, target_feature_id)
                return result
            
            elif operation == "area":
                result = await self.spatial_query_tool.area(feature_id)
                return result
            
            else:
                # If we have an LLM, use it to decide what to do
                if llm:
                    # Create LangChain agent
                    prompt = PromptTemplate(
                        template="""You are a spatial analysis expert. Use the tools available to you to solve the given problem.
                        
                        Problem: {problem}
                        
                        Available tools:
                        {tools}
                        
                        Use the following format:
                        
                        Thought: Consider what to do
                        Action: tool_name
                        Action Input: tool input
                        Observation: tool output
                        ... (repeat until you have solved the problem)
                        Final Answer: The answer to the problem
                        
                        Begin!
                        
                        Thought:""",
                        input_variables=["problem", "tools"],
                    )
                    
                    agent = create_react_agent(llm, self.tools, prompt)
                    agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
                    
                    # Convert parameters to problem statement
                    problem = f"I need to analyze feature {feature_id} using {operation} operation. Parameters: {json.dumps(parameters)}"
                    
                    # Run agent
                    result = await agent_executor.arun({"problem": problem})
                    
                    return {
                        "operation": operation,
                        "feature_id": feature_id,
                        "analysis": result
                    }
                else:
                    raise ValueError(f"Unsupported operation: {operation} and no LLM available")
            
        except Exception as e:
            logger.error(f"Error in spatial query agent: {str(e)}")
            raise

class DataConvertAgent(Agent):
    """
    Agent for converting data between different formats
    """
    def __init__(self):
        super().__init__(
            name="data_convert_agent",
            description="Agent for converting data between different formats and coordinate systems"
        )
        
        # Initialize tools
        self.data_conversion_tool = DataConversionTool()
        
        # Set up tools
        self.tools = [
            Tool(
                name="convert_format",
                func=self.data_conversion_tool.convert_format,
                description="Convert data between different formats"
            ),
            Tool(
                name="transform_coordinates",
                func=self.data_conversion_tool.transform_coordinates,
                description="Transform coordinates between different coordinate systems"
            )
        ]
    
    async def run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the data conversion agent
        
        Args:
            parameters: Agent parameters
            
        Returns:
            Agent result
        """
        try:
            # Extract parameters
            source_format = parameters.get("source_format")
            target_format = parameters.get("target_format")
            source_data = parameters.get("source_data")
            source_crs = parameters.get("source_crs")
            target_crs = parameters.get("target_crs")
            
            # If we're converting formats
            if source_format and target_format and source_data:
                result = await self.data_conversion_tool.convert_format(
                    source_data, source_format, target_format
                )
                return result
            
            # If we're transforming coordinates
            elif source_crs and target_crs and source_data:
                result = await self.data_conversion_tool.transform_coordinates(
                    source_data, source_crs, target_crs
                )
                return result
            
            else:
                raise ValueError("Invalid parameters for data conversion agent")
            
        except Exception as e:
            logger.error(f"Error in data convert agent: {str(e)}")
            raise

class AuditAgent(Agent):
    """
    Agent for performing data quality audits
    """
    def __init__(self):
        super().__init__(
            name="audit_agent",
            description="Agent for performing data quality audits and applying corrections"
        )
        
        # Initialize tools
        self.feature_retrieval_tool = FeatureRetrievalTool()
        
        # Set up tools
        self.tools = [
            Tool(
                name="get_feature",
                func=self.feature_retrieval_tool.get_feature,
                description="Get a feature by ID"
            ),
            Tool(
                name="validate_geometry",
                func=self.validate_geometry,
                description="Validate a geometry for correctness"
            ),
            Tool(
                name="validate_properties",
                func=self.validate_properties,
                description="Validate feature properties"
            ),
            Tool(
                name="fix_geometry",
                func=self.fix_geometry,
                description="Fix invalid geometries"
            )
        ]
    
    async def validate_geometry(self, feature_id: str) -> Dict[str, Any]:
        """
        Validate a geometry for correctness
        
        Args:
            feature_id: ID of the feature to validate
            
        Returns:
            Validation result
        """
        try:
            # Get feature
            feature = await self.feature_retrieval_tool.get_feature(feature_id)
            
            # Extract geometry
            geometry = feature.get("geometry", {})
            
            # Make validation API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "validation",
                        "parameters": {
                            "feature_id": feature_id,
                            "rules": ["valid_geometry"]
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if validation task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error validating geometry: {result.get('detail')}")
                    
                    return {
                        "feature_id": feature_id,
                        "task_id": result.get("task_id"),
                        "message": "Validation task started"
                    }
        except Exception as e:
            logger.error(f"Error validating geometry: {str(e)}")
            raise
    
    async def validate_properties(self, feature_id: str, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate feature properties
        
        Args:
            feature_id: ID of the feature to validate
            required_fields: List of required fields
            
        Returns:
            Validation result
        """
        try:
            # Get feature
            feature = await self.feature_retrieval_tool.get_feature(feature_id)
            
            # Extract properties
            properties = feature.get("properties", {})
            
            # Validate required fields
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in properties:
                        missing_fields.append(field)
                
                return {
                    "feature_id": feature_id,
                    "valid": len(missing_fields) == 0,
                    "missing_fields": missing_fields
                }
            
            return {
                "feature_id": feature_id,
                "valid": True,
                "properties": list(properties.keys())
            }
        except Exception as e:
            logger.error(f"Error validating properties: {str(e)}")
            raise
    
    async def fix_geometry(self, feature_id: str) -> Dict[str, Any]:
        """
        Fix invalid geometries
        
        Args:
            feature_id: ID of the feature to fix
            
        Returns:
            Fix result
        """
        try:
            # Make fix API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "validation",
                        "parameters": {
                            "feature_id": feature_id,
                            "rules": ["valid_geometry"],
                            "auto_correct": True
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if validation task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error fixing geometry: {result.get('detail')}")
                    
                    return {
                        "feature_id": feature_id,
                        "task_id": result.get("task_id"),
                        "message": "Geometry fix task started"
                    }
        except Exception as e:
            logger.error(f"Error fixing geometry: {str(e)}")
            raise
    
    async def run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the audit agent
        
        Args:
            parameters: Agent parameters
            
        Returns:
            Agent result
        """
        try:
            # Extract parameters
            feature_id = parameters.get("feature_id")
            rules = parameters.get("rules", [])
            auto_correct = parameters.get("auto_correct", False)
            
            if not feature_id:
                raise ValueError("feature_id is required")
            
            # Make API call to audit service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "validation",
                        "parameters": {
                            "feature_id": feature_id,
                            "rules": rules,
                            "auto_correct": auto_correct,
                            "required_fields": parameters.get("required_fields", [])
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if validation task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error in audit agent: {result.get('detail')}")
                    
                    task_id = result.get("task_id")
                    
                    # Wait for task to complete
                    max_retries = 10
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check task status
                        async with session.get(
                            f"http://localhost:8000/terra_insight/agents/tasks/{task_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            task = status_result.get("task", {})
                            
                            if task.get("status") == "completed":
                                return task.get("result", {})
                            
                            if task.get("status") == "failed":
                                raise ValueError(f"Audit task failed: {task.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for audit task to complete")
            
        except Exception as e:
            logger.error(f"Error in audit agent: {str(e)}")
            raise

# Agent registry
_AGENTS = {}

def register_agent(agent: Agent):
    """
    Register an agent with the system
    
    Args:
        agent: Agent to register
    """
    _AGENTS[agent.name] = agent

def get_agent_by_name(name: str) -> Optional[Agent]:
    """
    Get an agent by name
    
    Args:
        name: Name of the agent
        
    Returns:
        Agent if found, None otherwise
    """
    return _AGENTS.get(name)

class AgentRegistry:
    """
    Registry for agents in the system
    """
    def __init__(self):
        # Register default agents
        self.register_defaults()
    
    def register_defaults(self):
        """Register default agents"""
        register_agent(SpatialQueryAgent())
        register_agent(DataConvertAgent())
        register_agent(AuditAgent())
    
    def register(self, agent: Agent):
        """
        Register an agent
        
        Args:
            agent: Agent to register
        """
        register_agent(agent)
    
    def get(self, name: str) -> Optional[Agent]:
        """
        Get an agent by name
        
        Args:
            name: Name of the agent
            
        Returns:
            Agent if found, None otherwise
        """
        return get_agent_by_name(name)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents
        
        Returns:
            List of agent information
        """
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "tools": [tool.name for tool in agent.tools]
            }
            for agent in _AGENTS.values()
        ]
