"""
Delivers standard logging configuration for CloudFoundry app.
"""

import logging
import sys

NEGATIVE_LEVEL = logging.ERROR


def configure_logging(log_level):
    log_formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')

    positive_handler = logging.StreamHandler(sys.stdout)
    positive_handler.addFilter(_PositiveMessageFilter())
    positive_handler.setFormatter(log_formatter)

    negative_handler = logging.StreamHandler(sys.stderr)
    negative_handler.setLevel(NEGATIVE_LEVEL)
    negative_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(positive_handler)
    root_logger.addHandler(negative_handler)


class _PositiveMessageFilter(logging.Filter):

    """
    Logging filter that allows only positive messages to pass
    """

    def filter(self, record):
        return record.levelno < NEGATIVE_LEVEL
