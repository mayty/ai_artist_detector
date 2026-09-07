# This file has been edited with the assistance of an AI tool.
from sqlite3 import Error as SQLiteError

from loguru import logger
from starlette.responses import Response

from ai_artist_detector.containers import services
from ai_artist_detector.domain.metrics_service import MetricsSnapshot


async def metrics_endpoint() -> Response:
    try:
        ai_count = len(await services.verdict_controller_service.get_ai_artists())
        associated_count = len(await services.verdict_controller_service.get_associated_artists())
        last_run = await services.metrics_service.get_last_run()
        snapshot = MetricsSnapshot(
            verdicts_ai_count=ai_count, verdicts_associated_count=associated_count, last_run=last_run
        )
    except SQLiteError:
        logger.exception('MetricsRefreshFailed')
        snapshot = None
    services.metrics_service.update_snapshot(snapshot)
    content, content_type = services.metrics_service.render_latest()
    return Response(content=content, media_type=content_type)
