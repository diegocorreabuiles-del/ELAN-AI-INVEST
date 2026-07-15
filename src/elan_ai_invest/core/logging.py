from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from elan_ai_invest.core.config import LoggingConfig


def configure_logging(config: LoggingConfig, root: Path) -> logging.Logger:
    logger = logging.getLogger("elan_ai_invest")
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_path = root / config.file_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger
