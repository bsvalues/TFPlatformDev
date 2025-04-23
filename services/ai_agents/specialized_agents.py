"""
Specialized AI agents for TerraFusion - Customized for specific geospatial tasks.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union, Tuple

from services.ai_agents import AgentType, BaseAgent
from services.ai_agents.openai_agent import OpenAIAgent
from services.ai_agents.anthropic_agent import AnthropicAgent

logger = logging.getLogger(__name__)

class GeoParsingAgent(OpenAIAgent):
    """
    Specialized agent for extracting and validating geographic coordinates and features from text
    """
    
    def __init__(self):
        """Initialize the GeoParsingAgent"""
        super().__init__(
            agent_id="geo_parsing_agent",
            agent_type=AgentType.GEOSPATIAL_ANALYSIS,
            description="Extracts and validates geographic coordinates and features from text"
        )
        
        # Override capabilities
        self.capabilities = []
        self.register_capability(
            "coordinate_extraction", 
            "Extract geographic coordinates from text in various formats"
        )
        self.register_capability(
            "feature_identification", 
            "Identify geographic features mentioned in text"
        )
        self.register_capability(
            "location_resolution", 
            "Resolve ambiguous location references to specific coordinates"
        )
    
    async def process(self, input_data: Union[str, Dict, bytes], 
               options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process text to extract geographic information
        
        Args:
            input_data: Text to analyze
            options: Processing options
            
        Returns:
            Extracted geographic information
        """
        if not isinstance(input_data, str):
            raise ValueError("GeoParsingAgent only supports text input")
            
        if options is None:
            options = {}
            
        capability = options.get("capability", "coordinate_extraction")
        
        if capability == "coordinate_extraction":
            return await self._extract_coordinates(input_data)
        elif capability == "feature_identification":
            return await self._identify_features(input_data)
        elif capability == "location_resolution":
            return await self._resolve_locations(input_data)
        else:
            # Fallback to standard processing
            return await super().process(input_data, options)
    
    async def _extract_coordinates(self, text: str) -> Dict[str, Any]:
        """Extract coordinates from text"""
        # Configure specialized prompt for coordinate extraction
        system_prompt = """You are a geographic coordinate extraction specialist. Your task is to find and extract any geographic coordinates from the provided text.
        
        Extract coordinates in ANY format, including:
        1. Decimal degrees (e.g., 40.7128, -74.0060)
        2. Degrees, minutes, seconds (e.g., 40°42'51.3"N 74°00'21.5"W)
        3. UTM coordinates
        4. MGRS grid references
        
        For each coordinate found:
        1. Extract the original text
        2. Convert to standard decimal degrees (if possible)
        3. Indicate the confidence level (high/medium/low)
        4. Note any context about what the coordinate refers to
        
        Return the results as a structured JSON object with an array of found coordinates.
        
        Format:
        {
          "coordinates": [
            {
              "original_text": "The original coordinate text as found",
              "decimal_degrees": {"latitude": lat, "longitude": lon},
              "confidence": "high|medium|low",
              "context": "What this coordinate refers to",
              "coordinate_system": "The identified coordinate system"
            }
          ],
          "text_contains_coordinates": true|false
        }
        """
        
        # Process with OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,  # Lower temperature for more deterministic results
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return {
                "success": True,
                "agent_id": self.agent_id,
                "capability": "coordinate_extraction",
                "content": response.choices[0].message.content,
                "coordinates": result.get("coordinates", []),
                "text_contains_coordinates": result.get("text_contains_coordinates", False)
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse coordinate extraction results as JSON")
            return {
                "success": False,
                "agent_id": self.agent_id,
                "capability": "coordinate_extraction",
                "error": "Failed to parse results",
                "content": response.choices[0].message.content
            }
    
    async def _identify_features(self, text: str) -> Dict[str, Any]:
        """Identify geographic features in text"""
        # Similar implementation as _extract_coordinates but for features
        system_prompt = """You are a geographic feature extraction specialist. Your task is to identify any geographic features mentioned in the provided text.
        
        Look for:
        1. Natural features (mountains, rivers, lakes, forests, etc.)
        2. Administrative areas (countries, states, counties, cities, etc.)
        3. Infrastructure (roads, buildings, landmarks, etc.)
        4. Land use areas (parks, reserves, districts, etc.)
        
        For each feature found:
        1. Extract the name
        2. Classify the feature type
        3. Note any descriptive information
        4. Estimate a confidence level (high/medium/low)
        
        Return the results as a structured JSON object with an array of found features.
        
        Format:
        {
          "features": [
            {
              "name": "Feature name",
              "type": "Feature classification",
              "description": "Any additional information",
              "confidence": "high|medium|low"
            }
          ],
          "text_contains_features": true|false
        }
        """
        
        # Process with OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return {
                "success": True,
                "agent_id": self.agent_id,
                "capability": "feature_identification",
                "content": response.choices[0].message.content,
                "features": result.get("features", []),
                "text_contains_features": result.get("text_contains_features", False)
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse feature identification results as JSON")
            return {
                "success": False,
                "agent_id": self.agent_id,
                "capability": "feature_identification",
                "error": "Failed to parse results",
                "content": response.choices[0].message.content
            }
    
    async def _resolve_locations(self, text: str) -> Dict[str, Any]:
        """Resolve ambiguous location references"""
        # Implementation for location resolution
        system_prompt = """You are a location resolution specialist. Your task is to resolve ambiguous location references in the provided text.
        
        For each ambiguous location:
        1. Identify the potential matches
        2. Rank them by likelihood
        3. Provide reasoning for the ranking
        
        Return the results as a structured JSON object with an array of resolved locations.
        
        Format:
        {
          "resolved_locations": [
            {
              "original_text": "The ambiguous location reference",
              "possible_matches": [
                {
                  "name": "Full location name",
                  "type": "Location type",
                  "likelihood": "high|medium|low",
                  "reasoning": "Why this is a likely match"
                }
              ]
            }
          ]
        }
        """
        
        # Process with OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return {
                "success": True,
                "agent_id": self.agent_id,
                "capability": "location_resolution",
                "content": response.choices[0].message.content,
                "resolved_locations": result.get("resolved_locations", [])
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse location resolution results as JSON")
            return {
                "success": False,
                "agent_id": self.agent_id,
                "capability": "location_resolution",
                "error": "Failed to parse results",
                "content": response.choices[0].message.content
            }

class EnvironmentalImpactAgent(AnthropicAgent):
    """
    Specialized agent for analyzing environmental impacts of land use changes
    """
    
    def __init__(self):
        """Initialize the EnvironmentalImpactAgent"""
        super().__init__(
            agent_id="environmental_impact_agent",
            agent_type=AgentType.DECISION_SUPPORT,
            description="Analyzes environmental impacts of land use changes and development projects"
        )
        
        # Override capabilities
        self.capabilities = []
        self.register_capability(
            "impact_assessment", 
            "Assess potential environmental impacts of land use changes"
        )
        self.register_capability(
            "mitigation_recommendations", 
            "Recommend measures to mitigate environmental impacts"
        )
        self.register_capability(
            "regulatory_compliance", 
            "Evaluate compliance with environmental regulations"
        )
    
    async def process(self, input_data: Union[str, Dict, bytes], 
               options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process text or structured data to analyze environmental impacts
        
        Args:
            input_data: Text or data to analyze
            options: Processing options
            
        Returns:
            Environmental impact analysis
        """
        if options is None:
            options = {}
            
        capability = options.get("capability", "impact_assessment")
        
        # Handle specialized capabilities
        if capability == "impact_assessment":
            return await self._assess_impacts(input_data)
        elif capability == "mitigation_recommendations":
            return await self._recommend_mitigations(input_data)
        elif capability == "regulatory_compliance":
            return await self._evaluate_compliance(input_data)
        else:
            # Fallback to standard processing
            return await super().process(input_data, options)
    
    async def _assess_impacts(self, input_data: Union[str, Dict]) -> Dict[str, Any]:
        """Assess environmental impacts"""
        # Convert dict to string if needed
        if isinstance(input_data, dict):
            input_text = json.dumps(input_data, indent=2)
        else:
            input_text = input_data
            
        system_prompt = """You are an environmental impact assessment specialist. Analyze the described project or land use change and identify potential environmental impacts.
        
        Consider impacts on:
        1. Water resources (quality, quantity, drainage)
        2. Air quality
        3. Habitats and biodiversity
        4. Soil and geology
        5. Noise and light pollution
        6. Visual and aesthetic impacts
        7. Climate change implications
        
        For each potential impact:
        1. Describe the nature of the impact
        2. Assess the likely severity (high/medium/low)
        3. Indicate whether it's short-term or long-term
        4. Note any cascading or cumulative effects
        
        Maintain a balanced perspective and focus on scientifically supportable impacts. Avoid speculation while being thorough in your assessment.
        
        Structure your response as JSON with the following format:
        {
          "project_summary": "Brief summary of the assessed project/change",
          "impacts": [
            {
              "category": "Impact category",
              "description": "Detailed description",
              "severity": "high|medium|low",
              "duration": "short-term|long-term",
              "cascading_effects": "Description of any cascading effects"
            }
          ],
          "overall_assessment": "Summary assessment of environmental impact"
        }
        """
        
        message = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.5,
            messages=[
                {"role": "user", "content": input_text}
            ]
        )
        
        result = {
            "success": True,
            "agent_id": self.agent_id,
            "capability": "impact_assessment",
            "content": message.content[0].text,
            "model": self.model,
        }
        
        # Try to parse as JSON
        try:
            result["json_content"] = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse impact assessment as JSON")
        
        return result
    
    async def _recommend_mitigations(self, input_data: Union[str, Dict]) -> Dict[str, Any]:
        """Recommend mitigation measures"""
        # Implementation for mitigation recommendations
        if isinstance(input_data, dict):
            input_text = json.dumps(input_data, indent=2)
        else:
            input_text = input_data
            
        system_prompt = """You are an environmental mitigation specialist. Based on the described project and identified impacts, recommend effective mitigation measures.
        
        For each recommended measure:
        1. Describe the mitigation approach clearly
        2. Explain how it addresses specific impacts
        3. Note any limitations or considerations
        4. Indicate the expected effectiveness (high/medium/low)
        
        Focus on practical, established mitigation techniques. Where possible, suggest measures that can be incorporated into project design rather than add-ons. Consider cost-effectiveness where relevant.
        
        Structure your response as JSON with the following format:
        {
          "project_summary": "Brief summary of the project",
          "mitigation_measures": [
            {
              "impact_addressed": "The impact this addresses",
              "measure": "Description of the mitigation measure",
              "effectiveness": "high|medium|low",
              "implementation_considerations": "Notes on implementation",
              "monitoring_needed": "Any monitoring requirements"
            }
          ],
          "overall_strategy": "Summary of the comprehensive mitigation approach"
        }
        """
        
        message = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.5,
            messages=[
                {"role": "user", "content": input_text}
            ]
        )
        
        result = {
            "success": True,
            "agent_id": self.agent_id,
            "capability": "mitigation_recommendations",
            "content": message.content[0].text,
            "model": self.model,
        }
        
        # Try to parse as JSON
        try:
            result["json_content"] = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse mitigation recommendations as JSON")
        
        return result
    
    async def _evaluate_compliance(self, input_data: Union[str, Dict]) -> Dict[str, Any]:
        """Evaluate regulatory compliance"""
        # Implementation for compliance evaluation
        if isinstance(input_data, dict):
            input_text = json.dumps(input_data, indent=2)
        else:
            input_text = input_data
            
        system_prompt = """You are an environmental regulatory compliance specialist. Evaluate the described project against common environmental regulations and requirements.
        
        Consider compliance with:
        1. Clean Water Act requirements
        2. Clean Air Act provisions
        3. Endangered Species Act considerations
        4. Wetland protection regulations
        5. Environmental Impact Assessment requirements
        6. Stormwater management regulations
        7. Hazardous material management requirements
        
        For each regulatory area:
        1. Identify potential compliance issues
        2. Note additional information needed for full assessment
        3. Suggest documentation or permits likely needed
        
        Structure your response as JSON with the following format:
        {
          "project_summary": "Brief summary of the project",
          "compliance_areas": [
            {
              "regulation": "Regulatory area",
              "compliance_status": "likely_compliant|potential_issues|additional_info_needed|likely_non_compliant",
              "issues": "Description of any issues",
              "required_actions": "Actions needed for compliance",
              "documentation_needed": "Required permits or documentation"
            }
          ],
          "overall_compliance": "Summary of overall compliance status"
        }
        """
        
        message = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.5,
            messages=[
                {"role": "user", "content": input_text}
            ]
        )
        
        result = {
            "success": True,
            "agent_id": self.agent_id,
            "capability": "regulatory_compliance",
            "content": message.content[0].text,
            "model": self.model,
        }
        
        # Try to parse as JSON
        try:
            result["json_content"] = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse compliance evaluation as JSON")
        
        return result

class ZoningAnalysisAgent(OpenAIAgent):
    """
    Specialized agent for analyzing zoning regulations and land use compatibility
    """
    
    def __init__(self):
        """Initialize the ZoningAnalysisAgent"""
        super().__init__(
            agent_id="zoning_analysis_agent",
            agent_type=AgentType.GEOSPATIAL_ANALYSIS,
            description="Analyzes zoning regulations and evaluates land use compatibility"
        )
        
        # Override capabilities
        self.capabilities = []
        self.register_capability(
            "zoning_interpretation", 
            "Interpret and explain zoning regulations"
        )
        self.register_capability(
            "use_compatibility", 
            "Evaluate compatibility of proposed uses with zoning"
        )
        self.register_capability(
            "variance_analysis", 
            "Analyze potential for zoning variances"
        )
    
    # Implementation of process and specialized functions would be similar to other agents

# Factory function to create all specialized agents
def create_all_specialized_agents() -> List[BaseAgent]:
    """
    Create all specialized AI agents
    
    Returns:
        List of specialized agent instances
    """
    return [
        GeoParsingAgent(),
        EnvironmentalImpactAgent(),
        ZoningAnalysisAgent()
    ]