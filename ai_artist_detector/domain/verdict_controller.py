# This file has been edited with the assistance of an AI tool.
import asyncio
from datetime import datetime, timedelta, UTC
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.constants import DataSources
from ai_artist_detector.domain.metrics_service import IngestionRunStats
from ai_artist_detector.lib.helpers import ttl_cache
from ai_artist_detector.lib.tracking import tracking

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.verdicts import VerdictsRepository
    from ai_artist_detector.domain.data_source.explicit import ExplicitService
    from ai_artist_detector.domain.data_source.iimuzyka_top import IimuzykaTopService
    from ai_artist_detector.domain.data_source.soul_over_ai import SoulOverAiService
    from ai_artist_detector.domain.metrics_service import MetricsService


class VerdictControllerService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        enabled_sources: set[DataSources],
        soul_over_ai_service: SoulOverAiService,
        iimuzyka_top_service: IimuzykaTopService,
        explicit_service: ExplicitService,
        verdicts_repository: VerdictsRepository,
        metrics_service: MetricsService,
    ) -> None:
        self.verdicts_repository = verdicts_repository
        self.metrics_service = metrics_service

        _sources = {
            DataSources.SOUL_OVER_AI: soul_over_ai_service,
            DataSources.IIMUZYKA_TOP: iimuzyka_top_service,
            DataSources.EXPLICIT: explicit_service,
        }

        self._sources = {source: _sources[source] for source in enabled_sources}

    async def recalculate(self, ignore_aliases_cache: bool) -> None:
        started_at = datetime.now(tz=UTC)
        previous_artists = self.verdicts_repository.get_ai()
        ai_artists: set[str] = set()
        source_metrics: dict[str, dict[str, int]] = {}
        total_unresolved_handles = 0
        total_not_matched = 0
        total_retrieved = 0

        for source, service in self._sources.items():
            old_artists_count = len(ai_artists)
            logger.info('RetrievingAiArtists', source=source)
            retrieved_artists = service.get_ai_artists(ignore_aliases_cache=ignore_aliases_cache)
            added_count = len(ai_artists | retrieved_artists) - old_artists_count
            ai_artists |= retrieved_artists
            logger.info('ArtistsRetrieved', count=len(retrieved_artists), added_count=added_count)
            total_retrieved += len(retrieved_artists)
            total_unresolved_handles += service.unresolved_handles_count
            total_not_matched += service.not_matched_count
            source_metrics[source.value] = {
                'artists_count': service.artists_count,
                'ytm_ids_count': len(retrieved_artists),
                'unresolved_handles_count': service.unresolved_handles_count,
                'not_matched_count': service.not_matched_count,
            }

        stage_metrics = tracking.dump_metrics()

        finished_at = datetime.now(tz=UTC)
        logger.info('VerdictsRecalculated', total_count=len(ai_artists), stage_metrics=stage_metrics)
        self.verdicts_repository.set_ai(ai_artists)

        await self.metrics_service.record_run(
            IngestionRunStats(
                started_at=started_at,
                finished_at=finished_at,
                ingestion_run_duration_seconds=(finished_at - started_at).total_seconds(),
                ingestion_last_run_timestamp_seconds=finished_at.timestamp(),
                ingestion_artists_cached=len(ai_artists),
                ingestion_artists_new=len(ai_artists - previous_artists),
                ingestion_artist_ids_added=total_retrieved,
                ingestion_unmatched_count=total_unresolved_handles + total_not_matched,
                stage_metrics=stage_metrics,
                source_metrics=source_metrics,
            )
        )

    @ttl_cache(timedelta(minutes=1))
    async def get_ai_artists(self) -> set[str]:
        logger.info('FetchingAiVerdicts')
        ai_artists = await asyncio.to_thread(self.verdicts_repository.get_ai)
        logger.info('AiVerdictsFetched', count=len(ai_artists))
        return ai_artists
