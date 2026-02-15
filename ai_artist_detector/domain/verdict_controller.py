from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.constants import DataSources
from ai_artist_detector.lib.helpers import ttl_cache

if TYPE_CHECKING:
    from ai_artist_detector.data.redis.verdicts import VerdictsRepository
    from ai_artist_detector.domain.data_source.explicit import ExplicitService
    from ai_artist_detector.domain.data_source.iimuzyka_top import IimuzykaTopService
    from ai_artist_detector.domain.data_source.soul_over_ai import SoulOverAiService


class VerdictControllerService:
    def __init__(
        self,
        enabled_sources: set[DataSources],
        soul_over_ai_service: SoulOverAiService,
        iimuzyka_top_service: IimuzykaTopService,
        explicit_service: ExplicitService,
        verdicts_repository: VerdictsRepository,
    ) -> None:
        self.verdicts_repository = verdicts_repository

        _sources = {
            DataSources.SOUL_OVER_AI: soul_over_ai_service,
            DataSources.IIMUZYKA_TOP: iimuzyka_top_service,
            DataSources.EXPLICIT: explicit_service,
        }

        self._sources = {source: _sources[source] for source in enabled_sources}

        self._ai_artists: set[str] | None = None
        self._updated_at: datetime | None = None

    async def recalculate(self, ignore_aliases_cache: bool) -> None:
        ai_artists: set[str] = set()

        for source, service in self._sources.items():
            old_artists_count = len(ai_artists)
            logger.info('RetrievingAiArtists', source=source)
            retrieved_artists = service.get_ai_artists(ignore_aliases_cache=ignore_aliases_cache)
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
