"""
Test script for TerraFusion AI agents
"""

import asyncio
import json
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.ai_agents import AgentType
from services.ai_agents.agent_manager import get_agent_manager

async def test_agents():
    """Test the AI agents"""
    print("Initializing AI agents...")
    
    # Get the agent manager
    agent_manager = await get_agent_manager()
    
    # List all available agents
    agents = agent_manager.get_agent_info()
    print(f"Found {len(agents)} AI agents:")
    for agent in agents:
        print(f"  - {agent['id']} ({agent['type']})")
        print(f"    Description: {agent['description']}")
        print(f"    Capabilities: {', '.join(cap['name'] for cap in agent['capabilities'])}")
        print()
    
    # Test geospatial analysis with OpenAI agent
    print("\nTesting geospatial analysis...")
    try:
        result = await agent_manager.process_with_agent_type(
            AgentType.GEOSPATIAL_ANALYSIS,
            "Analyze the potential impacts of building a solar farm in a rural area adjacent to wetlands.",
            {"temperature": 0.7}
        )
        print(f"Result: {result['content'][:200]}...\n")
    except Exception as e:
        print(f"Error testing geospatial analysis: {e}")
    
    # Test document analysis with Anthropic agent
    print("\nTesting document analysis...")
    try:
        result = await agent_manager.process_with_agent_type(
            AgentType.DOCUMENT_ANALYSIS,
            "Extract key information from this zoning document: The property (Parcel #12345) is zoned R-2 Residential with a minimum lot size of 5,000 sq ft. Setbacks are: 20ft front, 10ft sides, 15ft rear. Maximum building height is 35ft.",
            {"temperature": 0.5}
        )
        print(f"Result: {result['content'][:200]}...\n")
    except Exception as e:
        print(f"Error testing document analysis: {e}")
    
    print("AI agent tests completed")

if __name__ == "__main__":
    asyncio.run(test_agents())