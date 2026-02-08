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
            ytm_ids.update(self._get_artist_youtube_music_ids(artist_id))

        return ytm_ids

    def _get_artist_youtube_music_ids(self, artist_id: int) -> set[str]:
        try:
            youtube_handles = self.iimuzyka_ids_mapping_repository.get_or_raise_youtube_handles(artist_id)
            logger.debug('UsingCachedYoutubeHandles', artist_id=artist_id, youtube_handles=youtube_handles)
        except RowNotFoundError:
            youtube_handles_response = self.iimyzyka_top_client.get_artist_youtube(artist_id)
            youtube_handles = youtube_handles_response.handles
            self.iimuzyka_ids_mapping_repository.set_youtube_handles(
                artist_id, youtube_handles_response.name, youtube_handles_response.handles
            )

        if not youtube_handles:
            logger.debug('NoYoutubeHandlesForArtist', artist_id=artist_id)
            return set()

        ytm_ids: set[str] = set()

        for handle in youtube_handles:
            if handle.startswith('@'):
                artist_ytm_id = self.youtube_adapter_service.get_artist_id_from_handle(handle)
                if artist_ytm_id is None:
                    continue
            else:
                artist_ytm_id = handle

            ytm_ids.add(artist_ytm_id)

            ytm_ids.update(self.youtube_adapter_service.get_artist_aliases(artist_ytm_id, handle))

        return ytm_ids
