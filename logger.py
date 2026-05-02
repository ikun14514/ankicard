import logging
import sys
from typing import Optional
from pathlib import Path

from config import get_config


class Logger:
    _instances = {}

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        config = get_config()
        log_config = config.get_logging_config()

        level = getattr(logging, log_config.get('level', 'INFO').upper(), logging.INFO)
        self.logger.setLevel(level)

        if not self.logger.handlers:
            formatter = logging.Formatter(log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            log_file = log_config.get('file')
            if log_file:
                try:
                    file_handler = logging.FileHandler(log_file, encoding='utf-8')
                    file_handler.setLevel(level)
                    file_handler.setFormatter(formatter)
                    self.logger.addHandler(file_handler)
                except Exception as e:
                    self.logger.warning(f"Could not create log file {log_file}: {e}")

    @classmethod
    def get_logger(cls, name: str) -> 'Logger':
        if name not in cls._instances:
            cls._instances[name] = Logger(name)
        return cls._instances[name]

    def debug(self, message: str) -> None:
        self.logger.debug(message)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False) -> None:
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False) -> None:
        self.logger.critical(message, exc_info=exc_info)


def get_logger(name: str) -> Logger:
    return Logger.get_logger(name)