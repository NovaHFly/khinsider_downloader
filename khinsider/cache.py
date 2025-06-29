import logging
import multiprocessing
import time
from datetime import datetime
from typing import Any, Self

from .constants import CACHE_LIFESPAN_DAYS
from .util import get_object_hash

logger = logging.getLogger('khinsider-cache')


class CacheManager:
    __instance: Self | None = None

    """Caching mechanism with built-in old cache removal.

    Note: Always stop garbage collector when stopping program
    to prevent any possible side effects from loose running thread."""

    def __init__(
        self,
        lifespan: int = CACHE_LIFESPAN_DAYS * 24 * 60 * 60,
        garbage_collector_active: bool = True,
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
        self.__garbage_collector_interval = garbage_collector_interval

        if garbage_collector_active:
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

    def _run_garbage_collector(self) -> None:
        while True:
            time.sleep(self.__garbage_collector_interval)
            self.delete_old_cache()

    def start_garbage_collector(self) -> None:
        """Start cache manager's garbage collector."""
        logger.info(
            'Started cache garbage collector. '
            f'Interval: {self.__garbage_collector_interval} seconds'
        )
        self.__collector_process = multiprocessing.Process(
            target=self._run_garbage_collector
        )
        self.__collector_process.start()

    def stop_garbage_collector(self) -> None:
        """Stop cache manager's garbage collector."""
        self.__collector_process.terminate()
        self.__collector_process.join()
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

        logger.info('Old cache deleted')

    def __enter__(self) -> Self:
        return self

    # TODO: Add typehints
    def __exit__(self, type, value, traceback) -> None:
        self.stop_garbage_collector()

    @classmethod
    def get_manager(cls, *args, **kwargs) -> Self:
        """Get running cache manager or create new.

        Args:
            lifespan (int): Maximum cache lifespan. Defaults to 1 day.
            run_garbage_collector (bool): Start garbage collector from get-go.
                Defaults to True.
            garbage_collector_interval (int): Interval at which garbage
                collector will delete old cache. Defaults to 6 hours."""
        if cls.__instance:
            return cls.__instance

        cls.__instance = cls(*args, **kwargs)
        return cls.__instance
