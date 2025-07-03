import logging
import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from requests.exceptions import Timeout
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .cache import CacheManager
from .util import get_object_md5

P = ParamSpec('P')
T = TypeVar('T')


global_logger = logging.getLogger('khinsider')


def log_errors(
    *, logger: logging.Logger | None = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Log exceptions raised during function execution.

    :param Logger | None logger: Logger to use.
        Default is the global logger.
    """
    local_logger = logger or global_logger

    def _decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                local_logger.error(
                    f'{func.__name__}(args: {args}, kwargs: {kwargs}): {e}'
                )
                raise

        return _wrapper

    return _decorator


def log_inputs(
    *,
    logger: logging.Logger,
    level: int = logging.DEBUG,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Log function's inputs.

    :param Logger | None logger: Logger to use.
        Default is the global logger.
    :param int level: logging level to log messages under. Default is DEBUG.
    """
    local_logger = logger or global_logger

    def _decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            local_logger.log(
                level, f'{func.__name__}(args: {args}, kwargs: {kwargs})'
            )
            return func(*args, **kwargs)

        return _wrapper

    return _decorator


def log_outputs(
    *,
    logger: logging.Logger | None = None,
    level: int = logging.DEBUG,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Log function's output.

    :param Logger | None logger: Logger to use.
        Default is the global logger.
    :param int level: logging level to log messages under. Default is DEBUG.
    """
    local_logger = logger or global_logger

    def _decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            out = func(*args, **kwargs)
            local_logger.log(
                level,
                f'{func.__name__}(args: {args}, kwargs: {kwargs}) -> {out}',
            )
            return out

        return _wrapper

    return _decorator


def log_time(func: Callable[P, T]) -> Callable[P, T]:
    """Log real time elapsed by function call."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        global_logger.info(
            f'{func.__name__} took {end_time - start_time:.2f} seconds'
        )
        return result

    return wrapper


def cache(func: Callable[P, T]) -> Callable[P, T]:
    """Cache function call result."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        cache_manager = CacheManager.get_manager()
        call_signature = f'{func.__name__}/{args}/{kwargs}'

        if cached_value := cache_manager.get_cached_object(
            get_object_md5(call_signature)
        ):
            return cached_value

        result = func(*args, **kwargs)
        cache_manager.cache_object(result, key_value=call_signature)

        return result

    return wrapper


retry_if_timeout = retry(
    retry=retry_if_exception_type(Timeout),
    stop=stop_after_attempt(5),
)
