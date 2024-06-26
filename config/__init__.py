import atexit
import logging
import logging.config
from functools import cache
from pathlib import Path

import yaml

__all__ = ('logger',)

logger = logging.getLogger('scidock')
Path('logs').mkdir(exist_ok=True)


@cache  # ensure that the function gets called only once
def setup_logging():
    with open('config/logging.yaml') as config_file:
        log_config = yaml.load(config_file, Loader=yaml.SafeLoader)

    logging.config.dictConfig(log_config)
    queue_handler = logging.getHandlerByName('queue_handler')
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


setup_logging()
