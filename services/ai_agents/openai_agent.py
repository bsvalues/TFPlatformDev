"""
OpenAI-based AI agent for TerraFusion.
This agent specializes in geospatial analysis, image recognition, and visualization tasks.
"""

import json
import logging
import os
import base64
from typing import Any, Dict, List, Optional, Union

import openai
from openai import OpenAI

from services.ai_agents import BaseAgent, AgentType

# Set up logging
logger = logging.getLogger(__name__)

class OpenAIAgent(BaseAgent):
    """
    OpenAI-based AI agent with specialized capabilities for geospatial tasks
    """
    
    def __init__(self, agent_id: str, agent_type: AgentType, description: str):
        """
        Initialize the OpenAI agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent from AgentType enum
            description: Human-readable description of the agent's purpose and capabilities
        """
        super().__init__(agent_id, agent_type, description)
        
        # Initialize the OpenAI client
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        try:
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            self.client = OpenAI(api_key=self.api_key)
            self.model = "gpt-4o"  # Default to GPT-4o
            logger.info(f"OpenAI agent '{agent_id}' initialized successfully")
            
            # Register capabilities specific to this agent
            self._register_default_capabilities()
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI agent: {e}")
            raise
    
    def _register_default_capabilities(self):
        """Register the default capabilities for this agent"""
        self.register_capability(
            "geospatial_analysis", 
            "Analyze geospatial data and provide insights"
        )
        self.register_capability(
            "image_recognition", 
            "Identify features in satellite or aerial imagery"
        )
        self.register_capability(
            "visualization_generation", 
            "Generate visualization descriptions for geospatial data"
        )
        self.register_capability(
            "coordinate_parsing", 
            "Extract and validate geographic coordinates from text"
        )
        self.register_capability(
            "land_use_classification", 
            "Classify land use from descriptive text or imagery"
        )
    
    async def process(self, input_data: Union[str, Dict, bytes], 
               options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process input data using OpenAI API
        
        Args:
            input_data: Data to be processed (text, JSON, image bytes, etc.)
            options: Optional parameters including:
                - capability: Specific capability to use
                - model: Override default model
                - temperature: Model temperature (default 0.7)
                - max_tokens: Maximum tokens to generate (default 1000)
                
        Returns:
            Dictionary containing processing results
        """
        if options is None:
            options = {}
            
        capability = options.get("capability", "geospatial_analysis")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 1000)
        
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
            logger.error(f"Error processing data with OpenAI agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_id": self.agent_id,
                "capability": capability
            }
    
    async def _process_text(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process text input using OpenAI API"""
        capability = options.get("capability", "geospatial_analysis")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 1000)
        response_format = options.get("response_format", None)
        
        # Configure prompts based on capability
        system_prompt = self._get_system_prompt_for_capability(capability)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        chat_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Add response format if specified
        if response_format == "json":
            chat_params["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**chat_params)
        
        result = {
            "success": True,
            "agent_id": self.agent_id,
            "capability": capability,
            "content": response.choices[0].message.content,
            "model": model,
        }
        
        # If JSON was requested, try to parse the response
        if response_format == "json":
            try:
                result["json_content"] = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse response as JSON")
                
        return result
    
    async def _process_image(self, image_data: bytes, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process image data using OpenAI API"""
        capability = options.get("capability", "image_recognition")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 1000)
        prompt = options.get("prompt", "Analyze this geospatial image in detail")
        
        # Configure prompts based on capability
        system_prompt = self._get_system_prompt_for_capability(capability)
        
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        # Create message with image
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
        
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            "success": True,
            "agent_id": self.agent_id,
            "capability": capability,
            "content": response.choices[0].message.content,
            "model": model
        }
    
    async def _process_structured_data(self, data: Dict, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process structured JSON data using OpenAI API"""
        capability = options.get("capability", "geospatial_analysis")
        model = options.get("model", self.model)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 1000)
        
        # Convert structured data to a string representation
        data_str = json.dumps(data, indent=2)
        prompt = options.get("prompt", f"Analyze this geospatial data:\n\n{data_str}")
        
        # Configure prompts based on capability
        system_prompt = self._get_system_prompt_for_capability(capability)
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"} if options.get("response_format") == "json" else None
        )
        
        result = {
            "success": True,
            "agent_id": self.agent_id,
            "capability": capability,
            "content": response.choices[0].message.content,
            "model": model
        }
        
        # If JSON response format was requested, parse the response
        if options.get("response_format") == "json":
            try:
                result["json_content"] = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse response as JSON")
        
        return result
    
    def _get_system_prompt_for_capability(self, capability: str) -> str:
        """Get the appropriate system prompt for a specific capability"""
        if capability == "geospatial_analysis":
            return """You are a geospatial analysis expert. Analyze geographic data, identify spatial patterns, and provide insights about locations, territories, and geographic features. 
            Use GIS terminology correctly and provide accurate interpretations of geographic data. When appropriate, suggest types of visualizations or further analysis that could be useful."""
        
        elif capability == "image_recognition":
            return """You are an expert in analyzing satellite and aerial imagery. Identify features, land use patterns, structures, natural formations, and other elements visible in the images. 
            Be precise in describing what you see and the confidence level of your identification. Note any limitations based on image quality or ambiguity."""
        
        elif capability == "visualization_generation":
            return """You are a data visualization specialist for geospatial data. Create detailed visualization descriptions for maps, spatial patterns, and geographic data. 
            Suggest appropriate chart types, map projections, color schemes, and interactive elements. Your descriptions should be specific enough that a developer could implement them."""
        
        elif capability == "coordinate_parsing":
            return """You are a specialist in geographic coordinate systems. Extract and validate geographic coordinates from text. 
            Recognize different coordinate formats (decimal degrees, DMS, etc.) and convert between them when needed. Flag any potentially invalid or unclear coordinates."""
        
        elif capability == "land_use_classification":
            return """You are an expert in land use classification. Analyze descriptions or images of areas and classify them according to standard land use categories. 
            Consider factors like vegetation, structures, roads, water bodies, and other visible features. Provide confidence levels for your classifications."""
        
        else:
            # Default prompt if capability not recognized
            return """You are a TerraFusion AI assistant specializing in geospatial data analysis. Provide helpful, accurate information related to geographic data, spatial analysis, 
            and location-based insights. Use proper terminology and explain concepts clearly."""

# Factory function to create specific types of OpenAI agents
def create_openai_agent(agent_type: AgentType, agent_id: Optional[str] = None) -> OpenAIAgent:
    """
    Create an OpenAI agent of the specified type
    
    Args:
        agent_type: Type of agent to create
        agent_id: Optional custom ID for the agent
        
    Returns:
        Configured OpenAI agent instance
    """
    if agent_type == AgentType.GEOSPATIAL_ANALYSIS:
        return OpenAIAgent(
            agent_id or "openai_geospatial",
            AgentType.GEOSPATIAL_ANALYSIS,
            "Specializes in analyzing geospatial data, identifying patterns, and extracting insights from geographic information"
        )
    
    elif agent_type == AgentType.IMAGE_RECOGNITION:
        return OpenAIAgent(
            agent_id or "openai_image_recognition",
            AgentType.IMAGE_RECOGNITION,
            "Specializes in analyzing satellite and aerial imagery to identify features, structures, and patterns"
        )
    
    elif agent_type == AgentType.VISUALIZATION:
        return OpenAIAgent(
            agent_id or "openai_visualization",
            AgentType.VISUALIZATION,
            "Specializes in generating visualization concepts and descriptions for geospatial data"
        )
    
    else:
        raise ValueError(f"Unsupported agent type for OpenAI agent: {agent_type}")