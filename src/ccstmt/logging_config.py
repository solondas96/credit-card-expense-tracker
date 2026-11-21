"""Structured logging configuration."""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: Path, name: str = "ccstmt") -> logging.Logger:
    """Set up structured logging with rotation."""
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Rotating file handler (10MB per file, keep 5 files)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / f"{name}.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler (INFO level only, no spam)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # Formatter: JSON-like but human-readable
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
