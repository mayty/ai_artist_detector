import asyncio
import threading
from functools import wraps
from typing import Any, Protocol, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

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


T = TypeVar('T')
NestedDict = dict[str, 'T | NestedDict[T]']


def construct_routes[T](d: NestedDict[T]) -> dict[str, T]:
    result: dict[str, T] = {}

    for key, value in d.items():
        if isinstance(value, dict):
            for nested_key, nested_value in construct_routes(value).items():
                result[f'/{key}{nested_key}'] = nested_value
            continue

        result[f'/{key}'] = value

    return result
