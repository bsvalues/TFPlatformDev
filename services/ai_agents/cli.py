#!/usr/bin/env python
"""
Command-line interface for testing TerraFusion AI agents directly
"""

import argparse
import asyncio
import json
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.ai_agents import AgentType
from services.ai_agents.agent_manager import get_agent_manager
from services.ai_agents.specialized_agents import GeoParsingAgent, EnvironmentalImpactAgent

async def list_agents():
    """List all available agents and their capabilities"""
    agent_manager = await get_agent_manager()
    agents = agent_manager.get_agent_info()
    
    print(f"Found {len(agents)} AI agents:\n")
    for agent in agents:
        print(f"ID: {agent['id']}")
        print(f"Type: {agent['type']}")
        print(f"Description: {agent['description']}")
        print("Capabilities:")
        for cap in agent['capabilities']:
            print(f"  - {cap['name']}: {cap['description']}")
        print()

async def query_agent(agent_id, query, options=None):
    """Run a query against a specific agent"""
    if options is None:
        options = {}
    
    try:
        agent_manager = await get_agent_manager()
        result = await agent_manager.process_with_agent(agent_id, query, options)
        
        # Pretty-print the result
        print("\n===== RESULT =====")
        print(f"Agent: {result.get('agent_id')}")
        print(f"Capability: {result.get('capability')}")
        print(f"Success: {result.get('success')}")
        
        # Print content
        print("\n--- Content ---")
        print(result.get('content', ''))
        
        # Print JSON content if available
        if 'json_content' in result:
            print("\n--- JSON Content ---")
            print(json.dumps(result['json_content'], indent=2))
    
    except Exception as e:
        print(f"Error querying agent: {e}")

async def test_geo_parsing(text):
    """Test the GeoParsingAgent with the given text"""
    agent = GeoParsingAgent()
    
    print("Testing GeoParsingAgent with coordinate extraction...")
    result = await agent.process(text, {"capability": "coordinate_extraction"})
    print("\n===== COORDINATE EXTRACTION =====")
    print(result.get('content', ''))
    
    print("\nTesting GeoParsingAgent with feature identification...")
    result = await agent.process(text, {"capability": "feature_identification"})
    print("\n===== FEATURE IDENTIFICATION =====")
    print(result.get('content', ''))

async def test_environmental_impact(description):
    """Test the EnvironmentalImpactAgent with the given project description"""
    agent = EnvironmentalImpactAgent()
    
    print("Testing EnvironmentalImpactAgent with impact assessment...")
    result = await agent.process(description, {"capability": "impact_assessment"})
    print("\n===== IMPACT ASSESSMENT =====")
    print(result.get('content', ''))
    
    print("\nTesting EnvironmentalImpactAgent with mitigation recommendations...")
    result = await agent.process(description, {"capability": "mitigation_recommendations"})
    print("\n===== MITIGATION RECOMMENDATIONS =====")
    print(result.get('content', ''))

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='TerraFusion AI Agent CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List agents command
    list_parser = subparsers.add_parser('list', help='List all available agents')
    
    # Query agent command
    query_parser = subparsers.add_parser('query', help='Query a specific agent')
    query_parser.add_argument('agent_id', help='ID of the agent to query')
    query_parser.add_argument('text', help='Text to process')
    query_parser.add_argument('--capability', help='Specific capability to use')
    query_parser.add_argument('--format', choices=['text', 'json'], default='text',
                             help='Desired output format')
    
    # Geo parsing command
    geo_parser = subparsers.add_parser('geo', help='Test GeoParsingAgent')
    geo_parser.add_argument('text', help='Text to process for geographic information')
    
    # Environmental impact command
    env_parser = subparsers.add_parser('env', help='Test EnvironmentalImpactAgent')
    env_parser.add_argument('description', help='Project description to assess')
    
    return parser.parse_args()

async def main():
    """Main CLI entry point"""
    args = parse_arguments()
    
    if args.command == 'list':
        await list_agents()
    
    elif args.command == 'query':
        options = {}
        if hasattr(args, 'capability') and args.capability:
            options['capability'] = args.capability
        if hasattr(args, 'format') and args.format == 'json':
            options['response_format'] = 'json'
        
        await query_agent(args.agent_id, args.text, options)
    
    elif args.command == 'geo':
        await test_geo_parsing(args.text)
    
    elif args.command == 'env':
        await test_environmental_impact(args.description)
    
    else:
        print("Please specify a command. Use --help for more information.")

if __name__ == '__main__':
    asyncio.run(main())