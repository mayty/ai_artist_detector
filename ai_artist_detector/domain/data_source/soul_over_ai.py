from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_artist_detector.domain.youtube import YouTubeAdapterService
    from ai_artist_detector.external.soul_over_ai import SoulOverAiClient


class SoulOverAiService:
    def __init__(
        self,
        youtube_adapter_service: YouTubeAdapterService,
        soul_over_ai_client: SoulOverAiClient,
    ):
        self.youtube_adapter_service = youtube_adapter_service
        self.soul_over_ai_client = soul_over_ai_client

    def get_ai_artists(self) -> set[str]:
        ai_artists = self.soul_over_ai_client.retrieve_ai_youtube_channels()
        ai_ids: set[str] = set()

        for raw_artist_id in ai_artists:
            if raw_artist_id.startswith('@'):
                artist_id = self.youtube_adapter_service.get_artist_id_from_handle(raw_artist_id)
                if artist_id is None:
                    continue
            else:
                artist_id = raw_artist_id

            ai_ids.add(artist_id)

            artist_aliases = self.youtube_adapter_service.get_artist_aliases(artist_id)
            ai_ids.update(artist_aliases)

        return ai_ids
