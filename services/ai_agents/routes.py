"""
API routes for TerraFusion AI agents.
"""

import asyncio
import base64
import json
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, current_app

from services.ai_agents import AgentType
from services.ai_agents.agent_manager import get_agent_manager

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint for AI agent routes
ai_agent_bp = Blueprint('ai_agent', __name__, url_prefix='/api/ai')

@ai_agent_bp.route('/agents', methods=['GET'])
def list_agents():
    """
    List all available AI agents and their capabilities
    
    Returns:
        JSON response with agent information
    """
    try:
        # Use a helper function to run the async code in a sync context
        def run_async_get_agents():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                agent_manager = loop.run_until_complete(get_agent_manager())
                return agent_manager.get_agent_info()
            finally:
                loop.close()
        
        agents = run_async_get_agents()
        return jsonify({
            "status": "success",
            "agents": agents
        })
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_agent_bp.route('/process/<agent_id>', methods=['POST'])
def process_with_agent(agent_id):
    """
    Process data with a specific agent
    
    Args:
        agent_id: ID of the agent to use
        
    Returns:
        JSON response with processing results
    """
    try:
        # Use a helper function to run the async code in a sync context
        def run_async_process():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Parse input data based on content type
                input_data, options = loop.run_until_complete(_parse_request_data(request))
                
                # Process with specified agent
                agent_manager = loop.run_until_complete(get_agent_manager())
                result = loop.run_until_complete(agent_manager.process_with_agent(agent_id, input_data, options))
                return result
            finally:
                loop.close()
        
        result = run_async_process()
        
        return jsonify({
            "status": "success",
            "result": result
        })
    except ValueError as e:
        logger.error(f"Invalid agent or request: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error processing with agent: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_agent_bp.route('/process/type/<agent_type>', methods=['POST'])
def process_with_agent_type(agent_type):
    """
    Process data with an agent of the specified type
    
    Args:
        agent_type: Type of agent to use
        
    Returns:
        JSON response with processing results
    """
    try:
        # Convert string to AgentType enum
        try:
            agent_type_enum = AgentType(agent_type)
        except ValueError:
            return jsonify({
                "status": "error",
                "message": f"Invalid agent type: {agent_type}"
            }), 400
        
        # Use a helper function to run the async code in a sync context
        def run_async_process():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Parse input data based on content type
                input_data, options = loop.run_until_complete(_parse_request_data(request))
                
                # Process with agent of specified type
                agent_manager = loop.run_until_complete(get_agent_manager())
                result = loop.run_until_complete(agent_manager.process_with_agent_type(agent_type_enum, input_data, options))
                return result
            finally:
                loop.close()
        
        result = run_async_process()
        
        return jsonify({
            "status": "success",
            "result": result
        })
    except ValueError as e:
        logger.error(f"Invalid agent type or request: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error processing with agent type: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_agent_bp.route('/process/capability/<capability>', methods=['POST'])
def process_with_capability(capability):
    """
    Process data with the best agent for a specific capability
    
    Args:
        capability: Capability needed for processing
        
    Returns:
        JSON response with processing results
    """
    try:
        # Use a helper function to run the async code in a sync context
        def run_async_process():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Parse input data based on content type
                input_data, options = loop.run_until_complete(_parse_request_data(request))
                
                # Process with best agent for capability
                agent_manager = loop.run_until_complete(get_agent_manager())
                result = loop.run_until_complete(agent_manager.process_with_best_agent(input_data, capability, options))
                return result
            finally:
                loop.close()
        
        result = run_async_process()
        
        return jsonify({
            "status": "success",
            "result": result
        })
    except ValueError as e:
        logger.error(f"Invalid capability or request: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error processing with capability: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

async def _parse_request_data(request):
    """
    Parse input data from request based on content type
    
    Args:
        request: Flask request object
        
    Returns:
        Tuple of (input_data, options)
    """
    content_type = request.headers.get('Content-Type', '')
    
    # Get options from query parameters or JSON data
    options = {}
    
    # Handle different content types
    if content_type.startswith('application/json'):
        # JSON data
        data = request.get_json(silent=True) or {}
        
        if 'options' in data:
            options = data.pop('options')
            
        if 'data' in data:
            input_data = data['data']
        else:
            input_data = data
    
    elif content_type.startswith('multipart/form-data'):
        # Form data with possible file upload
        options_json = request.form.get('options', '{}')
        try:
            options = json.loads(options_json)
        except json.JSONDecodeError:
            options = {}
            
        # Check for file upload
        if 'file' in request.files:
            file = request.files['file']
            file_content = file.read()
            
            # Determine how to handle the file based on mimetype
            if file.mimetype.startswith('image/'):
                # Image file
                input_data = file_content
            elif file.mimetype.startswith('application/json'):
                # JSON file
                try:
                    input_data = json.loads(file_content.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    input_data = {"content": base64.b64encode(file_content).decode('utf-8')}
            else:
                # Text or binary file
                try:
                    input_data = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    input_data = {"content": base64.b64encode(file_content).decode('utf-8')}
        else:
            # No file, use text data
            input_data = request.form.get('data', '')
    
    else:
        # Default to text data
        try:
            data = request.get_data()
            try:
                # Try to parse as JSON
                parsed_data = json.loads(data.decode('utf-8'))
                if 'options' in parsed_data:
                    options = parsed_data.pop('options')
                if 'data' in parsed_data:
                    input_data = parsed_data['data']
                else:
                    input_data = parsed_data
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Not valid JSON, treat as text
                input_data = data.decode('utf-8', errors='replace')
        except Exception:
            # Fallback to empty string
            input_data = ""
    
    # Get additional options from query parameters
    for key, value in request.args.items():
        if key != 'data' and key not in options:
            options[key] = value
    
    return input_data, options

def register_agent_routes(app):
    """
    Register AI agent routes with the Flask application
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(ai_agent_bp)
    logger.info("Registered AI agent routes")