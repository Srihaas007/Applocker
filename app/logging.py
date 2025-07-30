import logging
from logging.handlers import RotatingFileHandler
from app.config import LOG_FILE, LOG_FORMAT, LOG_LEVEL, MAX_LOG_SIZE, BACKUP_COUNT

# Set up logging configuration with rotation
def setup_logging():
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Create console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        handlers=[file_handler, console_handler],
        format=LOG_FORMAT
    )

# Log an event
def log_event(message):
    logging.info(message)

# Log an error
def log_error(message):
    logging.error(message)

# Log a warning
def log_warning(message):
    logging.warning(message)

# Log debug information
def log_debug(message):
    logging.debug(message)
