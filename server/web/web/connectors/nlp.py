from aiohttp_client_cache import CacheBackend, CachedSession

__all__ = ('extract_names', 'extract_keywords', 'remove_stop_words')

NLP_URL = 'http://nlp:7234'

cache = CacheBackend(allowed_methods=('GET', 'POST'))


async def extract_names(query: str) -> list[str]:
    async with CachedSession(cache=cache) as session:  # noqa: SIM117
        async with session.post(f'{NLP_URL}/extract_names', json={'query': query}) as response:
            return await response.json()


async def extract_keywords(query: str) -> list[str]:
    async with CachedSession(cache=cache) as session:  # noqa: SIM117
        async with session.post(f'{NLP_URL}/extract_keywords', json={'query': query}) as response:
            return await response.json()


async def remove_stop_words(query: str) -> str:
    async with CachedSession(cache=cache) as session:  # noqa: SIM117
        async with session.post(f'{NLP_URL}/remove_stop_words', json={'query': query}) as response:
            return await response.json()
