# This file has been edited with the assistance of an AI tool.
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from ai_artist_detector.domain.youtube import YouTubeAdapterService
    from ai_artist_detector.external.soul_over_ai import SoulOverAiClient


class SoulOverAiService:
    def __init__(
        self,
        youtube_adapter_service: YouTubeAdapterService,
        soul_over_ai_client: SoulOverAiClient,
    ) -> None:
        self.youtube_adapter_service = youtube_adapter_service
        self.soul_over_ai_client = soul_over_ai_client

        self.artists_count = 0
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

    def get_ai_artists(self, ignore_aliases_cache: bool) -> set[str]:
        ai_artists = self.soul_over_ai_client.retrieve_ai_youtube_channels()
        ai_ids: set[str] = set()

        self.artists_count = len(ai_artists)
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

        for raw_artist_id in ai_artists:
            if raw_artist_id.startswith('@'):
                artist_id = self.youtube_adapter_service.get_artist_id_from_handle(raw_artist_id)
                if artist_id is None:
                    self.unresolved_handles_count += 1
                    continue
            else:
                artist_id = raw_artist_id

            ai_ids.add(artist_id)

            artist_aliases = self.youtube_adapter_service.get_artist_aliases(
                artist_id, ignore_aliases_cache=ignore_aliases_cache
            )
            ai_ids.update(artist_aliases)

        logger.info(
            'RetrievalStats',
            artists_count=len(ai_artists),
            ytm_ids_count=len(ai_ids),
            unresolved_handles_count=self.unresolved_handles_count,
            not_matched_count=self.not_matched_count,
        )

        return ai_ids
