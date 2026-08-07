# This file has been edited with the assistance of an AI tool.
from contextlib import suppress
from copy import copy
from itertools import chain
from typing import TYPE_CHECKING

import requests
from loguru import logger

from ai_artist_detector.exceptions import MatchingNotImplementedError, RowNotFoundError
from ai_artist_detector.lib.helpers import get_first_query_param
from ai_artist_detector.lib.tracking import CacheHit, StageFailed, tracking

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.iimuzyka_ids_mapping import IimuzykaIdsMappingRepository
    from ai_artist_detector.data.sqlite.iimuzyka_youtube_music_artist_matches import (
        IimuzykaYouTubeMusicArtistMatchesRepository,
    )
    from ai_artist_detector.domain.youtube import YouTubeAdapterService
    from ai_artist_detector.external.iimuzyka_top import IimuzykaTopClient


class IimuzykaTopService:
    def __init__(
        self,
        youtube_adapter_service: YouTubeAdapterService,
        iimyzyka_top_client: IimuzykaTopClient,
        iimuzyka_ids_mapping_repository: IimuzykaIdsMappingRepository,
        iimuzyka_youtube_music_artist_matches_repository: IimuzykaYouTubeMusicArtistMatchesRepository,
    ) -> None:
        self.youtube_adapter_service = youtube_adapter_service
        self.iimyzyka_top_client = iimyzyka_top_client
        self.iimuzyka_ids_mapping_repository = iimuzyka_ids_mapping_repository
        self.iimuzyka_youtube_music_artist_matches_repository = iimuzyka_youtube_music_artist_matches_repository

        self.artists_count = 0
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

    def get_ai_artists(self, ignore_aliases_cache: bool) -> set[str]:
        logger.info('RetrievingInitialPage')
        page = self.iimyzyka_top_client.get_page()
        logger.info('RetrievedPage', artists_count=len(page.artists))
        artists = page.artists

        while page.next_page_id is not None:
            logger.info('RetrievingNextPage', page_id=page.next_page_id)
            page = self.iimyzyka_top_client.get_page(page.next_page_id)
            logger.info('RetrievedPage', artists_count=len(page.artists))
            artists.update(page.artists)

        ytm_ids: set[str] = set()

        self.artists_count = len(artists)
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

        for i, (artist_id, artist_tracks) in enumerate(artists.items(), 1):
            with logger.contextualize(artist_id=artist_id, progress=f'{i}/{len(artists)}'):
                artist_ytm_ids = self._get_artist_youtube_music_ids(
                    artist_id, artist_tracks, ignore_aliases_cache=ignore_aliases_cache
                )
                if not artist_ytm_ids:
                    self.not_matched_count += 1
                ytm_ids.update(artist_ytm_ids)

        logger.info(
            'RetrievalStats',
            artists_count=len(artists),
            ytm_ids_count=len(ytm_ids),
            unresolved_handles_count=self.unresolved_handles_count,
            not_matched_count=self.not_matched_count,
        )

        return ytm_ids

    def _get_artist_youtube_music_ids(
        self, artist_id: int, artist_tracks: set[str], ignore_aliases_cache: bool
    ) -> set[str]:
        youtube_paths = self._fetch_youtube_paths(artist_id)
        if youtube_paths is None:
            return set()
        if not youtube_paths:
            logger.debug('NoYoutubeHandlesForArtist')
            return set()

        ytm_ids = set(
            chain.from_iterable(
                self._get_youtube_music_ids(artist_id, path, query_params, artist_tracks)
                for path, query_params in youtube_paths
            )
        )

        if not ytm_ids:
            logger.warning('NoYoutubeIdForArtist', youtube_paths=youtube_paths)
            return set()

        for artist_ytm_id in copy(ytm_ids):
            ytm_ids |= self.youtube_adapter_service.get_artist_aliases(
                artist_ytm_id, ignore_aliases_cache=ignore_aliases_cache
            )

        return ytm_ids

    @tracking.stage_metrics('youtube_path_fetch', default=None)
    def _fetch_youtube_paths(self, artist_id: int) -> list[tuple[str, list[tuple[str, str]]]] | None:
        with suppress(RowNotFoundError):
            youtube_paths = self.iimuzyka_ids_mapping_repository.get_or_raise_youtube_paths(artist_id)
            logger.debug('UsingCachedYoutubePaths', youtube_paths=youtube_paths)
            raise CacheHit(youtube_paths)

        try:
            youtube_handles_response = self.iimyzyka_top_client.get_artist_youtube(artist_id)
        except (requests.exceptions.RequestException, ConnectionResetError) as exc:
            logger.error('FailedToFetchArtistYoutubePaths', artist_id=artist_id, error=str(exc))
            msg = 'network'
            raise StageFailed(msg) from None

        self.iimuzyka_ids_mapping_repository.set_youtube_paths(
            artist_id,
            youtube_handles_response.name,  # pyrefly: ignore[unbound-name]
            youtube_handles_response.paths,
        )
        return youtube_handles_response.paths

    def _get_youtube_music_ids(
        self,
        iimuzyka_id: int,
        path: str,
        query_params: list[tuple[str, str]],
        artist_tracks: set[str],
    ) -> set[str]:
        if path.startswith('channel/'):
            return {path.removeprefix('channel/').split('/')[0]}

        if path == 'results':
            search_query = get_first_query_param(query_params, 'search_query')
            if search_query:
                artist_ytm_ids = self.youtube_adapter_service.get_artist_id_from_search_query(search_query)

                logger.debug('FilteringArtists', artist_ids=artist_ytm_ids, search_query=search_query)
                return set(
                    filter(
                        lambda artist_id: self._artist_has_tracks_overlap(iimuzyka_id, artist_id, artist_tracks),
                        artist_ytm_ids,
                    )
                )

            logger.warning('NoSearchQueryInYoutubePath', youtube_path=path, query_params=query_params)
            return set()

        for prefix in ('@', 'user/', 'c/'):
            if not path.startswith(prefix):
                continue
            handle = path.removeprefix(prefix).split('/')[0]
            artist_ytm_id = self.youtube_adapter_service.get_artist_id_from_handle(handle)
            if artist_ytm_id is not None:
                return {artist_ytm_id}
            self.unresolved_handles_count += 1

        return set()

    @tracking.stage_metrics('song_match_verification', default=False)
    def _artist_has_tracks_overlap(self, iimuzyka_artist_id: int, artist_id: str, artist_tracks: set[str]) -> bool:
        with suppress(RowNotFoundError):
            is_match = self.iimuzyka_youtube_music_artist_matches_repository.is_match(iimuzyka_artist_id, artist_id)
            logger.debug(
                'UsingCachedMatchStatus', iimuzyka_artist_id=iimuzyka_artist_id, youtube_id=artist_id, is_match=is_match
            )
            raise CacheHit(is_match)

        try:
            is_match = self.youtube_adapter_service.artist_has_songs_match(artist_id, artist_tracks)
        except MatchingNotImplementedError:
            logger.warning('CouldNotCheckForMatch', iimuzyka_artist_id=iimuzyka_artist_id, youtube_id=artist_id)
            msg = 'not_implemented'
            raise StageFailed(msg) from None
        self.iimuzyka_youtube_music_artist_matches_repository.set_match_status(iimuzyka_artist_id, artist_id, is_match)
        return is_match
