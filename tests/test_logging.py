from __future__ import annotations

import logging
from pathlib import Path

import pytest

from elan_ai_invest.core.config import LoggingConfig
from elan_ai_invest.core.logging import (
    CONSOLE_HANDLER_NAME,
    FILE_HANDLER_NAME,
    LOGGER_NAME,
    configure_logging,
)


def _owned_handlers() -> list[logging.Handler]:
    logger = logging.getLogger(LOGGER_NAME)
    return [
        handler
        for handler in logger.handlers
        if handler.name in {CONSOLE_HANDLER_NAME, FILE_HANDLER_NAME}
    ]


@pytest.fixture(autouse=True)
def clean_owned_handlers():
    logger = logging.getLogger(LOGGER_NAME)
    for handler in _owned_handlers():
        logger.removeHandler(handler)
        handler.close()
    yield
    for handler in _owned_handlers():
        logger.removeHandler(handler)
        handler.close()


def test_logging_configuration_is_idempotent(tmp_path: Path) -> None:
    config = LoggingConfig(file_path="logs/first.log")

    configure_logging(config, tmp_path)
    first_ids = {id(handler) for handler in _owned_handlers()}
    configure_logging(config, tmp_path)

    assert len(_owned_handlers()) == 2
    assert {id(handler) for handler in _owned_handlers()} == first_ids


def test_logging_reconfiguration_moves_the_file_handler(tmp_path: Path) -> None:
    configure_logging(LoggingConfig(file_path="logs/first.log"), tmp_path)
    configure_logging(LoggingConfig(file_path="other/second.log"), tmp_path)

    file_handler = next(
        handler for handler in _owned_handlers() if handler.name == FILE_HANDLER_NAME
    )
    assert Path(file_handler.baseFilename) == (tmp_path / "other/second.log").resolve()
    assert len(_owned_handlers()) == 2


def test_logging_reconfiguration_updates_levels(tmp_path: Path) -> None:
    logger = configure_logging(LoggingConfig(level="WARNING"), tmp_path)

    assert logger.level == logging.WARNING
    assert all(handler.level == logging.WARNING for handler in _owned_handlers())
