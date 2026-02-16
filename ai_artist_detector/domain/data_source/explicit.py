from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from ai_artist_detector.domain.youtube import YouTubeAdapterService


class ExplicitService:
    def __init__(
        self,
        artist_ids: set[str],
        youtube_adapter_service: YouTubeAdapterService,
    ) -> None:
        self.youtube_adapter_service = youtube_adapter_service
        self.artist_ids = artist_ids

    def get_ai_artists(self, ignore_aliases_cache: bool) -> set[str]:
        artist_ids: set[str] = set()

        self.youtube_adapter_service.reset_stats()
        for artist_id in self.artist_ids:
            artist_ids.add(artist_id)

            artist_ids |= self.youtube_adapter_service.get_artist_aliases(
                artist_id, ignore_aliases_cache=ignore_aliases_cache
            )

        logger.info(
            'RetrievalStats',
            rate_limit_errors=self.youtube_adapter_service.failed_rate_limit_count,
            artists_count=len(self.artist_ids),
            ytm_ids_count=len(artist_ids),
            aliases_update=self.youtube_adapter_service.aliases_cache_updated_count,
            search_update=self.youtube_adapter_service.search_cache_updated_count,
            handles_update=self.youtube_adapter_service.handles_cache_updated_count,
        )

        return artist_ids
