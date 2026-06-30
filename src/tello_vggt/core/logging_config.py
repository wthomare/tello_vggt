"""Logging configuration for tello_vggt."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Color codes for terminal output
COLORS = {
    "DEBUG": "\033[36m",      # Cyan
    "INFO": "\033[32m",       # Green
    "WARNING": "\033[33m",    # Yellow
    "ERROR": "\033[31m",      # Red
    "CRITICAL": "\033[35m",   # Magenta
    "RESET": "\033[0m",
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output."""

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = COLORS.get(levelname, COLORS["RESET"])
        reset = COLORS["RESET"]

        # Format message
        record.levelname = f"{color}{levelname}{reset}"
        message = super().format(record)
        record.levelname = levelname  # Reset for other handlers

        return message


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    mission_id: Optional[str] = None,
    log_to_file: bool = True,
) -> logging.Logger:
    """
    Setup logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files. If None, only console logging.
        mission_id: Mission ID for per-mission log files
        log_to_file: Whether to log to file

    Returns:
        Root logger instance
    """
    # Get root logger
    root_logger = logging.getLogger("tello_vggt")
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(ColoredFormatter(console_format._fmt, console_format.datefmt))
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_to_file and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file
        log_file = log_dir / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_format = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

        # Mission-specific log file
        if mission_id:
            mission_log_file = log_dir / f"mission_{mission_id}.log"
            mission_handler = logging.FileHandler(mission_log_file)
            mission_handler.setLevel(logging.DEBUG)
            mission_handler.setFormatter(file_format)
            root_logger.addHandler(mission_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"tello_vggt.{name}")


# Convenience functions for common logging patterns

def log_section(logger: logging.Logger, title: str) -> None:
    """Log a section header."""
    logger.info(f"\n{'=' * 70}")
    logger.info(f"  {title.center(66)}")
    logger.info(f"{'=' * 70}\n")


def log_progress(logger: logging.Logger, current: int, total: int, message: str = "") -> None:
    """Log progress in a consistent format."""
    percentage = (current / total) * 100 if total > 0 else 0
    logger.info(f"Progress: {current}/{total} ({percentage:.1f}%) {message}")


def log_metrics(logger: logging.Logger, metrics: dict) -> None:
    """Log metrics in a structured format."""
    logger.info("Metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            logger.info(f"  {key}: {value:.4f}")
        else:
            logger.info(f"  {key}: {value}")
