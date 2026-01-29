from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_artist_detector.api.urls import GET_URLS, POST_URLS
from ai_artist_detector.lib.helpers import construct_routes


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

    for url, handler in construct_routes(GET_URLS).items():
        app.get(url)(handler)

    for url, handler in construct_routes(POST_URLS).items():
        app.post(url)(handler)

    return app
