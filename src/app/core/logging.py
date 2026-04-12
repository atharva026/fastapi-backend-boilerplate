import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from src.app.core.config import config

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"

def setup_logging() -> None:
    """
    Configure application-wide logging.
    Must be called ONCE during application startup.

    If log_level = logging.INFO, then DEBUG log messages
    will NOT be emitted (they are ignored).
    """

    log_level = logging.DEBUG if config.DEBUG else logging.INFO

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Prevent duplicate handlers
    if root_logger.handlers:
        return

    formatter = logging.Formatter(LOG_FORMAT)

    # Console handler (Docker / local)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (production)
    if config.LOG_TO_FILE:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-specific logger.
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
