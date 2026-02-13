import asyncio
import threading
from copy import deepcopy
from datetime import datetime, timedelta, UTC
from functools import wraps
from time import sleep
from typing import Any, cast, Protocol, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    class TextGenerator(Protocol):
        @property
        def text(self) -> str: ...


_loop = asyncio.new_event_loop()
_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_thread.start()


def async_to_sync[**ParamSpec, Ret](
    func: Callable[ParamSpec, Coroutine[Any, Any, Ret]],
) -> Callable[ParamSpec, Ret]:
    @wraps(func)
    def wrapper(*args: ParamSpec.args, **kwargs: ParamSpec.kwargs) -> Ret:
        return asyncio.run_coroutine_threadsafe(func(*args, **kwargs), _loop).result()

    return wrapper


def merge_dicts(merge_to: dict[object, object], overrides: dict[object, object]) -> None:
    for key, value in overrides.items():
        if key not in merge_to:
            merge_to[key] = value
            continue

        if merge_to[key] is None:
            merge_to[key] = value
            continue

        if type(merge_to[key]) is not type(value):
            msg = f'Cannot merge dicts with conflicting types: {key}={merge_to[key]} vs {value}'
            raise RuntimeError(msg)

        if isinstance(value, dict):
            merge_to_value = merge_to[key]
            assert isinstance(merge_to_value, dict)
            merge_dicts(merge_to_value, value)
            continue

        merge_to[key] = value


type NestedDict[T] = dict[str, 'T | NestedDict[T]']


def construct_routes[T](d: NestedDict[T]) -> dict[str, T]:
    result: dict[str, T] = {}

    for key, value in d.items():
        if isinstance(value, dict):
            for nested_key, nested_value in construct_routes(value).items():
                result[f'/{key}{nested_key}'] = nested_value
            continue

        result[f'/{key}'] = value

    return result


def ttl_cache[**ParamSpec, Ret](
    ttl: timedelta,
) -> Callable[[Callable[ParamSpec, Awaitable[Ret]]], Callable[ParamSpec, Awaitable[Ret]]]:
    def decorator(func: Callable[ParamSpec, Awaitable[Ret]]) -> Callable[ParamSpec, Awaitable[Ret]]:
        checked_at: datetime | None = None
        cached_value: Ret | None = None

        @wraps(func)
        async def wrapper(*args: ParamSpec.args, **kwargs: ParamSpec.kwargs) -> Ret:
            nonlocal checked_at, cached_value
            now = datetime.now(tz=UTC)

            if checked_at is None or (now - checked_at) > ttl:
                checked_at = now
                cached_value = await func(*args, **kwargs)

            return cast('Ret', cached_value)

        return wrapper

    return decorator


def get_first_query_param(params: list[tuple[str, str]], name: str) -> str | None:
    for param_name, param_value in params:
        if param_name == name:
            return param_value
    return None


def rate_limit[**ParamSpec, Ret](
    rps: float,
) -> Callable[[Callable[ParamSpec, Ret]], Callable[ParamSpec, Ret]]:
    def decorator(func: Callable[ParamSpec, Ret]) -> Callable[ParamSpec, Ret]:
        last_call_at = datetime.min.replace(tzinfo=UTC)
        call_wait_time = timedelta(seconds=1 / rps)

        @wraps(func)
        def wrapper(*args: ParamSpec.args, **kwargs: ParamSpec.kwargs) -> Ret:
            nonlocal last_call_at
            now = datetime.now(tz=UTC)
            since_last_call = now - last_call_at
            last_call_at = now

            if since_last_call < call_wait_time:
                time_to_wait = call_wait_time - since_last_call
                logger.debug('RateLimiterSleeping', time_to_wait=time_to_wait)
                sleep(time_to_wait.total_seconds())

            return func(*args, **kwargs)

        return wrapper

    return decorator


def singular_cache[**ParamSpec, Ret](func: Callable[ParamSpec, Ret]) -> Callable[ParamSpec, Ret]:
    first_call_args: tuple[tuple, dict] | None = None
    result: Ret | None = None

    @wraps(func)
    def wrapper(*args: ParamSpec.args, **kwargs: ParamSpec.kwargs) -> Ret:
        nonlocal first_call_args, result

        if first_call_args is None:
            first_call_args = (deepcopy(args), deepcopy(kwargs))
            result = func(*args, **kwargs)
            return result

        if args != first_call_args[0]:
            logger.error(
                'MismatchedCallArgs',
                args=args,
                first_args=first_call_args[0],
            )
            msg = 'Mismatched arguments'
            raise RuntimeError(msg)

        if kwargs != first_call_args[1]:
            logger.error(
                'MismatchedCallArgs',
                kwargs=kwargs,
                first_kwargs=first_call_args[1],
            )
            msg = 'Mismatched arguments'
            raise RuntimeError(msg)

        return cast('Ret', result)

    return wrapper
