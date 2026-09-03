"""
Firmware Regression Intelligence (FRI)

Central logging configuration.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fri.constants import LOG_DIR, LOG_FILE


class Logger:

    _logger = None

    @classmethod
    def get_logger(cls):

        if cls._logger is not None:
            return cls._logger

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        logger = logging.getLogger("FRI")

        logger.setLevel(logging.INFO)

        logger.propagate = False

        #
        # Prevent duplicate handlers
        #
        if logger.handlers:
            cls._logger = logger
            return logger

        formatter = logging.Formatter(

            fmt=(
                "%(asctime)s | "
                "%(levelname)-8s | "
                "%(message)s"
            ),

            datefmt="%Y-%m-%d %H:%M:%S"

        )

        #
        # Console
        #
        console = logging.StreamHandler(sys.stdout)

        console.setFormatter(formatter)

        logger.addHandler(console)

        #
        # File
        #
        logfile = logging.FileHandler(

            Path(LOG_FILE),

            mode="w",

            encoding="utf-8"

        )

        logfile.setFormatter(formatter)

        logger.addHandler(logfile)

        cls._logger = logger

        return logger


#
# Global logger
#
logger = Logger.get_logger()
