from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ai_artist_detector.api.urls import GET_URLS, POST_URLS
from ai_artist_detector.containers import services
from ai_artist_detector.lib.helpers import construct_routes

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.responses import Response


async def record_timing(
    request: Request,  # pyrefly: ignore [explicit-any]
    call_next: Callable[[Request], Awaitable[Response]],  # pyrefly: ignore [explicit-any]
) -> Response:
    start = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - start
    services.metrics_service.record_http_request(request.method, request.url.path, response.status_code, duration)
    return response


def setup_api() -> FastAPI:
    app = FastAPI()

    origins = ['https://music.youtube.com', 'http://localhost:8080']

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.middleware('http')(record_timing)

    for url, handler in construct_routes(GET_URLS).items():
        app.get(url)(handler)

    for url, handler in construct_routes(POST_URLS).items():
        app.post(url)(handler)

    return app
