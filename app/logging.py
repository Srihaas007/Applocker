import logging

# Set up logging configuration
def setup_logging():
    logging.basicConfig(
        filename='logs/app_logs.log',
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

# Log an event
def log_event(message):
    logging.info(message)

# Log an error
def log_error(message):
    logging.error(message)
