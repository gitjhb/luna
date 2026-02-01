"""
Logging Configuration
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

logger = logging.getLogger("ai_companion")


def setup_logging():
    """Setup application logging with file and console output"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text")
    
    # Log file path - in backend directory
    log_dir = Path(__file__).parent.parent.parent  # backend/
    log_file = log_dir / "server.log"

    if log_format == "json":
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers to avoid duplicates on reload
    root_logger.handlers.clear()
    
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.info(f"Logging initialized at {log_level} level, writing to {log_file}")
