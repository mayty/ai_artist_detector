from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.constants import QueryUpdatePolicies
from ai_artist_detector.exceptions import (
    InvalidYoutubeMusicAccountTypeError,
    RateLimitExceededError,
    RowNotFoundError,
)

if TYPE_CHECKING:
    from ai_artist_detector.config import YouTubeConfig
    from ai_artist_detector.data.sqlite.youtube_handles_mapping import YouTubeHandlesRepository
    from ai_artist_detector.data.sqlite.youtube_music_aliases import YouTubeMusicAliasesRepository
    from ai_artist_detector.data.sqlite.youtube_search_results import YoutubeSearchResultsRepository
    from ai_artist_detector.external.youtube import YouTubeClient
    from ai_artist_detector.external.youtube_music import YouTubeMusicClient


class YouTubeAdapterService:
    def __init__(  # noqa: PLR0913
        self,
        config: YouTubeConfig,
        youtube_client: YouTubeClient,
        youtube_music_client: YouTubeMusicClient,
        youtube_handles_repository: YouTubeHandlesRepository,
        youtube_music_aliases_repository: YouTubeMusicAliasesRepository,
        youtube_search_results_repository: YoutubeSearchResultsRepository,
    ) -> None:
        self.config = config
        self.youtube_client = youtube_client
        self.youtube_music_client = youtube_music_client
        self.youtube_handles_repository = youtube_handles_repository
        self.youtube_music_aliases_repository = youtube_music_aliases_repository
        self.youtube_search_results_repository = youtube_search_results_repository
        self._failed_rate_limit_count = 0
        self._total_failed_rate_limit_count = 0
        self.handles_cache_updated_count = 0
        self.aliases_cache_updated_count = 0
        self.search_cache_updated_count = 0

    def reset_stats(self) -> None:
        self._failed_rate_limit_count = 0
        self.handles_cache_updated_count = 0
        self.aliases_cache_updated_count = 0
        self.search_cache_updated_count = 0

    @property
    def failed_rate_limit_count(self) -> int:
        return self._failed_rate_limit_count

    @failed_rate_limit_count.setter
    def failed_rate_limit_count(self, value: int) -> None:
        self._total_failed_rate_limit_count += value - self._failed_rate_limit_count
        self._failed_rate_limit_count = value

    def get_artist_id_from_handle(self, artist_handle: str) -> str | None:
        artist_handle = artist_handle.removeprefix('@')

        try:
            artist_id = self.youtube_handles_repository.get_or_raise_youtube_id(artist_handle)
        except RowNotFoundError:
            pass
        else:
            logger.debug('UsingCachedYoutubeId', artist_handle=artist_handle, youtube_id=artist_id)
            return artist_id

        if self._total_failed_rate_limit_count:
            self.failed_rate_limit_count += 1
            logger.error('RateLimitExceeded', artist_handle=artist_handle)
            return None

        try:
            artist_id = self.youtube_client.convert_youtube_handle_to_id(artist_handle)
        except RateLimitExceededError:
            logger.error('RateLimitExceeded', artist_handle=artist_handle)
            self.failed_rate_limit_count += 1
            return None
        except RuntimeError:
            logger.exception('FailedToFetchYoutubeId', artist_handle=artist_handle)
            return None

        logger.debug('FetchedYoutubeId', artist_handle=artist_handle, youtube_id=artist_id)
        self.youtube_handles_repository.set_youtube_id(artist_handle, artist_id)
        self.handles_cache_updated_count += 1
        return artist_id

    def get_artist_aliases(self, artist_id: str, ignore_aliases_cache: bool) -> set[str]:
        if not ignore_aliases_cache:
            try:
                aliases = self.youtube_music_aliases_repository.get_aliases(artist_id)
            except RowNotFoundError:
                pass
            else:
                logger.debug('UsingCachedAliases', artist_id=artist_id, aliases=aliases)
                return aliases

        try:
            artist_name, aliases, can_cache_empty_result = self.youtube_music_client.get_ytm_id_aliases(artist_id)
        except InvalidYoutubeMusicAccountTypeError as exc:
            logger.error('InvalidYoutubeMusicAccountTypeError', artist_id=artist_id, reason=exc.reason)
            return set()
        logger.debug('FetchedAliases', artist_id=artist_id, aliases=aliases)
        if can_cache_empty_result or aliases:
            self.youtube_music_aliases_repository.set_aliases(artist_id, artist_name, aliases)
            self.aliases_cache_updated_count += 1
        return aliases

    def get_artist_id_from_search_query(self, search_query: str) -> set[str]:
        search_query = search_query.lower().strip()
        current_version = 2

        try:
            cached_artist_ids, query_version = self.youtube_search_results_repository.get_or_raise_artist_ids(
                search_query
            )
        except RowNotFoundError:
            cached_artist_ids = None
        else:
            if (
                query_version == current_version
                or (self.config.query_update_policy == QueryUpdatePolicies.IGNORE)
                or (self.config.query_update_policy == QueryUpdatePolicies.UPDATE_EMPTY and cached_artist_ids)
            ):
                logger.debug(
                    'UsingCachedSearchQuery',
                    search_query=search_query,
                    artist_ids=cached_artist_ids,
                    query_version=query_version,
                    current_version=current_version,
                )
                return cached_artist_ids

        if self._total_failed_rate_limit_count:
            logger.error('RateLimitExceeded', search_query=search_query)
            self.failed_rate_limit_count += 1
            return cached_artist_ids or set()

        try:
            artist_ids = self.youtube_client.find_artist_by_search_query(search_query)
        except RateLimitExceededError:
            logger.error('SearchRateLimitExceeded', search_query=search_query)
            self.failed_rate_limit_count += 1
            return cached_artist_ids or set()
        self.youtube_search_results_repository.set_artist_ids(search_query, artist_ids, current_version)
        self.search_cache_updated_count += 1
        return artist_ids

    def artist_has_songs_match(self, artist_id: str, artist_tracks: set[str]) -> bool:
        return self.youtube_music_client.artist_has_tracks_overlap(artist_id, artist_tracks)
