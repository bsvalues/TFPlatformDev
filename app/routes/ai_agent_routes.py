"""
AI Agent routes for the TerraFusion Platform.
Provides web UI for interacting with AI agents.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any

from flask import Blueprint, render_template, jsonify, request, redirect, url_for

from services.ai_agents.agent_manager import get_agent_manager

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint for AI agent UI routes
ai_agent_ui_bp = Blueprint('ai_agent_ui', __name__, url_prefix='/ai')

def run_async(coro):
    """Run an async coroutine from sync code"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@ai_agent_ui_bp.route('/agents')
def agents_list():
    """
    Display the list of available AI agents
    
    Returns:
        Rendered template with agent information
    """
    try:
        # Use helper function to run the async code in a sync context
        agent_manager = run_async(get_agent_manager())
        agents = agent_manager.get_agent_info()
        
        # Count agents by type
        anthropic_count = sum(1 for agent in agents if "anthropic" in agent['id'])
        openai_count = sum(1 for agent in agents if "openai" in agent['id'])
        specialized_count = sum(1 for agent in agents if not ("anthropic" in agent['id'] or "openai" in agent['id']))
        
        return render_template(
            'ai_agents/index.html',
            agents=agents,
            anthropic_count=anthropic_count,
            openai_count=openai_count,
            specialized_count=specialized_count
        )
    except Exception as e:
        logger.error(f"Error displaying agents: {e}")
        return render_template('error.html', error=str(e))

@ai_agent_ui_bp.route('/agents/<agent_id>')
def agent_detail(agent_id):
    """
    Display detailed information about a specific agent
    
    Args:
        agent_id: ID of the agent to display
        
    Returns:
        Rendered template with agent details
    """
    try:
        # Use helper function to run the async code in a sync context
        agent_manager = run_async(get_agent_manager())
        agents = agent_manager.get_agent_info()
        
        # Find the agent with the given ID
        agent = next((a for a in agents if a['id'] == agent_id), None)
        
        if not agent:
            return redirect(url_for('ai_agent_ui.agents_list'))
            
        # For demonstration, create some example history
        # In a real implementation, this would come from a database
        history = [
            {
                'id': '1',
                'prompt': 'Analyze the impact of building a solar farm near wetlands at coordinates 37.7749° N, 122.4194° W.',
                'response': 'The proposed solar farm near wetlands at coordinates 37.7749° N, 122.4194° W presents significant environmental concerns. These wetlands likely provide critical habitat for diverse species and offer flood protection. Solar development could disrupt hydrology, wildlife corridors, and potentially release sediments into waterways. The site appears to be in the San Francisco area, suggesting high land value and possible alternative locations. Recommendations include seeking alternative locations, conducting environmental impact studies, incorporating buffer zones (minimum 100m), using elevated panel designs to maintain ground vegetation, and implementing comprehensive stormwater management plans.',
                'timestamp': 'April 23, 2025 10:15 AM'
            },
            {
                'id': '2',
                'prompt': 'What zoning considerations apply to building a commercial structure in a C-2 district adjacent to residential properties?',
                'response': 'Building a commercial structure in a C-2 (Commercial) district adjacent to residential properties involves several key zoning considerations: 1) Buffer requirements - typically 15-30 ft landscaped buffers, 8 ft opaque fencing/walls, and possibly berms; 2) Height restrictions - often 35-45 ft maximum with additional setbacks for taller portions; 3) Setbacks - larger than normal rear/side setbacks adjacent to residential zones (15-30 ft); 4) Operational restrictions - limited hours (often 7am-10pm), regulated deliveries, noise limits of ~60dB at property line; 5) Lighting controls - full cutoff fixtures, maximum 0.5 footcandles at residential property lines; 6) Traffic management - entrance/exit placement away from residential streets; 7) Parking requirements - higher ratios plus screening requirements; 8) Uses - restricted higher-impact uses requiring additional reviews. Always consult the specific local zoning code and consider applying for a Planned Unit Development for more flexible design solutions.',
                'timestamp': 'April 23, 2025 11:30 AM'
            }
        ]
            
        return render_template(
            'ai_agents/detail.html',
            agent=agent,
            history=history
        )
    except Exception as e:
        logger.error(f"Error displaying agent details: {e}")
        return render_template('error.html', error=str(e))

@ai_agent_ui_bp.route('/agents/docs')
def agent_docs():
    """
    Display AI agent documentation
    
    Returns:
        Rendered template with documentation
    """
    return render_template('ai_agents/documentation.html')

def register_ai_agent_ui_routes(app):
    """
    Register AI agent UI routes with the Flask application
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(ai_agent_ui_bp)
    logger.info("Registered AI agent UI routes")