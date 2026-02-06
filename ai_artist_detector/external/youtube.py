from typing import TYPE_CHECKING

import requests
from loguru import logger
from starlette.status import HTTP_200_OK

if TYPE_CHECKING:
    from ai_artist_detector.config import YouTubeConfig


class YouTubeClient:
    def __init__(self, config: YouTubeConfig) -> None:
        self.config = config

    def conver_youtube_handle_to_id(self, artist_handle: str) -> str | None:
        logger.debug('ConvertingYoutubeToYoutubeMusic', handle=artist_handle)
        channel_response = requests.get(
            self.config.channels_endpoint,
            params={
                'forHandle': artist_handle,
                'key': self.config.api_key,
            },
            timeout=self.config.timeout_seconds,
        )

        if channel_response.status_code != HTTP_200_OK:
            msg = f'Failed to fetch user data for {artist_handle}: <{channel_response.status_code}>{channel_response.text!r}'
            raise RuntimeError(msg)

        channel_data = channel_response.json()

        if 'items' not in channel_data:
            return None

        for item in channel_data['items']:
            if item['kind'] != 'youtube#channel':
                continue
            return item['id']

        msg = f'Failed to find channel id for {artist_handle}'
        raise RuntimeError(msg)
