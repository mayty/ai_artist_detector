from typing import TYPE_CHECKING

from starlette.responses import JSONResponse, Response

from ai_artist_detector.api.ai_artists import check_artist, check_artists_batch

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    HANDLER_TYPE = Callable[..., Awaitable[Response]]
    HANDLERS_DICT = dict[str, HANDLER_TYPE | 'HANDLERS_DICT']


async def ping() -> Response:
    return JSONResponse(
        content='pong',
    )


GET_URLS: HANDLERS_DICT = {
    'ping': ping,
    'youtube': {'v1': {'artists': {'check': check_artist}}},
}

POST_URLS: HANDLERS_DICT = {
    'youtube': {'v1': {'artists': {'check': {'batch': check_artists_batch}}}},
}
