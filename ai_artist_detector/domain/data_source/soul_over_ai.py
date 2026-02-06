from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.youtube_handles_mapping import YouTubeHandlesRepository
    from ai_artist_detector.data.sqlite.youtube_music_aliases import YouTubeMusicAliasesRepository
    from ai_artist_detector.external.soul_over_ai import SoulOverAiClient
    from ai_artist_detector.external.youtube import YouTubeClient
    from ai_artist_detector.external.youtube_music import YouTubeMusicClient


class SoulOverAiService:
    def __init__(
        self,
        youtube_client: YouTubeClient,
        youtube_music_client: YouTubeMusicClient,
        soul_over_ai_client: SoulOverAiClient,
        youtube_handles_repository: YouTubeHandlesRepository,
        youtube_music_aliases_repository: YouTubeMusicAliasesRepository,
    ):
        self.youtube_client = youtube_client
        self.youtube_music_client = youtube_music_client
        self.soul_over_ai_client = soul_over_ai_client
        self.youtube_handles_repository = youtube_handles_repository
        self.youtube_music_aliases_repository = youtube_music_aliases_repository

    def _get_artist_id_from_handle(self, artist_handle: str) -> str | None:
        artist_handle = artist_handle.removeprefix('@')

        try:
            artist_id = self.youtube_handles_repository.get_or_raise_youtube_id(artist_handle)
        except RowNotFoundError:
            pass
        else:
            logger.debug('UsingCachedYoutubeId', artist_handle=artist_handle, youtube_id=artist_id)
            return artist_id

        try:
            artist_id = self.youtube_client.conver_youtube_handle_to_id(artist_handle)
        except RuntimeError:
            logger.exception('FailedToFetchYoutubeId', artist_handle=artist_handle)
            return None

        logger.debug('FetchedYoutubeId', artist_handle=artist_handle, youtube_id=artist_id)
        self.youtube_handles_repository.set_youtube_id(artist_handle, artist_id)
        return artist_id

    def _get_artist_aliases(self, artist_id: str, artist_name: str) -> set[str]:
        try:
            aliases = self.youtube_music_aliases_repository.get_aliases(artist_id)
        except RowNotFoundError:
            pass
        else:
            logger.debug('UsingCachedAliases', artist_id=artist_id, aliases=aliases)
            return aliases

        aliases = set(self.youtube_music_client.get_ytm_id_aliases(artist_id))
        logger.debug('FetchedAliases', artist_id=artist_id, aliases=aliases)
        self.youtube_music_aliases_repository.set_aliases(artist_id, artist_name, aliases)
        return aliases

    def get_ai_artists(self) -> set[str]:
        ai_artists = self.soul_over_ai_client.retrieve_ai_youtube_channels()
        ai_ids: set[str] = set()

        for artist_name, raw_artist_id in ai_artists.items():
            if raw_artist_id.startswith('@'):
                artist_id = self._get_artist_id_from_handle(raw_artist_id)
                if artist_id is None:
                    continue
            else:
                artist_id = raw_artist_id

            ai_ids.add(artist_id)

            artist_aliases = self._get_artist_aliases(artist_id, artist_name)
            ai_ids.update(artist_aliases)

        return ai_ids
