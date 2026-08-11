from functools import cached_property

from cloudscraper import CloudScraper
from prometheus_client import CollectorRegistry
from ytmusicapi import YTMusic

from ai_artist_detector.config import AppConfig, get_config
from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager
from ai_artist_detector.data.sqlite.iimuzyka_ids_mapping import IimuzykaIdsMappingRepository
from ai_artist_detector.data.sqlite.iimuzyka_overrides import IimuzykaOverridesRepository
from ai_artist_detector.data.sqlite.iimuzyka_youtube_music_artist_matches import (
    IimuzykaYouTubeMusicArtistMatchesRepository,
)
from ai_artist_detector.data.sqlite.ingestion_metrics import MetricsRepository
from ai_artist_detector.data.sqlite.verdicts import VerdictsRepository
from ai_artist_detector.data.sqlite.youtube_handles_mapping import YouTubeHandlesRepository
from ai_artist_detector.data.sqlite.youtube_music_aliases import YouTubeMusicAliasesRepository
from ai_artist_detector.data.sqlite.youtube_search_results import YoutubeSearchResultsRepository
from ai_artist_detector.domain.data_source.explicit import ExplicitService
from ai_artist_detector.domain.data_source.iimuzyka_top import IimuzykaTopService
from ai_artist_detector.domain.data_source.soul_over_ai import SoulOverAiService
from ai_artist_detector.domain.metrics_service import MetricsService
from ai_artist_detector.domain.verdict_controller import VerdictControllerService
from ai_artist_detector.domain.youtube import YouTubeAdapterService
from ai_artist_detector.external.iimuzyka_top import IimuzykaTopClient
from ai_artist_detector.external.soul_over_ai import SoulOverAiClient

__all__ = ('services',)

from ai_artist_detector.external.youtube import YouTubeClient
from ai_artist_detector.external.youtube_music import YouTubeMusicClient


class Core:
    @cached_property
    def config(self) -> AppConfig:
        return get_config()

    @cached_property
    def sqlite_connection_manager(self) -> SQLiteConnectionManager:
        return SQLiteConnectionManager(self.config.sqlite)

    @cached_property
    def yt_music_client(self) -> YTMusic:
        return YTMusic()

    @cached_property
    def scraper(self) -> CloudScraper:
        return CloudScraper()

    @cached_property
    def metrics_registry(self) -> CollectorRegistry:
        return CollectorRegistry()


core = Core()


class Repositories:
    @cached_property
    def verdicts_repository(self) -> VerdictsRepository:
        return VerdictsRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def metrics_repository(self) -> MetricsRepository:
        return MetricsRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def youtube_handles_repository(self) -> YouTubeHandlesRepository:
        return YouTubeHandlesRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def youtube_music_aliases_repository(self) -> YouTubeMusicAliasesRepository:
        return YouTubeMusicAliasesRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def iimuzyka_ids_mapping_repository(self) -> IimuzykaIdsMappingRepository:
        return IimuzykaIdsMappingRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def youtube_search_results_repository(self) -> YoutubeSearchResultsRepository:
        return YoutubeSearchResultsRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def iimuzyke_overrides_repository(self) -> IimuzykaOverridesRepository:
        return IimuzykaOverridesRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def iimuzyka_youtube_music_artist_matches_repository(self) -> IimuzykaYouTubeMusicArtistMatchesRepository:
        return IimuzykaYouTubeMusicArtistMatchesRepository(connection_manager=core.sqlite_connection_manager)


repositories = Repositories()


class External:
    @cached_property
    def soul_over_ai_client(self) -> SoulOverAiClient:
        return SoulOverAiClient(config=core.config.sources.soul_over_ai)

    @cached_property
    def youtube(self) -> YouTubeClient:
        return YouTubeClient(config=core.config.external.youtube)

    @cached_property
    def youtube_music(self) -> YouTubeMusicClient:
        return YouTubeMusicClient(client=core.yt_music_client)

    @cached_property
    def iimyzyka_top_client(self) -> IimuzykaTopClient:
        return IimuzykaTopClient(config=core.config.sources.iimuzyka_top, scraper=core.scraper)


external = External()


class Services:
    @cached_property
    def metrics_service(self) -> MetricsService:
        return MetricsService(
            registry=core.metrics_registry,
            metrics_repository=repositories.metrics_repository,
        )

    @cached_property
    def youtube_adapter_service(self) -> YouTubeAdapterService:
        return YouTubeAdapterService(
            config=core.config.external.youtube,
            youtube_client=external.youtube,
            youtube_music_client=external.youtube_music,
            youtube_handles_repository=repositories.youtube_handles_repository,
            youtube_music_aliases_repository=repositories.youtube_music_aliases_repository,
            youtube_search_results_repository=repositories.youtube_search_results_repository,
        )

    @cached_property
    def soul_over_ai_service(self) -> SoulOverAiService:
        return SoulOverAiService(
            youtube_adapter_service=self.youtube_adapter_service,
            soul_over_ai_client=external.soul_over_ai_client,
        )

    @cached_property
    def iimyzyka_top_service(self) -> IimuzykaTopService:
        return IimuzykaTopService(
            youtube_adapter_service=self.youtube_adapter_service,
            iimyzyka_top_client=external.iimyzyka_top_client,
            iimuzyka_ids_mapping_repository=repositories.iimuzyka_ids_mapping_repository,
            iimuzyka_youtube_music_artist_matches_repository=repositories.iimuzyka_youtube_music_artist_matches_repository,
        )

    @cached_property
    def explicit_service(self) -> ExplicitService:
        return ExplicitService(
            artist_ids=core.config.sources.explicit.artist_ids,
        )

    @cached_property
    def verdict_controller_service(self) -> VerdictControllerService:
        return VerdictControllerService(
            enabled_sources=core.config.sources.enabled_sources,
            soul_over_ai_service=self.soul_over_ai_service,
            iimuzyka_top_service=self.iimyzyka_top_service,
            explicit_service=self.explicit_service,
            youtube_adapter_service=self.youtube_adapter_service,
            verdicts_repository=repositories.verdicts_repository,
            metrics_service=self.metrics_service,
        )


services = Services()
