from pydantic import BaseModel
from starlette.responses import JSONResponse, Response

from ai_artist_detector.constants import ArtistStatuses
from ai_artist_detector.containers import external


async def check_artist(artist_id: str) -> Response:
    if artist_id in external.soul_over_ai.get_ai_artists():
        return JSONResponse(content={'status': ArtistStatuses.AI})

    return JSONResponse(content={'status': ArtistStatuses.UNKNOWN})


class BatchCheckArtistsRequest(BaseModel):
    artist_ids: list[str]


async def check_artists_batch(request: BatchCheckArtistsRequest) -> Response:
    ai_artists = external.soul_over_ai.get_ai_artists()

    return JSONResponse(
        content={
            artist_id: (ArtistStatuses.AI if artist_id in ai_artists else ArtistStatuses.UNKNOWN)
            for artist_id in request.artist_ids
        }
    )
