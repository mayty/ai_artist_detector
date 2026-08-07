from typing import TYPE_CHECKING

from starlette.responses import JSONResponse, Response

from ai_artist_detector.api.ai_artists import check_artist, check_artists_batch
from ai_artist_detector.api.metrics import metrics_endpoint

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from ai_artist_detector.lib.helpers import NestedDict

    type HANDLER_TYPE = Callable[..., Awaitable[Response]]


async def ping() -> Response:
    return JSONResponse(
        content='pong',
    )


GET_URLS: NestedDict[HANDLER_TYPE] = {
    'ping': ping,
    'metrics': metrics_endpoint,
    'youtube': {'v1': {'artists': {'check': check_artist}}},
}

POST_URLS: NestedDict[HANDLER_TYPE] = {
    'youtube': {'v1': {'artists': {'check': {'batch': check_artists_batch}}}},
}
