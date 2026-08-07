# This file has been created with the assistance of an AI tool.
from enum import auto, StrEnum
from typing import TYPE_CHECKING

from ai_artist_detector.constants import RedisNamespaces
from ai_artist_detector.domain.metrics_service import IngestionRunStats

if TYPE_CHECKING:
    from redis.asyncio import Redis


class MetricsKeys(StrEnum):
    LAST_RUN = auto()


class MetricsRepository:
    namespace = RedisNamespaces.METRICS

    def __init__(self, redis: Redis[str]) -> None:
        self.redis = redis

    async def record_run(self, stats: IngestionRunStats) -> None:
        await self.redis.set(f'{self.namespace}:{MetricsKeys.LAST_RUN}', stats.model_dump_json())

    async def get_last_run(self) -> IngestionRunStats | None:
        last_run_raw = await self.redis.get(f'{self.namespace}:{MetricsKeys.LAST_RUN}')

        if last_run_raw is None:
            return None

        return IngestionRunStats.model_validate_json(last_run_raw)
