"""
Create logging objects and functions

See https://docs.python.org/3/howto/logging.html
"""

import logging

# Setup config - doesn't work properly without this
logging.basicConfig()   # setup logging


def create_logger(name: str) -> logging.Logger:
    """Create new logger instance"""
    return logging.getLogger(name)