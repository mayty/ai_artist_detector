from pathlib import Path

from pydantic import AnyHttpUrl, BaseModel as PydanticBaseModel, Field, field_validator
from pydantic_settings import SettingsConfigDict
from yaml import full_load

from ai_artist_detector.constants import CONFIG_OVERRIDE_PATH, CONFIG_PATH, PROJECT_ROOT
from ai_artist_detector.exceptions import (
    InvalidConfigTypeError,
)
from ai_artist_detector.lib.helpers import merge_dicts


class BaseModel(PydanticBaseModel):
    model_config = SettingsConfigDict(extra='forbid')


class SoulOverAiConfig(BaseModel):
    source: AnyHttpUrl
    google_api_key: str
    file_location: Path = Field(default=PROJECT_ROOT / 'data' / 'soul_over_ai.json', validate_default=True)
    youtube_cache_location: Path = Field(
        default=PROJECT_ROOT / 'data' / 'youtube_handles_mapping.json', validate_default=True
    )
    youtube_music_cache_location: Path = Field(
        default=PROJECT_ROOT / 'data' / 'youtube_music_aliases.json', validate_default=True
    )

    @field_validator('file_location', 'youtube_cache_location', 'youtube_music_cache_location', mode='after')
    def validate_file_location(cls, v: Path) -> Path:
        if not v.exists():
            return v
        if not v.is_file():
            msg = f'Path {v} must be a file'
            raise ValueError(msg)
        return v


class SourcesConfig(BaseModel):
    soul_over_ai: SoulOverAiConfig


class AppConfig(BaseModel):
    sources: SourcesConfig


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
