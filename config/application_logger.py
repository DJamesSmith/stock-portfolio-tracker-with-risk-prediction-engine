# Purpose:
# Central application-wide logger.
# Every application event should be written through ApplicationLogger.

import logging
from pathlib import Path


class ApplicationLogger:
    """Small wrapper around Python's logging module."""

    LOG_FILE = Path("app.log")

    logger = logging.getLogger("stock_tracker")

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(LOG_FILE, mode="a")
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    @classmethod
    def info(cls, message):
        cls.logger.info(message)

    @classmethod
    def warning(cls, message):
        cls.logger.warning(message)

    @classmethod
    def error(cls, message):
        cls.logger.error(message)

    @classmethod
    def exception(cls, message):
        cls.logger.exception(message)
