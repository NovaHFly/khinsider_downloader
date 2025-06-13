import logging
import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from requests.exceptions import Timeout
from tenacity import retry, retry_if_exception_type, stop_after_attempt

P = ParamSpec('P')
T = TypeVar('T')

Decorator = Callable[[Callable[P, T]], Callable[P, T]]
ExceptionGroup = tuple[Exception, ...]

global_logger = logging.getLogger('khinsider')


def log_errors(
    func: Callable[P, T] = None,
    *,
    logger: logging.Logger = None,
) -> Callable[[Callable[P, T]], Callable[P, T]] | Callable[P, T]:
    """Log exceptions raised while calling function."""
    local_logger = logger or global_logger

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                local_logger.error(
                    f'{func.__name__}(args: {args}, kwargs: {kwargs}): {e}'
                )
                raise

        return wrapper

    if func:
        return decorator(func)

    return decorator


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


retry_if_timeout = retry(
    retry=retry_if_exception_type(Timeout),
    stop=stop_after_attempt(5),
)
