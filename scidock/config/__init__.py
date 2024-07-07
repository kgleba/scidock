import inspect
import logging
import sys
from functools import cache
from pathlib import Path

from loguru import logger

__all__ = ('logger',)

Path('~/.scidock/logs').expanduser().mkdir(parents=True, exist_ok=True)


# source: https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


@cache  # ensure that the function gets called only once
def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level='WARNING', format='<level>{level}: {message}</level>')
    logger.add(Path('~/.scidock/logs/scidock.log').expanduser(), level='DEBUG',
               format='[{level}|{module}|L{line}] {time:DD.MM.YYYY HH:mm:ss}: {message}',
               rotation='10 MB', enqueue=True)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


setup_logging()
