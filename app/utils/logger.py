import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """Configure logging with both file and console handlers."""
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Create logger
    logger = logging.getLogger('BaplieParser')
    logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler (rotating log files)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'baplie_parser.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
