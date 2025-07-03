import logging
import multiprocessing
import time
from datetime import datetime
from typing import Any, Self

from .constants import CACHE_LIFESPAN_DAYS, DAY_SECONDS, HOUR_SECONDS
from .util import get_object_md5

logger = logging.getLogger('khinsider-cache')


class CacheManager:
    """Caching mechanism with built-in garbage collector.

    Manager should be instantiated using the :meth:`get_manager` method.

    Before caching object (or key value) is converted into string
    and encoded using md5. This md5 hash is used as a key under
    which the object is stored.

    Every interval the garbage collector (if it is running) checks all objects
    in storage. If they are stored for more than specified lifespan they are
    removed from cache.

    Methods:
    - :meth:`cache_object`: saves object in cache;
    - :meth:`get_cached_object`: retrieves object from cache if exists;
    - :meth:`delete_old_cache`: delete cache which lifespan exceeds
        the maximum allowed;
    - :meth:`stop_garbage_collector`: force stop the garbage collector.
    - :meth:`get_manager`: Create (or retrieve if exists) the instance of
        cache manager. This method ensures that only one cache manager
        is running at any time.
    """

    __instance: Self | None = None

    def __init__(
        self,
        lifespan: int,
        use_garbage_collector: bool,
        garbage_collector_interval: int,
    ) -> None:
        self.__table: dict[str, tuple[Any, datetime]] = {}

        self.__cache_lifespan = lifespan
        self.__garbage_collector_interval = garbage_collector_interval
        self.__collector_process: multiprocessing.Process | None = None

        if use_garbage_collector:
            self.__start_garbage_collector()

    @classmethod
    def get_manager(
        cls,
        lifespan: int = CACHE_LIFESPAN_DAYS * DAY_SECONDS,
        use_garbage_collector: bool = True,
        garbage_collector_interval: int = 6 * HOUR_SECONDS,
    ) -> Self:
        """Get running cache manager or create new.

        This method ensures that only one instance of cache manager
        is running at any time and allows to retrieve that instance
        from anywhere.

        :param int lifespan: Maximum cache lifespan in seconds.
            Default is 1 day.
        :param bool use_garbage_collector: Start garbage collector from get-go.
            Default is True
        :param int garbage_collector_interval: Interval in seconds at which
            garbage collector is scheduled to run. Default is 6 hours.
        """
        if cls.__instance:
            return cls.__instance

        cls.__instance = cls(
            lifespan=lifespan,
            use_garbage_collector=use_garbage_collector,
            garbage_collector_interval=garbage_collector_interval,
        )
        return cls.__instance

    def cache_object(self, obj: Any, key_value: Any | None = None) -> str:
        """Save the object in cache storage.

        :param Any obj: The object to be stored.
        :param Any | None key_value: The value to use as key to the object.
            Default is the object itself.
        :return str: The key under which object is stored.
        """
        if not key_value:
            key_value = obj

        md5_hash = get_object_md5(key_value)
        self.__table[md5_hash] = obj, datetime.now()

        return md5_hash

    def get_cached_object(self, key: str) -> Any | None:
        """Retrieve object stored in cache.

        :param str key: The key under which object is stored.
        :returns Any | None: The requested object.
            If key does not exist return None.
        """
        if key not in self.__table:
            return None
        return self.__table[key][0]

    def _run_garbage_collector(self) -> None:
        while True:
            time.sleep(self.__garbage_collector_interval)
            self.delete_old_cache()

    def __start_garbage_collector(self) -> None:
        logger.info(
            'Started cache garbage collector. '
            f'Interval: {self.__garbage_collector_interval} seconds'
        )
        self.__collector_process = multiprocessing.Process(
            target=self._run_garbage_collector
        )
        self.__collector_process.start()

    def stop_garbage_collector(self) -> None:
        """Force Stop cache manager's garbage collector.

        This method does nothing if cache manager was not started
        in the first place.
        """
        if not self.__collector_process:
            logger.warning(
                'Cache garbage collector is not running'
                ' or process tracking was not set!'
            )
            return
        self.__collector_process.terminate()
        self.__collector_process.join()
        self.__collector_process = None
        logger.info('Cache garbage collector is stopped')

    def delete_old_cache(self) -> None:
        """Delete objects which were cached too long ago."""
        logger.info('Deleting old cache...')

        to_delete = []
        for key, value in self.__table.items():
            if (datetime.now() - value[1]).seconds >= self.__cache_lifespan:
                to_delete.append(key)

        for key in to_delete:
            self.__table.pop(key)

        logger.info('Old cache deleted')
