# -*- coding: utf-8 -*-
"""Project logging configuration."""
import os
from datetime import datetime

from botpy import logging


def setup_logging(*args, **kwargs) -> None:
    """Store botpy log files under logs/YYYY-MM-DD for this process."""
    log_date = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join("logs", log_date)
    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.DEFAULT_FILE_HANDLER.copy()
    file_handler["filename"] = os.path.join(log_dir, "%(name)s.log")

    logging.configure_logging(ext_handlers=file_handler)
    logging.get_logger(__name__).info("Logging to %s", log_dir)


def get_logger(name: str = None):
    if name is None:
        return logging.get_logger()
    return logging.get_logger(name)
