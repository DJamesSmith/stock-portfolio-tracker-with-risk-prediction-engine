import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path


class ApplicationLogger:
    BASE_DIR = Path(__file__).resolve().parent.parent
    LOG_DIR = BASE_DIR / "logs"
    LOG_FILE = LOG_DIR / "app.log"
    MAX_LOG_BYTES = 5 * 1024 * 1024
    BACKUP_COUNT = 5

    logger = logging.getLogger("stock_risk_engine")

    if not logger.handlers:
        LOG_DIR.mkdir(exist_ok=True)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s UTC - %(levelname)s - %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S")
        formatter.converter = time.gmtime
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