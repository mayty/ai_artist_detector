from functools import cached_property

from ai_artist_detector.config import AppConfig, get_config
from ai_artist_detector.external.soul_over_ai import SoulOverAiProxy

__all__ = (
    'core',
    'external',
)


class Core:
    @cached_property
    def config(self) -> AppConfig:
        return get_config()


core = Core()


class External:
    @cached_property
    def soul_over_ai(self) -> SoulOverAiProxy:
        return SoulOverAiProxy(config=core.config.sources.soul_over_ai)


external = External()
