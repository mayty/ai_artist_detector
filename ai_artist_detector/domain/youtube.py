# This file has been edited with the assistance of an AI tool.
from contextlib import suppress
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.constants import QueryUpdatePolicies
from ai_artist_detector.exceptions import (
    InvalidYoutubeMusicAccountTypeError,
    RateLimitExceededError,
    RowNotFoundError,
)
from ai_artist_detector.lib.tracking import CacheHit, StageFailed, tracking

if TYPE_CHECKING:
    from ai_artist_detector.config import YouTubeConfig
    from ai_artist_detector.data.sqlite.youtube_handles_mapping import YouTubeHandlesRepository
    from ai_artist_detector.data.sqlite.youtube_music_aliases import YouTubeMusicAliasesRepository
    from ai_artist_detector.data.sqlite.youtube_search_results import YoutubeSearchResultsRepository
    from ai_artist_detector.external.youtube import YouTubeClient
    from ai_artist_detector.external.youtube_music import YouTubeMusicClient


class YouTubeAdapterService:
    def __init__(  # noqa: PLR0913, PLR0917
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

        self._handles_rate_limited = False
        self._search_rate_limited = False

    @tracking.stage_metrics('handle_resolution', default=None)
    def get_artist_id_from_handle(self, artist_handle: str) -> str | None:
        artist_handle = artist_handle.removeprefix('@')

        with suppress(RowNotFoundError):
            artist_id = self.youtube_handles_repository.get_or_raise_youtube_id(artist_handle)
            logger.debug('UsingCachedYoutubeId', artist_handle=artist_handle, youtube_id=artist_id)
            raise CacheHit(artist_id)

        if self._handles_rate_limited:
            logger.error('RateLimitExceeded', artist_handle=artist_handle)
            msg = 'rate_limit'
            raise StageFailed(msg) from None

        try:
            artist_id = self.youtube_client.convert_youtube_handle_to_id(artist_handle)
        except RateLimitExceededError:
            logger.error('RateLimitExceeded', artist_handle=artist_handle)
            self._handles_rate_limited = True
            msg = 'rate_limit'
            raise StageFailed(msg) from None
        except RuntimeError:
            logger.exception('FailedToFetchYoutubeId', artist_handle=artist_handle)
            msg = 'error'
            raise StageFailed(msg) from None

        logger.debug('FetchedYoutubeId', artist_handle=artist_handle, youtube_id=artist_id)
        self.youtube_handles_repository.set_youtube_id(artist_handle, artist_id)
        return artist_id

    @tracking.stage_metrics('alias_resolution', default=set())
    def get_artist_aliases(self, artist_id: str, ignore_aliases_cache: bool) -> set[str]:
        if not ignore_aliases_cache:
            with suppress(RowNotFoundError):
                aliases = self.youtube_music_aliases_repository.get_aliases(artist_id)
                logger.debug('UsingCachedAliases', artist_id=artist_id, aliases=aliases)
                raise CacheHit(aliases)

        try:
            artist_name, aliases, can_cache_empty_result = self.youtube_music_client.get_ytm_id_aliases(artist_id)
        except InvalidYoutubeMusicAccountTypeError as exc:
            logger.error('InvalidYoutubeMusicAccountTypeError', artist_id=artist_id, reason=exc.reason)
            msg = 'invalid_account'
            raise StageFailed(msg) from None
        logger.debug('FetchedAliases', artist_id=artist_id, aliases=aliases)
        if can_cache_empty_result or aliases:
            self.youtube_music_aliases_repository.set_aliases(artist_id, artist_name, aliases)
        return aliases

    @tracking.stage_metrics('search_resolution', default=set())
    def get_artist_id_from_search_query(self, search_query: str) -> set[str]:
        search_query = search_query.lower().strip()
        current_version = 2

        with suppress(RowNotFoundError):
            cached_artist_ids, query_version = self.youtube_search_results_repository.get_or_raise_artist_ids(
                search_query
            )
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
                raise CacheHit(cached_artist_ids)

        if self._search_rate_limited:
            logger.error('RateLimitExceeded', search_query=search_query)
            msg = 'rate_limit'
            raise StageFailed(msg) from None

        try:
            artist_ids = self.youtube_client.find_artist_by_search_query(search_query)
        except RateLimitExceededError:
            logger.error('SearchRateLimitExceeded', search_query=search_query)
            self._search_rate_limited = True
            msg = 'rate_limit'
            raise StageFailed(msg) from None
        except RuntimeError:
            logger.exception('FailedToFetchSearchQuery', search_query=search_query)
            msg = 'error'
            raise StageFailed(msg) from None
        self.youtube_search_results_repository.set_artist_ids(search_query, artist_ids, current_version)
        return artist_ids

    def artist_has_songs_match(self, artist_id: str, artist_tracks: set[str]) -> bool:
        return self.youtube_music_client.artist_has_tracks_overlap(artist_id, artist_tracks)
