from functools import cached_property

from redis.asyncio import Redis
from ytmusicapi import YTMusic

from ai_artist_detector.config import AppConfig, get_config
from ai_artist_detector.data.redis.verdicts import VerdictsRepository
from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager
from ai_artist_detector.data.sqlite.youtube_handles_mapping import YouTubeHandlesRepository
from ai_artist_detector.data.sqlite.youtube_music_aliases import YouTubeMusicAliasesRepository
from ai_artist_detector.domain.data_source.soul_over_ai import SoulOverAiService
from ai_artist_detector.domain.verdict_controller import VerdictControllerService
from ai_artist_detector.external.soul_over_ai import SoulOverAiClient

__all__ = ('services',)

from ai_artist_detector.external.youtube import YouTubeClient
from ai_artist_detector.external.youtube_music import YouTubeMusicClient


class Core:
    @cached_property
    def config(self) -> AppConfig:
        return get_config()

    @cached_property
    def redis(self) -> Redis:
        return Redis(host=self.config.redis.host, port=self.config.redis.port, db=self.config.redis.db)

    @cached_property
    def sqlite_connection_manager(self) -> SQLiteConnectionManager:
        return SQLiteConnectionManager(self.config.sqlite)

    @cached_property
    def yt_music_client(self) -> YTMusic:
        return YTMusic()


core = Core()


class Repositories:
    @cached_property
    def redis_verdicts_repository(self) -> VerdictsRepository:
        return VerdictsRepository(core.redis)

    @cached_property
    def youtube_handles_repository(self) -> YouTubeHandlesRepository:
        return YouTubeHandlesRepository(connection_manager=core.sqlite_connection_manager)

    @cached_property
    def youtube_music_aliases_repository(self) -> YouTubeMusicAliasesRepository:
        return YouTubeMusicAliasesRepository(connection_manager=core.sqlite_connection_manager)


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


external = External()


class Services:
    @cached_property
    def soul_over_ai_service(self) -> SoulOverAiService:
        return SoulOverAiService(
            youtube_client=external.youtube,
            youtube_music_client=external.youtube_music,
            soul_over_ai_client=external.soul_over_ai_client,
            youtube_handles_repository=repositories.youtube_handles_repository,
            youtube_music_aliases_repository=repositories.youtube_music_aliases_repository,
        )

    @cached_property
    def verdict_controller_service(self) -> VerdictControllerService:
        return VerdictControllerService(
            soul_over_ai_service=self.soul_over_ai_service, verdicts_repository=repositories.redis_verdicts_repository
        )


services = Services()
