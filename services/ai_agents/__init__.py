"""
TerraFusion AI Agents - Specialized AI agents for geospatial data processing and analysis.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

class AgentType(Enum):
    """Types of AI agents available in the system"""
    GEOSPATIAL_ANALYSIS = "geospatial_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    IMAGE_RECOGNITION = "image_recognition"
    DECISION_SUPPORT = "decision_support"
    DATA_EXTRACTION = "data_extraction"
    VISUALIZATION = "visualization"


class BaseAgent(ABC):
    """Base class for all AI agents in TerraFusion"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, description: str):
        """
        Initialize the base agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent from AgentType enum
            description: Human-readable description of the agent's purpose and capabilities
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.description = description
        self.capabilities = []
        
    @abstractmethod
    async def process(self, input_data: Union[str, Dict, bytes], 
               options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process input data and return results
        
        Args:
            input_data: Data to be processed (text, JSON, image bytes, etc.)
            options: Optional parameters to configure processing
            
        Returns:
            Dictionary containing processing results
        """
        pass
    
    def register_capability(self, capability_name: str, description: str) -> None:
        """
        Register a capability for this agent
        
        Args:
            capability_name: Name of the capability
            description: Description of what the capability does
        """
        self.capabilities.append({
            "name": capability_name,
            "description": description
        })
        
    def get_capabilities(self) -> List[Dict[str, str]]:
        """
        Get all capabilities of this agent
        
        Returns:
            List of capability dictionaries
        """
        return self.capabilities