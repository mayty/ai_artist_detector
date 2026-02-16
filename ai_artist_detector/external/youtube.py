from typing import TYPE_CHECKING

import requests
from loguru import logger
from starlette.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from ai_artist_detector.exceptions import RateLimitExceededError
from ai_artist_detector.lib.web_helpers import names_match

if TYPE_CHECKING:
    from ai_artist_detector.config import YouTubeConfig


class YouTubeClient:
    def __init__(self, config: YouTubeConfig) -> None:
        self.config = config
        self._rate_limit_reached = False

    def _raise_if_forbidden(self) -> None:
        if not self.config.enabled:
            msg = 'YouTubeClientDisabled'
            raise RateLimitExceededError(msg)
        if self._rate_limit_reached:
            msg = 'RateLimitReached'
            raise RateLimitExceededError(msg)

    def _raise_if_rate_limit_exceeded(self, response: requests.Response) -> None:
        if response.status_code == HTTP_403_FORBIDDEN:
            self._rate_limit_reached = True
            raise RateLimitExceededError(response.text)

    def convert_youtube_handle_to_id(self, artist_handle: str) -> str | None:
        self._raise_if_forbidden()

        logger.info('FetchingYouTubeId', handle=artist_handle)
        channel_response = requests.get(
            self.config.channels_endpoint,
            params={
                'forHandle': f'@{artist_handle.removeprefix("@")}',
                'key': self.config.api_key,
            },
            timeout=self.config.timeout_seconds,
        )

        self._raise_if_rate_limit_exceeded(channel_response)

        if channel_response.status_code != HTTP_200_OK:
            msg = f'Failed to fetch user data for {artist_handle}: <{channel_response.status_code}>{channel_response.text}'
            raise RuntimeError(msg)

        channel_data = channel_response.json()

        if 'items' not in channel_data:
            return None

        for item in channel_data['items']:
            if item['kind'] != 'youtube#channel':
                continue
            return item['id']

        msg = f'Failed to find channel id for {artist_handle}: {channel_response.text}'
        raise RuntimeError(msg)

    def find_artist_by_search_query(self, search_query: str) -> set[str]:
        self._raise_if_forbidden()

        search_query = search_query.lower().strip().removesuffix(' topic').strip().removesuffix(' -').strip()
        logger.info('SearchingYoutube', query=search_query)

        params = {
            'part': 'snippet',
            'type': 'channel',
            'q': search_query,
            'key': self.config.api_key,
        }
        search_response = requests.get(
            self.config.search_endpoint,
            params=params,
            timeout=self.config.timeout_seconds,
        )

        self._raise_if_rate_limit_exceeded(search_response)

        if search_response.status_code != HTTP_200_OK:
            msg = (
                f'Failed to fetch user data for "{search_query}": <{search_response.status_code}>{search_response.text}'
            )
            raise RuntimeError(msg)

        search_data = search_response.json()

        if 'items' not in search_data:
            return set()

        artist_ids: set[str] = set()

        for item in search_data['items']:
            if item['kind'] != 'youtube#searchResult':
                continue

            if item['id']['kind'] != 'youtube#channel':
                continue

            artist_id = item['id']['channelId']

            snippet = item['snippet']
            title = snippet['title'].lower().strip()
            channel_title = snippet['channelTitle'].lower().strip()

            if names_match(search_query, title):
                logger.debug('FoundArtist', query=search_query, artist_id=artist_id, artist_name=title)
                artist_ids.add(artist_id)
            elif names_match(search_query, channel_title):
                logger.debug('FoundArtist', query=search_query, artist_id=artist_id, artist_name=channel_title)
                artist_ids.add(artist_id)

        return artist_ids
