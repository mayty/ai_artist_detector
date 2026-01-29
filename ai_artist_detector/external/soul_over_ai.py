import json
from functools import cache, cached_property
from typing import TYPE_CHECKING

import requests
from loguru import logger
from starlette.status import HTTP_200_OK
from ytmusicapi import YTMusic

from ai_artist_detector.exceptions import ChannelNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.config import SoulOverAiConfig


class SoulOverAiProxy:
    def __init__(self, config: SoulOverAiConfig):
        self.config = config
        self._raw_youtube_cache: dict[str, str] | None = None
        self._raw_ytm_cache: dict[str, list[str]] | None = None

    @cached_property
    def _yt_music_api(self) -> YTMusic:
        return YTMusic()

    @property
    def _cache(self) -> dict[str, str]:
        if self._raw_youtube_cache is None:
            try:
                with self.config.youtube_cache_location.open('rt', encoding='utf-8') as f:
                    self._raw_youtube_cache = json.load(f)
            except FileNotFoundError:
                self._raw_youtube_cache = {}
        assert self._raw_youtube_cache is not None
        return self._raw_youtube_cache

    def _update_youtube_cache(self, handle: str, youtube_id: str) -> None:
        self._cache[handle] = youtube_id
        with self.config.youtube_cache_location.open('wt', encoding='utf-8') as f:
            json.dump(self._cache, f, indent=4, ensure_ascii=False, sort_keys=True)

    @property
    def _ytm_cache(self) -> dict[str, list[str]]:
        if self._raw_ytm_cache is None:
            try:
                with self.config.youtube_music_cache_location.open('rt', encoding='utf-8') as f:
                    self._raw_ytm_cache = json.load(f)
            except FileNotFoundError:
                self._raw_ytm_cache = {}
        assert self._raw_ytm_cache is not None
        return self._raw_ytm_cache

    def _update_ytm_cache(self, youtube_id: str, aliases: list[str]) -> None:
        self._ytm_cache[youtube_id] = aliases
        with self.config.youtube_music_cache_location.open('wt', encoding='utf-8') as f:
            json.dump(self._ytm_cache, f, indent=4, ensure_ascii=False, sort_keys=True)

    def _conver_youtube_handle_to_id(self, artist_handle: str) -> str:
        if artist_handle in self._cache:
            return self._cache[artist_handle]

        logger.debug('ConvertingYoutubeToYoutubeMusic', handle=artist_handle)
        channel_response = requests.get(
            'https://youtube.googleapis.com/youtube/v3/channels',
            params={
                'forHandle': artist_handle,
                'key': self.config.google_api_key,
            },
            timeout=10,
        )

        if channel_response.status_code != HTTP_200_OK:
            msg = f'Failed to fetch user data for {artist_handle}: <{channel_response.status_code}>{channel_response.text!r}'
            raise RuntimeError(msg)

        channel_data = channel_response.json()

        if 'items' not in channel_data:
            raise ChannelNotFoundError(handle=artist_handle)

        for item in channel_data['items']:
            if item['kind'] != 'youtube#channel':
                continue
            youtube_id = item['id']

            self._update_youtube_cache(artist_handle, youtube_id)
            return youtube_id

        msg = f'Failed to find channel id for {artist_handle}'
        raise RuntimeError(msg)

    def _get_ytm_id_aliases(self, youtube_id: str) -> list[str]:
        if youtube_id in self._ytm_cache:
            return self._ytm_cache[youtube_id]

        logger.debug('RetrievingYoutubeMusicAliases', youtube_id=youtube_id)

        try:
            response = self._yt_music_api.get_artist(youtube_id)
        except KeyError as exc:
            logger.warning('FailedToFetchArtistData', youtube_id=youtube_id, exc=exc)
            self._update_ytm_cache(youtube_id, [])
            return []

        artist_name = response['name']
        channel_id = response['channelId']

        aliases: set[str] = set()

        if channel_id != youtube_id:
            aliases.add(channel_id)

        song_results = response['songs'].get('results', [])
        if not song_results:
            logger.warning('NoSongsFound', youtube_id=youtube_id, artist_name=artist_name)

        for song in song_results:
            for artist in song['artists']:
                if artist['name'] == artist_name:
                    alias = artist['id']
                    if alias != youtube_id:
                        aliases.add(alias)

        aliases_list = list(aliases)
        logger.debug('FoundAliases', youtube_id=youtube_id, name=artist_name, aliases=aliases_list)
        self._update_ytm_cache(youtube_id, aliases_list)
        return aliases_list

    def save_data(self) -> None:
        response = requests.get(str(self.config.source), timeout=10)
        response.raise_for_status()

        ai_artists: dict[str, str] = {}

        for artist_data in response.json():
            youtube_id = artist_data['youtube']
            if youtube_id is None:
                continue

            assert isinstance(youtube_id, str), f'Expected str, got {type(youtube_id).__name__}'

            name = artist_data['name']
            assert isinstance(name, str), f'Expected str, got {type(name).__name__}'

            if youtube_id.startswith('@'):
                try:
                    youtube_id = self._conver_youtube_handle_to_id(youtube_id)
                except ChannelNotFoundError:
                    logger.warning('FailedToFindChannelId', channel_handle=youtube_id, name=name)
                    continue

            if not youtube_id.startswith('UC'):
                logger.warning('UnknownHandleFormat', youtube_id=youtube_id, name=name)
                continue

            ai_artists[youtube_id] = name
            for alias in self._get_ytm_id_aliases(youtube_id):
                ai_artists[alias] = name

        self.config.file_location.parent.mkdir(parents=True, exist_ok=True)
        self.config.file_location.write_text(
            json.dumps(ai_artists, indent=4, ensure_ascii=False, sort_keys=True), encoding='utf-8'
        )

    @cache  # noqa: B019
    def get_ai_artists(self) -> set[str]:
        with self.config.file_location.open(encoding='utf-8') as f:
            return set(json.load(f).keys())
