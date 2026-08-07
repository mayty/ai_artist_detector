# This file has been created with the assistance of an AI tool.
from loguru import logger
from redis.exceptions import RedisError
from starlette.responses import Response

from ai_artist_detector.containers import repositories, services
from ai_artist_detector.domain.metrics_service import MetricsSnapshot


async def metrics_endpoint() -> Response:
    try:
        ai_count = len(await repositories.redis_verdicts_repository.get_ai())
        last_run = await repositories.metrics_repository.get_last_run()
        snapshot = MetricsSnapshot(verdicts_ai_count=ai_count, last_run=last_run)
    except RedisError:
        logger.exception('MetricsRefreshFailed')
        snapshot = None
    services.metrics_service.update_snapshot(snapshot)
    content, content_type = services.metrics_service.render_latest()
    return Response(content=content, media_type=content_type)
