from typing import TYPE_CHECKING

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

        for artist_id in self.artist_ids:
            artist_ids.add(artist_id)

            artist_ids |= self.youtube_adapter_service.get_artist_aliases(
                artist_id, ignore_aliases_cache=ignore_aliases_cache
            )

        return artist_ids
