from copy import copy
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.iimuzyka_ids_mapping import IimuzykaIdsMappingRepository
    from ai_artist_detector.domain.youtube import YouTubeAdapterService
    from ai_artist_detector.external.iimuzyka_top import IimuzykaTopClient


class IimuzykaTopService:
    def __init__(
        self,
        youtube_adapter_service: YouTubeAdapterService,
        iimyzyka_top_client: IimuzykaTopClient,
        iimuzyka_ids_mapping_repository: IimuzykaIdsMappingRepository,
    ) -> None:
        self.youtube_adapter_service = youtube_adapter_service
        self.iimyzyka_top_client = iimyzyka_top_client
        self.iimuzyka_ids_mapping_repository = iimuzyka_ids_mapping_repository

    def get_ai_artists(self) -> set[str]:
        logger.info('RetrievingInitialPage')
        page = self.iimyzyka_top_client.get_page()
        logger.info('RetrievedPage', artists_count=len(page.artist_ids))
        artist_ids = page.artist_ids

        while page.next_page_id is not None:
            logger.info('RetrievingNextPage', page_id=page.next_page_id)
            page = self.iimyzyka_top_client.get_page(page.next_page_id)
            logger.info('RetrievedPage', artists_count=len(page.artist_ids))
            artist_ids |= page.artist_ids

        ytm_ids: set[str] = set()

        for artist_id in artist_ids:
            with logger.contextualize(artist_id=artist_id):
                ytm_ids.update(self._get_artist_youtube_music_ids(artist_id))

        logger.info('FailedRequestsCount', rate_limit=self.youtube_adapter_service.failed_rate_limit_count)

        return ytm_ids

    def _get_artist_youtube_music_ids(self, artist_id: int) -> set[str]:
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
            ytm_ids |= self._get_youtube_music_ids(path, query_params)

        return ytm_ids

    def _get_youtube_music_ids(self, path: str, query_params: list[tuple[str, str]]) -> set[str]:
        artist_ytm_ids: set[str] = set()

        if path.startswith('channel/'):
            artist_ytm_ids = {path.removeprefix('channel/').split('/')[0]}
        elif path == 'results':
            search_query = self._get_first_query_param(query_params, 'search_query')
            if search_query:
                artist_ytm_ids = self.youtube_adapter_service.get_artist_id_from_search_query(search_query)
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
            ytm_ids |= self.youtube_adapter_service.get_artist_aliases(artist_ytm_id)

        return ytm_ids

    def _get_first_query_param(self, params: list[tuple[str, str]], name: str) -> str | None:
        for param_name, param_value in params:
            if param_name == name:
                return param_value
        return None
