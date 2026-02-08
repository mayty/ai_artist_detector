from typing import TYPE_CHECKING

import requests
from loguru import logger
from starlette.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from ai_artist_detector.exceptions import RateLimitExceededError

if TYPE_CHECKING:
    from ai_artist_detector.config import YouTubeConfig


class YouTubeClient:
    def __init__(self, config: YouTubeConfig) -> None:
        self.config = config
        self.hit_rate_limit = False

    def conver_youtube_handle_to_id(self, artist_handle: str) -> str | None:
        if self.hit_rate_limit:
            msg = 'RateLimiterHit'
            raise RateLimitExceededError(msg)
        logger.debug('ConvertingYoutubeToYoutubeMusic', handle=artist_handle)
        params = {
            'forHandle': f'@{artist_handle.removeprefix("@")}',
            'key': self.config.api_key,
        }
        channel_response = requests.get(
            self.config.channels_endpoint,
            params=params,
            timeout=self.config.timeout_seconds,
        )

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
        if self.hit_rate_limit:
            msg = 'RateLimiterHit'
            raise RateLimitExceededError(msg)

        search_query = search_query.lower().strip()
        logger.debug('SearchingYoutube', query=search_query)

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

        if search_response.status_code == HTTP_403_FORBIDDEN:
            raise RateLimitExceededError(search_response.text)

        if search_response.status_code != HTTP_200_OK:
            msg = (
                f'Failed to fetch user data for "{search_query}": <{search_response.status_code}>{search_response.text}'
            )
            raise RuntimeError(msg)

        search_data = search_response.json()

        if 'items' not in search_data:
            return set()

        artist_ids: set[str] = set()

        if search_query.endswith(' topic'):
            raw_query = search_query.removesuffix(' topic').strip().removesuffix(' -').strip()
            name_candidates = {
                raw_query + ' - topic',
            }
        else:
            name_candidates = {search_query}

        for item in search_data['items']:
            if item['kind'] != 'youtube#searchResult':
                continue

            if item['id']['kind'] != 'youtube#channel':
                continue

            artist_id = item['id']['channelId']

            snippet = item['snippet']
            title = snippet['title'].lower().strip()
            channel_title = snippet['channelTitle'].lower().strip()

            artist_names = {
                title,
                channel_title,
            }

            if name_candidates & artist_names:
                logger.debug('FoundArtist', artist_id=artist_id, artist_name=snippet['title'])
                artist_ids.add(artist_id)

        return artist_ids
