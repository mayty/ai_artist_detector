from copy import copy
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.exceptions import NoSongsFoundError, RowNotFoundError
from ai_artist_detector.lib.helpers import get_first_query_param

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

        for artist_id, artist_tracks in artists.items():
            with logger.contextualize(artist_id=artist_id):
                ytm_ids.update(
                    self._get_artist_youtube_music_ids(
                        artist_id, artist_tracks, ignore_aliases_cache=ignore_aliases_cache
                    )
                )

        logger.info('FailedRequestsCount', rate_limit=self.youtube_adapter_service.failed_rate_limit_count)

        return ytm_ids

    def _get_artist_youtube_music_ids(
        self, artist_id: int, artist_tracks: set[str], ignore_aliases_cache: bool
    ) -> set[str]:
        try:
            youtube_paths = self.iimuzyka_ids_mapping_repository.get_or_raise_youtube_paths(artist_id)
            logger.debug('UsingCachedYoutubePaths', youtube_paths=youtube_paths)
        except RowNotFoundError:
            youtube_handles_response = self.iimyzyka_top_client.get_artist_youtube(artist_id)
            youtube_paths = youtube_handles_response.paths
            self.iimuzyka_ids_mapping_repository.set_youtube_paths(
                artist_id, youtube_handles_response.name, youtube_handles_response.paths
            )

        if not youtube_paths:
            logger.debug('NoYoutubeHandlesForArtist')
            return set()

        ytm_ids: set[str] = set()

        for path, query_params in youtube_paths:
            ytm_ids |= self._get_youtube_music_ids(
                artist_id, path, query_params, artist_tracks, ignore_aliases_cache=ignore_aliases_cache
            )

        return ytm_ids

    def _artist_has_tracks_overlap(self, iimuzyka_artist_id: int, artist_id: str, artist_tracks: set[str]) -> bool:
        try:
            is_match = self.iimuzyka_youtube_music_artist_matches_repository.is_match(iimuzyka_artist_id, artist_id)
        except RowNotFoundError:
            pass
        else:
            logger.debug(
                'UsingCachedMatchStatus', iimuzyka_artist_id=iimuzyka_artist_id, youtube_id=artist_id, is_match=is_match
            )
            return is_match

        try:
            is_match = self.youtube_adapter_service.artist_has_songs_match(artist_id, artist_tracks)
        except NoSongsFoundError:
            logger.warning('NoSongsPlaylistFound', iimuzyka_artist_id=iimuzyka_artist_id, youtube_id=artist_id)
            is_match = False
        else:
            self.iimuzyka_youtube_music_artist_matches_repository.set_match_status(
                iimuzyka_artist_id, artist_id, is_match
            )
        return is_match

    def _get_youtube_music_ids(
        self,
        iimuzyka_id: int,
        path: str,
        query_params: list[tuple[str, str]],
        artist_tracks: set[str],
        ignore_aliases_cache: bool,
    ) -> set[str]:
        artist_ytm_ids: set[str] = set()

        if path.startswith('channel/'):
            artist_ytm_ids = {path.removeprefix('channel/').split('/')[0]}
        elif path == 'results':
            search_query = get_first_query_param(query_params, 'search_query')
            if search_query:
                artist_ytm_ids = self.youtube_adapter_service.get_artist_id_from_search_query(search_query)

                logger.debug('FilteringArtists', artist_ids=artist_ytm_ids, search_query=search_query)
                artist_ytm_ids = set(
                    filter(
                        lambda artist_id: self._artist_has_tracks_overlap(iimuzyka_id, artist_id, artist_tracks),
                        artist_ytm_ids,
                    )
                )

            else:
                logger.warning('NoSearchQueryInYoutubePath', youtube_path=path, query_params=query_params)
        else:
            for prefix in ('@', 'user/', 'c/'):
                if not path.startswith(prefix):
                    continue
                handle = path.removeprefix(prefix).split('/')[0]
                artist_ytm_id = self.youtube_adapter_service.get_artist_id_from_handle(handle)
                if artist_ytm_id is not None:
                    artist_ytm_ids = {artist_ytm_id}

        if not artist_ytm_ids:
            logger.warning('NoYoutubeIdForArtist', youtube_path=path, query_params=query_params)
            return set()

        ytm_ids = copy(artist_ytm_ids)

        for artist_ytm_id in artist_ytm_ids:
            ytm_ids |= self.youtube_adapter_service.get_artist_aliases(
                artist_ytm_id, ignore_aliases_cache=ignore_aliases_cache
            )

        return ytm_ids
