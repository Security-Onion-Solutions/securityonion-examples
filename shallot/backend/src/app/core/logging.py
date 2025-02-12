"""Logging utilities."""
import json
import logging
import os
from typing import Optional
from ..services.settings import get_setting
from ..database import AsyncSessionLocal

# Create logs directory if it doesn't exist
os.makedirs("/app/logs/app", exist_ok=True)

# Global variables for loggers and handler
root_logger = None
logger = None
aiosqlite_logger = None
file_handler = None

def setup_logging():
    """Initial logging setup with handlers."""
    global root_logger, logger, aiosqlite_logger, file_handler
    
    # Configure root logger to control all loggers including aiosqlite
    root_logger = logging.getLogger()
    
    # Configure our application logger
    logger = logging.getLogger("shallot")
    
    # Configure aiosqlite logger
    aiosqlite_logger = logging.getLogger("aiosqlite")
    
    # File handler
    file_handler = logging.FileHandler("/app/logs/app/backend.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to loggers
    root_logger.addHandler(file_handler)
    
    # Set initial levels
    set_log_levels(logging.INFO)

def set_log_levels(level: int):
    """Set log levels for all loggers."""
    global root_logger, logger, aiosqlite_logger, file_handler
    if not all([root_logger, logger, aiosqlite_logger, file_handler]):
        setup_logging()
    
    root_logger.setLevel(level)
    logger.setLevel(level)
    aiosqlite_logger.setLevel(level)
    file_handler.setLevel(level)

# Initialize logging on module import
setup_logging()

async def update_log_levels():
    """Update log levels based on debug setting."""
    debug_enabled = await should_debug_log()
    level = logging.DEBUG if debug_enabled else logging.INFO
    set_log_levels(level)

async def should_debug_log() -> bool:
    """Check if debug logging is enabled in system settings."""
    try:
        async with AsyncSessionLocal() as db:
            setting = await get_setting(db, 'system')
            if setting and setting.value:
                settings_dict = json.loads(setting.value)
                return settings_dict.get('debugLogging', False)
    except Exception:
        pass
    return False

async def debug_log(message: str, error: Optional[Exception] = None) -> None:
    """Log a debug message if debug logging is enabled."""
    if await should_debug_log():
        await update_log_levels()
        if error:
            logger.debug(f"{message}: {str(error)}")
        else:
            logger.debug(message)
