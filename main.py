import logging
import os
import asyncio
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from prometheus_flask_exporter import PrometheusMetrics

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the base class
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__, 
            static_folder="app/static",
            template_folder="app/templates")

# Configure the application
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database with the app
db.init_app(app)

# Initialize Prometheus metrics
metrics = PrometheusMetrics(app, group_by='endpoint')
metrics.info('terrafusion_info', 'TerraFusion Platform Information', 
             version='1.0.0', service='terrafusion-api')

# Import AI agent routes
try:
    from services.ai_agents.routes import register_agent_routes
    # Register AI agent routes immediately to avoid "already handled request" errors
    register_agent_routes(app)
    logger.info("AI agent routes registered")
    has_ai_agents = True
    
    # Import AI agent UI routes
    from app.routes.ai_agent_routes import register_ai_agent_ui_routes
    register_ai_agent_ui_routes(app)
    logger.info("AI agent UI routes registered")
except ImportError:
    logger.warning("AI agent modules not available")
    has_ai_agents = False

# Create routes for main pages
@app.route('/')
def index():
    return render_template('apple_dashboard.html')  # Using Apple-inspired dashboard

@app.route('/login')
def login():
    return render_template('login_standalone.html')

@app.route('/map')
def map_view():
    return render_template('map.html')

@app.route('/flow')
def flow():
    return render_template('flow.html')

@app.route('/insight')
def insight():
    return render_template('insight.html')

@app.route('/audit')
def audit():
    return render_template('audit.html')

# API routes - simplified for now
@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    # Check if we have JSON data
    if request.is_json:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
    else:
        # Form data
        username = request.form.get('username', '')
        password = request.form.get('password', '')
    
    # For demo purposes, accept any login (would use County authentication in production)
    if username and password:
        # In a real system, we would validate against County network authentication
        # For now, simulate successful login for any credentials
        return jsonify({
            "status": "success", 
            "message": "Login successful",
            "user": {
                "username": username,
                "full_name": "Demo User",
                "role": "Administrator" 
            }
        })
    else:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/api/tiles/<path:tile_path>')
def map_tiles(tile_path):
    # Simplified tile endpoint
    return jsonify({"status": "success", "message": f"Map tiles for {tile_path}"})

@app.route('/api/etl/<path:process_path>', methods=['GET', 'POST'])
def etl_process(process_path):
    # Simplified ETL endpoint
    return jsonify({"status": "success", "message": f"ETL process for {process_path}"})

@app.route('/api/ai/<path:model_path>', methods=['GET', 'POST'])
@metrics.counter('terrafusion_ai_requests_total', 'Number of AI model requests',
                labels={'model_path': lambda: request.view_args['model_path']})
def ai_model(model_path):
    # Simplified AI endpoint
    return jsonify({"status": "success", "message": f"AI model for {model_path}"})

@app.route('/api/audit/<path:audit_path>', methods=['GET', 'POST'])
def audit_api(audit_path):
    # Simplified audit endpoint
    return jsonify({"status": "success", "message": f"Audit for {audit_path}"})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and monitoring systems"""
    # Basic health check - could be expanded to check database, AI services, etc.
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "service": "terrafusion-api",
        "database": "connected" if db.engine.pool.checkedout() >= 0 else "error"
    }
    
    # Check if AI agents are available
    if has_ai_agents:
        health_status["ai_agents"] = "available"
    
    return jsonify(health_status)

# Helper function to run async tasks from sync code
def run_async(coro):
    """Run an async coroutine from sync code"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Database initialization (simplified)
with app.app_context():
    try:
        # Import models here for table creation
        import models
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Additional initialization for the application
@app.before_request
def initialize_app():
    # Only run this once, using an application flag
    if not getattr(app, '_initialization_complete', False):
        logger.info("TerraFusion Platform starting...")
        try:
            # Initialize AI Agent Manager if available
            if has_ai_agents:
                try:
                    # Import here to avoid circular imports
                    from services.ai_agents.agent_manager import get_agent_manager
                    # Initialize agent manager in a separate thread
                    # We can't use await directly in Flask, so we use a helper
                    run_async(get_agent_manager())
                    logger.info("AI Agent Manager initialized")
                except Exception as e:
                    logger.error(f"Error initializing AI Agent Manager: {e}")
            
            app._initialization_complete = True
            logger.info("TerraFusion Platform started successfully")
        except Exception as e:
            logger.error(f"Error starting TerraFusion Platform: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
