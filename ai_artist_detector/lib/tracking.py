# This file has been created with the assistance of an AI tool.
from copy import copy
from functools import wraps
from re import sub
from typing import cast, overload, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Types whose instances are safe to return by value (no defensive copy needed).
_IMMUTABLE_TYPES = (type(None), bool, int, float, str, tuple, frozenset)


class CacheHit[T = object](Exception):  # noqa: N818 - control-flow signal, not an error
    """Raised by a pipeline stage when its result is served from cache."""

    def __init__(self, value: T) -> None:
        super().__init__()
        self.value = value


class StageFailed(Exception):  # noqa: N818 - control-flow signal, not an error
    """Raised by a pipeline stage when the operation failed for a known reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# Class names whose acronym-ish casing the snake_case regex below would mangle
# (`YouTubeAdapterService` → `you_tube_adapter`).
_CLASS_PREFIX_OVERRIDES = {'YouTubeAdapterService': 'youtube_adapter'}


def _derive_prefix(func: Callable[..., object]) -> str:
    """
    Extract a snake_case stage namespace from the decorated function's owner class.

    `YouTubeAdapterService.get_artist_id_from_handle` → `youtube_adapter`
    """
    qualname = func.__qualname__
    owner = qualname.split('.')[0] if '.' in qualname else func.__module__.split('.')[-1]
    if owner in _CLASS_PREFIX_OVERRIDES:
        return _CLASS_PREFIX_OVERRIDES[owner]
    return sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', owner).lower().removesuffix('_service')


class TrackingService:
    """
    Accumulates per-stage metrics for a single ingestion run.

    Decorated stages signal their outcome by raising `CacheHit` (result served
    from cache) or `StageFailed` (operation failed for a reason). Any normal
    return is counted as a successful attempt. One process equals one run, so
    the tracker accumulates until `dump_metrics()` is called.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, dict[str, int]] = {}

    @overload
    def stage_metrics[**P, T](
        self, name: str, default: None
    ) -> Callable[[Callable[P, T | None]], Callable[P, T | None]]: ...

    @overload
    def stage_metrics[**P, T](self, name: str, default: T) -> Callable[[Callable[P, T]], Callable[P, T]]: ...

    def stage_metrics[**P, T](self, name: str, default: T) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Track a pipeline stage under `cache_hits` / `successful` / `failed_<reason>`.

        - `raise CacheHit(value)` → increments `cache_hits`, returns `value`
        - `raise StageFailed(reason)` → increments `failed_{reason}`, returns `default`
        - normal return → increments `successful`, returns the value
        """

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            full_name = f'{_derive_prefix(func)}.{name}'
            if full_name in self._metrics:
                msg = f'Stage {full_name} already exists'
                raise ValueError(msg)
            self._metrics[full_name] = {}
            stage = self._metrics[full_name]

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                try:
                    result = func(*args, **kwargs)
                except CacheHit as exc:
                    stage['cache_hits'] = stage.get('cache_hits', 0) + 1
                    return cast('CacheHit[T]', exc).value
                except StageFailed as exc:
                    key = f'failed_{exc.reason}'
                    stage[key] = stage.get(key, 0) + 1
                    if not isinstance(default, _IMMUTABLE_TYPES):
                        return copy(default)
                    return default
                else:
                    stage['successful'] = stage.get('successful', 0) + 1
                    return result

            return wrapper

        return decorator

    def dump_metrics(self) -> dict[str, dict[str, int]]:
        """Return a copy of all accumulated metrics: `{stage_name: {category: count}}`."""
        return {k: dict(v) for k, v in self._metrics.items()}


tracking = TrackingService()
