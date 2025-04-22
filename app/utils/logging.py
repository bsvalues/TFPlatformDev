import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    """
    Configure logging for the application
    """
    # Get log level from environment or use DEBUG by default
    log_level_name = os.environ.get("LOG_LEVEL", "DEBUG")
    log_level = getattr(logging, log_level_name.upper(), logging.DEBUG)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Create formatters
    verbose_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    )
    simple_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] - %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    
    # File handler
    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        file_handler = RotatingFileHandler(
            "logs/terrafusion.log", 
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(verbose_formatter)
        
        # Add file handler to root logger
        root_logger.addHandler(file_handler)
    except Exception as e:
        logging.warning(f"Failed to create file handler for logs: {e}")
    
    # Add console handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set levels for some noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Log configuration complete
    logging.info(f"Logging configured with level {log_level_name}")
