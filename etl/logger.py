"""
etl/logger.py
Cấu hình logging dùng chung cho toàn pipeline.
"""

import logging
import os
from datetime import datetime
import colorlog

from config import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)

_LOG_FILE = os.path.join(LOG_DIR, f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

def get_logger(name: str) -> logging.Logger:
    """Trả về logger và ghi file."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler (màu)
    ch = colorlog.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_red",
        }
    ))

    # File handler (plain)
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger
