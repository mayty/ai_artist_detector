from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.lib.helpers import ttl_cache

if TYPE_CHECKING:
    from ai_artist_detector.data.redis.verdicts import VerdictsRepository
    from ai_artist_detector.domain.data_source.soul_over_ai import SoulOverAiService


class VerdictControllerService:
    def __init__(self, soul_over_ai_service: SoulOverAiService, verdicts_repository: VerdictsRepository) -> None:
        self.soul_over_ai_service = soul_over_ai_service
        self.verdicts_repository = verdicts_repository

        self._ai_artists: set[str] | None = None
        self._updated_at: datetime | None = None

    async def recalculate(self) -> None:
        logger.info('RecalculatingVerdicts')
        ai_artists = self.soul_over_ai_service.get_ai_artists()
        logger.info('VerdictsRecalculated', count=len(ai_artists))
        await self.verdicts_repository.set_ai(ai_artists)

    async def _get_ai_updated_at(self) -> datetime | None:
        return await self.verdicts_repository.get_ai_updated_at()

    @ttl_cache(timedelta(minutes=1))
    async def get_ai_artists(self) -> set[str]:
        if self._updated_at is None:
            self._updated_at = await self._get_ai_updated_at()
            if self._updated_at is not None:
                logger.info('FetchingAiVerdicts')
                self._ai_artists = await self.verdicts_repository.get_ai()
            else:
                logger.info('NoAiVerdictsFoundForInitialLoad')

        elif (redis_updated_at := await self._get_ai_updated_at()) is None:
            logger.info('NoAiVerdictsFoundForUpdate')
        elif redis_updated_at > self._updated_at:
            logger.info('UpdatingAiVerdicts')
            self._ai_artists = await self.verdicts_repository.get_ai()
            self._updated_at = redis_updated_at

        return self._ai_artists or set()
