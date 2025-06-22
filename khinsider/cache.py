from datetime import datetime
from hashlib import md5
from threading import Timer
from typing import Any

from .constants import CACHE_LIFESPAN_DAYS


class CacheManager:
    def __init__(
        self,
        lifespan: int = CACHE_LIFESPAN_DAYS * 24 * 60 * 60,
        run_garbage_collector: bool = True,
        garbage_collector_interval: int = 6 * 60 * 60,
    ):
        self.__table: dict[str, tuple[Any, datetime]] = {}

        self.__cache_lifespan = lifespan
        self.__cache_clear_interval = garbage_collector_interval

        self.__run_garbage_collector = run_garbage_collector

        if self.__run_garbage_collector:
            self.start_garbage_collector()

    def get_hash(self, value: Any) -> str:
        return md5(str(value).encode()).hexdigest()

    def cache_value(self, value: Any, key_value: Any | None = None) -> str:
        if not key_value:
            key_value = value

        md5_hash = self.get_hash(key_value)
        self.__table[md5_hash] = value, datetime.now()

        return md5_hash

    def get_cached_value(self, md5_hash: str) -> Any | None:
        if md5_hash not in self.__table:
            return None
        return self.__table[md5_hash][0]

    def start_garbage_collector(self) -> None:
        self.__timer = Timer(
            self.__cache_clear_interval,
            self.delete_old_cache,
        )
        self.__timer.start()

    def stop_garbage_collector(self) -> None:
        self.__timer.cancel()

    def delete_old_cache(self) -> None:
        to_delete = []
        for key, value in self.__table.items():
            if (datetime.now() - value[1]).seconds >= self.__cache_lifespan:
                to_delete.append(key)

        for key in to_delete:
            self.__table.pop(key)

        if self.__run_garbage_collector:
            self.start_garbage_collector()


_manager: CacheManager | None = None


def get_manager() -> CacheManager:
    global _manager

    if not _manager:
        _manager = CacheManager()
    return _manager
