import re
from functools import cached_property
from pathlib import Path

from pydantic import AnyHttpUrl, BaseModel as PydanticBaseModel, Field, field_validator
from pydantic_settings import SettingsConfigDict
from yaml import full_load

from ai_artist_detector.constants import CONFIG_OVERRIDE_PATH, CONFIG_PATH, DataSources, QueryUpdatePolicies
from ai_artist_detector.exceptions import (
    InvalidConfigTypeError,
)
from ai_artist_detector.lib.helpers import merge_dicts


class BaseModel(PydanticBaseModel):
    model_config = SettingsConfigDict(extra='forbid')


class RedisConfig(BaseModel):
    host: str = Field(default='localhost', min_length=1, validate_default=True)
    port: int = Field(default=6379, ge=0, validate_default=True)
    db: int = Field(default=0, ge=0, validate_default=True)


class SqliteConfig(BaseModel):
    file_location: Path

    @cached_property
    def resolved_file_location(self) -> str:
        return str(self.file_location.resolve())


class SoulOverAiConfig(BaseModel):
    source: AnyHttpUrl = Field(
        default='https://raw.githubusercontent.com/xoundbyte/soul-over-ai/refs/heads/main/dist/artists.json',
        validate_default=True,
    )
    timeout_seconds: int = Field(default=10, ge=0, validate_default=True)


class IimuzykaTopConfig(BaseModel):
    host: str = Field(default='iimuzyka.top', min_length=1, validate_default=True)
    timeout_seconds: int = Field(default=10, ge=0, validate_default=True)
    cache_directory: Path = Field(default=Path('/app/data/iimuzyka_cache'), validate_default=True)
    prioritize_cache: bool = Field(default=True, validate_default=True)

    @field_validator('cache_directory', mode='after')
    def _ensure_cache_directory_exists(cls, v: Path) -> Path:
        if v.exists() and not v.is_dir():
            msg = 'cache_directory must be a directory'
            raise ValueError(msg)
        v.mkdir(parents=True, exist_ok=True)
        return v


class ExplicitDataSourceConfig(BaseModel):
    artist_ids: set[str] = Field(default_factory=set, validate_default=True)

    @field_validator('artist_ids', mode='after')
    def validate_artist_ids(cls, v: set[str]) -> set[str]:
        for artist_id in v:
            if not re.match(r'^[A-Za-z0-9_-]{24}$', artist_id):
                msg = f'Invalid artist ID format: {artist_id}'
                raise ValueError(msg)
        return v


class SourcesConfig(BaseModel):
    soul_over_ai: SoulOverAiConfig = Field(default_factory=SoulOverAiConfig)
    iimuzyka_top: IimuzykaTopConfig = Field(default_factory=IimuzykaTopConfig)
    explicit: ExplicitDataSourceConfig = Field(default_factory=ExplicitDataSourceConfig)
    enabled_sources: set[DataSources] = Field(default_factory=lambda: set(DataSources), validate_default=True)


class YouTubeConfig(BaseModel):
    api_key: str
    host: str = Field(default='youtube.googleapis.com', min_length=1, validate_default=True)
    channels_route: str = Field(default='/youtube/v3/channels', min_length=1, validate_default=True)
    search_route: str = Field(default='/youtube/v3/search', min_length=1, validate_default=True)
    timeout_seconds: int = Field(default=10, ge=0, validate_default=True)
    enabled: bool = Field(default=True, validate_default=True)
    query_update_policy: QueryUpdatePolicies = Field(default=QueryUpdatePolicies.IGNORE, validate_default=True)

    @cached_property
    def channels_endpoint(self) -> str:
        return f'https://{self.host.strip("/")}/{self.channels_route.strip("/")}'

    @cached_property
    def search_endpoint(self) -> str:
        return f'https://{self.host.strip("/")}/{self.search_route.strip("/")}'


class ExternalsConfig(BaseModel):
    youtube: YouTubeConfig


class AppConfig(BaseModel):
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    external: ExternalsConfig
    redis: RedisConfig = Field(default_factory=RedisConfig)
    sqlite: SqliteConfig


def get_config() -> AppConfig:
    raw_config: object = full_load(CONFIG_PATH.read_text(encoding='utf-8'))
    if not isinstance(raw_config, dict):
        raise InvalidConfigTypeError

    if CONFIG_OVERRIDE_PATH.exists():
        raw_config_override: object = full_load(CONFIG_OVERRIDE_PATH.read_text(encoding='utf-8'))
        if not isinstance(raw_config_override, dict):
            raise InvalidConfigTypeError
        merge_dicts(raw_config, raw_config_override)

    return AppConfig(**raw_config)
