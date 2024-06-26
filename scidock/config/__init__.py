import atexit
import logging
import logging.config
from functools import cache
from pathlib import Path

import yaml

__all__ = ('logger',)

logger = logging.getLogger('scidock')
Path('~/.scidock/logs').expanduser().mkdir(parents=True, exist_ok=True)


@cache  # ensure that the function gets called only once
def setup_logging():
    with open(Path(__file__).parent / 'logging.yaml') as config_file:
        log_config = yaml.load(config_file, Loader=yaml.SafeLoader)

    log_config['handlers']['file']['filename'] = str(Path(log_config['handlers']['file']['filename']).expanduser().absolute())

    logging.config.dictConfig(log_config)
    queue_handler = logging.getHandlerByName('queue_handler')
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


setup_logging()
