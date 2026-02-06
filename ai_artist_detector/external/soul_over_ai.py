from typing import TYPE_CHECKING

import requests
from loguru import logger

if TYPE_CHECKING:
    from ai_artist_detector.config import SoulOverAiConfig


class SoulOverAiClient:
    def __init__(self, config: SoulOverAiConfig):
        self.config = config
        self._raw_youtube_cache: dict[str, str] | None = None
        self._raw_ytm_cache: dict[str, list[str]] | None = None

    def retrieve_ai_youtube_channels(self) -> dict[str, str]:
        response = requests.get(str(self.config.source), timeout=10)
        response.raise_for_status()

        result: dict[str, str] = {}

        for artist_data in response.json():
            name = artist_data['name']
            youtube_id = artist_data['youtube']
            if youtube_id is None:
                logger.debug('NoYoutubeId', artist_name=name)
                continue

            assert isinstance(youtube_id, str), f'Expected str, got {type(youtube_id).__name__}'

            assert isinstance(name, str), f'Expected str, got {type(name).__name__}'

            if youtube_id.startswith('@'):
                logger.debug('YoutubeHandle', artist_name=name, youtube_handle=youtube_id[1:])
                result[name] = youtube_id
                continue

            if youtube_id.startswith('UC'):
                logger.debug('YoutubeId', artist_name=name, youtube_id=youtube_id)
                result[name] = youtube_id
                continue

            logger.debug('UnknownYoutubeIdFormat', artist_name=name, youtube_id=youtube_id)

        return result
