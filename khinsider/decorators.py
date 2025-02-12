import logging
import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec('P')
T = TypeVar('T')

Decorator = Callable[[Callable[P, T]], Callable[P, T]]
ExceptionGroup = tuple[Exception, ...]

logger = logging.getLogger('khinsider')


def log_errors(func: Callable[P, T] = None) -> Callable[P, T]:
    """Log exceptions raised while calling function."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f'{func.__name__}(args: {args}, kwargs: {kwargs}): {e}'
            )
            raise

    return wrapper


def log_time(func: Callable[P, T]) -> Callable[P, T]:
    """Log real time elapsed by function call."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(
            f'{func.__name__} took {end_time - start_time:.2f} seconds'
        )
        return result

    return wrapper
