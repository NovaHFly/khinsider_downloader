import logging
from datetime import datetime
from threading import Timer
from typing import Any, Self

from .constants import CACHE_LIFESPAN_DAYS
from .util import get_object_hash

logger = logging.getLogger('khinsider-cache')


class CacheManager:
    """Caching mechanism with built-in old cache removal.

    Note: Always stop garbage collector when stopping program
    to prevent any possible side effects from loose running thread."""

    def __init__(
        self,
        lifespan: int = CACHE_LIFESPAN_DAYS * 24 * 60 * 60,
        run_garbage_collector: bool = True,
        garbage_collector_interval: int = 6 * 60 * 60,
    ) -> None:
        """
        Args:
            lifespan (int): Maximum cache lifespan. Defaults to 1 day.
            run_garbage_collector (bool): Start garbage collector from get-go.
                Defaults to True.
            garbage_collector_interval (int): Interval at which garbage
                collector will delete old cache. Defaults to 6 hours."""
        self.__table: dict[str, tuple[Any, datetime]] = {}

        self.__cache_lifespan = lifespan
        self.__cache_clear_interval = garbage_collector_interval

        self.__run_garbage_collector = run_garbage_collector

        if self.__run_garbage_collector:
            self.start_garbage_collector()

    def cache_object(self, obj: Any, key_value: Any | None = None) -> str:
        """Cache object.

        Args:
            obj (Any): Object to cache;
            key_value (Any|None): Value to use hashing function on.
                Defaults to obj.

        Returns:
            (str): key_value md5 hash.
        """
        if not key_value:
            key_value = obj

        md5_hash = get_object_hash(key_value)
        self.__table[md5_hash] = obj, datetime.now()

        return md5_hash

    def get_cached_object(self, md5_hash: str) -> Any | None:
        """Get object stored in cache.

        If no object is stored under md5_hash return None."""
        if md5_hash not in self.__table:
            return None
        return self.__table[md5_hash][0]

    def start_garbage_collector(self) -> None:
        """Start cache manager's garbage collector."""
        logger.info(
            'Started cache garbage collector. '
            f'Interval: {self.__cache_clear_interval} seconds'
        )
        self.__timer = Timer(
            self.__cache_clear_interval,
            self.delete_old_cache,
        )
        self.__timer.start()
        self.__run_garbage_collector = True

    def stop_garbage_collector(self) -> None:
        """Stop cache manager's garbage collector."""
        self.__timer.cancel()
        self.__run_garbage_collector = False
        logger.info('Cache garbage collector is stopped')

    def delete_old_cache(self) -> None:
        """Delete cached objects with too long lifespan."""
        logger.info('Deleting old cache...')

        to_delete = []
        for key, value in self.__table.items():
            if (datetime.now() - value[1]).seconds >= self.__cache_lifespan:
                to_delete.append(key)

        for key in to_delete:
            self.__table.pop(key)

        if self.__run_garbage_collector:
            self.start_garbage_collector()

        logger.info('Old cache deleted')

    def __enter__(self) -> Self:
        return self

    # TODO: Add typehints
    def __exit__(self, type, value, traceback) -> None:
        self.stop_garbage_collector()


def get_manager(key: str = 'default', *args, **kwargs) -> CacheManager:
    """Get manager with identifier [key].

    Create manager if needed using args and kwargs."""
    if key not in _running_managers:
        manager = _running_managers[key] = CacheManager(*args, **kwargs)
    return manager


_running_managers: dict[str, CacheManager] = {}
