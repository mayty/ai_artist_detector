from pydantic import BaseModel
from starlette.responses import JSONResponse, Response

from ai_artist_detector.constants import ArtistStatuses, EndpointLabels
from ai_artist_detector.containers import services


async def check_artist(artist_id: str) -> Response:
    services.metrics_service.record_artist_ids_requested(EndpointLabels.CHECK, 1)
    if artist_id in await services.verdict_controller_service.get_ai_artists():
        services.metrics_service.record_artist_ids_checked_ai(EndpointLabels.CHECK, 1)
        return JSONResponse(content={'status': ArtistStatuses.AI})

    return JSONResponse(content={'status': ArtistStatuses.UNKNOWN})


class BatchCheckArtistsRequest(BaseModel):
    artist_ids: list[str]


async def check_artists_batch(request: BatchCheckArtistsRequest) -> Response:
    services.metrics_service.record_artist_ids_requested(EndpointLabels.BATCH, len(request.artist_ids))
    ai_artists = await services.verdict_controller_service.get_ai_artists()

    ai_matches = {artist_id: ArtistStatuses.AI for artist_id in request.artist_ids if artist_id in ai_artists}
    services.metrics_service.record_artist_ids_checked_ai(EndpointLabels.BATCH, len(ai_matches))

    return JSONResponse(content=ai_matches)
