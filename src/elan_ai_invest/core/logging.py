from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from elan_ai_invest.core.config import LoggingConfig

LOGGER_NAME = "elan_ai_invest"
CONSOLE_HANDLER_NAME = "elan_ai_invest.console"
FILE_HANDLER_NAME = "elan_ai_invest.file"


def _remove_handler(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.removeHandler(handler)
    handler.close()


def configure_logging(config: LoggingConfig, root: Path) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    level = getattr(logging, config.level.upper(), logging.INFO)
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handlers = [
        handler for handler in logger.handlers if handler.name == CONSOLE_HANDLER_NAME
    ]
    stream_handler = next(
        (handler for handler in console_handlers if type(handler) is logging.StreamHandler),
        None,
    )
    for handler in console_handlers:
        if handler is not stream_handler:
            _remove_handler(logger, handler)
    if stream_handler is None:
        stream_handler = logging.StreamHandler()
        stream_handler.set_name(CONSOLE_HANDLER_NAME)
        logger.addHandler(stream_handler)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    file_path = (root / config.file_path).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handlers = [handler for handler in logger.handlers if handler.name == FILE_HANDLER_NAME]
    file_handler = next(
        (
            handler
            for handler in file_handlers
            if isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename) == file_path
            and handler.maxBytes == config.max_bytes
            and handler.backupCount == config.backup_count
        ),
        None,
    )
    for handler in file_handlers:
        if handler is not file_handler:
            _remove_handler(logger, handler)
    if file_handler is None:
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        file_handler.set_name(FILE_HANDLER_NAME)
        logger.addHandler(file_handler)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.propagate = False
    return logger
