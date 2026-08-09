# This file has been edited with the assistance of an AI tool.
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

        self.artists_count = 0
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

    def get_ai_artists(self, ignore_aliases_cache: bool) -> set[str]:
        artist_ids: set[str] = set()

        self.artists_count = len(self.artist_ids)
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

        for artist_id in self.artist_ids:
            artist_ids.add(artist_id)

            artist_ids |= self.youtube_adapter_service.get_artist_aliases(
                artist_id, ignore_aliases_cache=ignore_aliases_cache
            )

        logger.info(
            'RetrievalStats',
            artists_count=len(self.artist_ids),
            ytm_ids_count=len(artist_ids),
            unresolved_handles_count=self.unresolved_handles_count,
            not_matched_count=self.not_matched_count,
        )

        return artist_ids
