import string
from contextlib import contextmanager
from typing import overload, TYPE_CHECKING
from unicodedata import combining, normalize
from urllib.parse import unquote

from loguru import logger

from ai_artist_detector.exceptions import InvalidYoutubeMusicAccountTypeError
from ai_artist_detector.lib.helpers import rate_limit, singular_cache

if TYPE_CHECKING:
    from collections.abc import Generator

    from ytmusicapi import YTMusic


class YouTubeMusicClient:
    def __init__(self, client: YTMusic) -> None:
        self.client = client

    @overload
    def _unescape_name(self, name: str) -> str: ...

    @overload
    def _unescape_name(self, name: None) -> None: ...

    def _unescape_name(self, name: str | None) -> str | None:
        if name is None:
            return name
        return unquote(name)

    @overload
    def _normalize_name(self, name: str) -> str | None: ...

    @overload
    def _normalize_name(self, name: None) -> None: ...

    def _normalize_name(self, name: str | None) -> str | None:
        if name is None:
            return name
        normalized = normalize('NFKD', self._unescape_name(name)).lower().replace('&', 'and')
        normalized = ''.join(a for a in normalized if not combining(a)).strip().removeprefix('the ')

        return ''.join(a for a in normalized if a not in string.punctuation and a not in string.whitespace) or None

    def _get_name_variations(self, name: str) -> set[str]:
        normalized_base = self._normalize_name(name)

        return {
            *({normalized_base} if normalized_base else []),
            *(normalized for suffix in ['official'] if (normalized := self._normalize_name(f'{name} {suffix}'))),
        }

    def _get_alias_from_element(self, song: dict, artist_name: str, *, validate_name: bool = True) -> Generator[str]:
        potential_names = self._get_name_variations(artist_name)

        artists = song['artists']
        if len(artists) == 1:  # If an element has only one artist, assume it's the target artist
            alias = artists[0]['id']
            if alias is None:
                return
            artist_names = self._get_name_variations(artists[0]['name'])
            if validate_name and not (artist_names & potential_names):
                return
            yield alias
        else:
            for artist in song['artists']:
                artist_names = self._get_name_variations(artist['name'])
                if not (artist_names & potential_names):
                    continue
                alias = artist['id']
                if alias is None:
                    continue
                yield alias

    @contextmanager
    def _cache_ytm_request(self) -> Generator[None]:

        old_send_request = self.client._send_request  # noqa: SLF001
        try:
            self.client._send_request = singular_cache(self.client._send_request)  # noqa: SLF001
            yield
        finally:
            self.client._send_request = old_send_request  # noqa: SLF001

    @rate_limit(rps=0.2)
    def _get_ytm_response(self, youtube_id: str) -> dict:
        try:
            return self.client.get_artist(youtube_id)
        except KeyError:
            logger.debug('ChannelIsNotArtist', youtube_id=youtube_id)

        try:
            return self.client.get_user(youtube_id)
        except KeyError as exc:
            logger.debug('ChannelIsNotUser', youtube_id=youtube_id)
            raise InvalidYoutubeMusicAccountTypeError(youtube_id, reason=str(exc)) from exc

    def get_ytm_id_aliases(self, youtube_id: str) -> tuple[str, list[str]]:
        logger.info('RetrievingYoutubeMusicAliases', youtube_id=youtube_id)

        with self._cache_ytm_request():
            response = self._get_ytm_response(youtube_id)

        artist_name = self._unescape_name(response['name'])
        if artist_name is None:
            raise InvalidYoutubeMusicAccountTypeError(youtube_id, reason='No artist name found')

        logger.info('FetchingForName', youtube_id=youtube_id, artist_name=artist_name, normalized_name=self._normalize_name(artist_name))

        aliases: set[str] = set()

        if (channel_id := response.get('channelId')) is not None:
            aliases.add(channel_id)

        song_results = response.get('songs', {}).get('results', [])
        if not song_results:
            logger.warning('NoSongsFound', youtube_id=youtube_id, artist_name=artist_name)

        for song in song_results:
            aliases.update(self._get_alias_from_element(song, artist_name))

        video_results = response.get('videos', {}).get('results', [])
        if not video_results:
            logger.warning('NoVideosFound', youtube_id=youtube_id, artist_name=artist_name)

        for video in video_results:
            aliases.update(self._get_alias_from_element(video, artist_name, validate_name=True))

        aliases_list = list(aliases - {youtube_id})
        logger.info('FoundAliases', youtube_id=youtube_id, name=artist_name, aliases=aliases_list)
        return artist_name, aliases_list
