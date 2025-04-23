"""
Anthropic Claude-based AI agent for TerraFusion.
This agent specializes in document analysis, decision support, and complex reasoning tasks.
"""

import json
import logging
import os
import base64
import sys
from typing import Any, Dict, List, Optional, Union

import anthropic
from anthropic import Anthropic

from services.ai_agents import BaseAgent, AgentType

# Set up logging
logger = logging.getLogger(__name__)

class AnthropicAgent(BaseAgent):
    """
    Anthropic Claude-based AI agent with specialized capabilities for document analysis and decision support
    """
    
    def __init__(self, agent_id: str, agent_type: AgentType, description: str):
        """
        Initialize the Anthropic agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent from AgentType enum
            description: Human-readable description of the agent's purpose and capabilities
        """
        super().__init__(agent_id, agent_type, description)
        
        # Initialize the Anthropic client
        # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024.
        # do not change this unless explicitly requested by the user
        try:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            
            self.client = Anthropic(api_key=self.api_key)
            self.model = "claude-3-5-sonnet-20241022"  # Default to newest Claude model
            logger.info(f"Anthropic agent '{agent_id}' initialized successfully")
            
            # Register capabilities specific to this agent
            self._register_default_capabilities()
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic agent: {e}")
            raise
    
    def _register_default_capabilities(self):
        """Register the default capabilities for this agent"""
        self.register_capability(
            "document_analysis", 
            "Analyze complex documents and extract structured information"
        )
        self.register_capability(
            "decision_support", 
            "Provide decision support for complex geospatial planning scenarios"
        )
        self.register_capability(
            "policy_assessment", 
            "Evaluate land use policies and regulations for compliance"
        )
        self.register_capability(
            "impact_analysis", 
            "Analyze environmental and social impacts of land use changes"
        )
        self.register_capability(
            "stakeholder_communication", 
            "Generate stakeholder communications related to land use decisions"
        )
    
    async def process(self, input_data: Union[str, Dict, bytes], 
               options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process input data using Anthropic API
        
        Args:
            input_data: Data to be processed (text, JSON, image bytes, etc.)
            options: Optional parameters including:
                - capability: Specific capability to use
                - model: Override default model
                - temperature: Model temperature (default 0.7)
                - max_tokens: Maximum tokens to generate (default 2000)
                
        Returns:
            Dictionary containing processing results
        """
        if options is None:
            options = {}
            
        capability = options.get("capability", "document_analysis")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2000)
        
        try:
            # Handle different input types
            if isinstance(input_data, bytes):
                # Process image data
                return await self._process_image(input_data, options)
            elif isinstance(input_data, dict):
                # Process structured data
                return await self._process_structured_data(input_data, options)
            else:
                # Process text input
                return await self._process_text(input_data, options)
                
        except Exception as e:
            logger.error(f"Error processing data with Anthropic agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_id": self.agent_id,
                "capability": capability
            }
    
    async def _process_text(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process text input using Anthropic API"""
        capability = options.get("capability", "document_analysis")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2000)
        
        # Configure system prompt based on capability
        system_prompt = self._get_system_prompt_for_capability(capability)
        
        message = self.client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": text}
            ]
        )
        
        result = {
            "success": True,
            "agent_id": self.agent_id,
            "capability": capability,
            "content": message.content[0].text,
            "model": model,
        }
        
        # If JSON was requested, try to parse the response
        if options.get("response_format") == "json":
            try:
                result["json_content"] = json.loads(message.content[0].text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse response as JSON")
                
        return result
    
    async def _process_image(self, image_data: bytes, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process image data using Anthropic API"""
        capability = options.get("capability", "document_analysis")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2000)
        prompt = options.get("prompt", "Analyze this document in detail")
        
        # Configure system prompt based on capability
        system_prompt = self._get_system_prompt_for_capability(capability)
        
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        message = self.client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "text", 
                            "text": prompt
                        },
                        {
                            "type": "image", 
                            "source": {
                                "type": "base64", 
                                "media_type": "image/jpeg", 
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        )
        
        return {
            "success": True,
            "agent_id": self.agent_id,
            "capability": capability,
            "content": message.content[0].text,
            "model": model
        }
    
    async def _process_structured_data(self, data: Dict, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process structured JSON data using Anthropic API"""
        capability = options.get("capability", "document_analysis")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2000)
        
        # Convert structured data to a string representation
        data_str = json.dumps(data, indent=2)
        prompt = options.get("prompt", f"Analyze this data:\n\n{data_str}")
        
        # Configure system prompt based on capability
        system_prompt = self._get_system_prompt_for_capability(capability)
        
        message = self.client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        result = {
            "success": True,
            "agent_id": self.agent_id,
            "capability": capability,
            "content": message.content[0].text,
            "model": model
        }
        
        # If JSON response format was requested, try to parse the response
        if options.get("response_format") == "json":
            try:
                result["json_content"] = json.loads(message.content[0].text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse response as JSON")
        
        return result
    
    def _get_system_prompt_for_capability(self, capability: str) -> str:
        """Get the appropriate system prompt for a specific capability"""
        if capability == "document_analysis":
            return """You are a document analysis expert specializing in geospatial and land use documentation. Extract structured information from complex documents like land use plans, environmental impact statements, zoning regulations, and property descriptions.
            Identify key information including parcel numbers, zoning designations, land use restrictions, and regulatory requirements. Organize the information in a clear, structured format."""
        
        elif capability == "decision_support":
            return """You are a decision support specialist for complex geospatial planning scenarios. Analyze multiple factors including environmental considerations, regulatory requirements, community needs, and economic impacts.
            Identify potential conflicts, provide balanced assessment of options, and highlight tradeoffs. Make clear, evidence-based recommendations while acknowledging areas of uncertainty."""
        
        elif capability == "policy_assessment":
            return """You are an expert in land use policy and regulatory compliance. Evaluate descriptions of land use proposals against applicable regulations and policies.
            Identify compliance issues, potential conflicts with zoning or environmental regulations, and required permits or approvals. Suggest modifications that would improve compliance when appropriate."""
        
        elif capability == "impact_analysis":
            return """You are an environmental and social impact analysis expert. Evaluate potential impacts of land use changes on the environment, community, and infrastructure.
            Consider factors like water resources, habitat, traffic, property values, community character, and service demands. Provide balanced assessment of both positive and negative impacts."""
        
        elif capability == "stakeholder_communication":
            return """You are a communication specialist focused on land use and planning issues. Create clear, accessible communications about complex land use topics for different stakeholder groups.
            Adjust technical detail and language based on the audience while maintaining accuracy. Present balanced information that acknowledges different perspectives."""
        
        else:
            # Default prompt if capability not recognized
            return """You are a TerraFusion AI assistant specializing in geospatial analysis, land use planning, and environmental assessment. Provide helpful, accurate information related to these topics.
            Use proper terminology, explain complex concepts clearly, and provide balanced perspectives on contentious issues."""

# Factory function to create specific types of Anthropic agents
def create_anthropic_agent(agent_type: AgentType, agent_id: Optional[str] = None) -> AnthropicAgent:
    """
    Create an Anthropic agent of the specified type
    
    Args:
        agent_type: Type of agent to create
        agent_id: Optional custom ID for the agent
        
    Returns:
        Configured Anthropic agent instance
    """
    if agent_type == AgentType.DOCUMENT_ANALYSIS:
        return AnthropicAgent(
            agent_id or "anthropic_document",
            AgentType.DOCUMENT_ANALYSIS,
            "Specializes in analyzing complex documents and extracting structured information"
        )
    
    elif agent_type == AgentType.DECISION_SUPPORT:
        return AnthropicAgent(
            agent_id or "anthropic_decision",
            AgentType.DECISION_SUPPORT,
            "Specializes in providing decision support for complex geospatial planning scenarios"
        )
    
    elif agent_type == AgentType.DATA_EXTRACTION:
        return AnthropicAgent(
            agent_id or "anthropic_extraction",
            AgentType.DATA_EXTRACTION,
            "Specializes in extracting structured data from unstructured sources like documents and reports"
        )
    
    else:
        raise ValueError(f"Unsupported agent type for Anthropic agent: {agent_type}")