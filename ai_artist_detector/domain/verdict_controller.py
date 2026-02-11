from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.lib.helpers import ttl_cache

if TYPE_CHECKING:
    from ai_artist_detector.data.redis.verdicts import VerdictsRepository
    from ai_artist_detector.domain.data_source.iimuzyka_top import IimuzykaTopService
    from ai_artist_detector.domain.data_source.soul_over_ai import SoulOverAiService


class VerdictControllerService:
    def __init__(
        self,
        soul_over_ai_service: SoulOverAiService,
        iimuzyka_top_service: IimuzykaTopService,
        verdicts_repository: VerdictsRepository,
    ) -> None:
        self.soul_over_ai_service = soul_over_ai_service
        self.iimuzyka_top_service = iimuzyka_top_service
        self.verdicts_repository = verdicts_repository

        self._ai_artists: set[str] | None = None
        self._updated_at: datetime | None = None

    async def recalculate(self) -> None:
        sources = {
            'soul_over_ai': self.soul_over_ai_service,
            'iimyzyka_top': self.iimuzyka_top_service,
        }

        ai_artists: set[str] = set()

        for source, service in sources.items():
            old_artists_count = len(ai_artists)
            logger.info('RetrievingAiArtists', source=source)
            retrieved_artists = service.get_ai_artists()
            ai_artists |= retrieved_artists
            logger.info(
                'ArtistsRetrieved', count=len(retrieved_artists), added_count=len(ai_artists) - old_artists_count
            )

        logger.info('VerdictsRecalculated', total_count=len(ai_artists))
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
                logger.info('AiVerdictsFetched', count=len(self._ai_artists))
            else:
                logger.info('NoAiVerdictsFoundForInitialLoad')

        elif (redis_updated_at := await self._get_ai_updated_at()) is None:
            logger.info('NoAiVerdictsFoundForUpdate')
        elif redis_updated_at > self._updated_at:
            logger.info('UpdatingAiVerdicts')
            self._ai_artists = await self.verdicts_repository.get_ai()
            self._updated_at = redis_updated_at
            logger.info('AiVerdictsUpdated', count=len(self._ai_artists))

        return self._ai_artists or set()
