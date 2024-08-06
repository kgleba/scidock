import random
from functools import cache, wraps

from web.log import logger

__all__ = ('responsive_cache', 'random_chain')

random.seed(42)


def responsive_cache(func):  # for synchronous functions only!
    func = cache(func)

    def format_args(args) -> str:
        return ', '.join(map(repr, args))

    def format_kwargs(kwargs) -> str:
        return ', '.join(f'{k}={v!r}' for k, v in kwargs.items())

    @wraps(func)
    def notification_wrapper(*args, **kwargs):
        hits = func.cache_info().hits
        func_return = func(*args, **kwargs)
        func_args = ', '.join((format_args(args), format_kwargs(kwargs)))

        logger.debug(
            f'Cache for {func.__name__}({func_args}) {'hit' if func.cache_info().hits > hits else 'missed'}'
        )

        return func_return

    return notification_wrapper


def random_chain(*iterables, weights: list[float] | None = None):
    iterators = [iter(it) for it in iterables]

    while iterators:
        iterator = random.choices(iterators, weights, k=1)[0]

        try:
            yield next(iterator)
        except StopIteration:
            iterator_index = iterators.index(iterator)

            iterators.pop(iterator_index)
            if weights is not None:
                weights.pop(iterator_index)
