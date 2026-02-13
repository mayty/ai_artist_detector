from typing import TYPE_CHECKING
from urllib.parse import unquote

from loguru import logger

from ai_artist_detector.exceptions import InvalidYoutubeMusicAccountTypeError

if TYPE_CHECKING:
    from collections.abc import Generator

    from ytmusicapi import YTMusic


class YouTubeMusicClient:
    def __init__(self, client: YTMusic) -> None:
        self.client = client

    def _unquote_name(self, name: str | None) -> str | None:
        if name is None:
            return name
        return unquote(name)

    def _get_alias_from_song(self, song: dict, artist_name: str) -> Generator[str]:
        artists = song['artists']
        if len(artists) == 1:  # If a song has only one artist, assume it's the target artist
            alias = artists[0]['id']
            if alias is None:
                return
            yield alias
        else:
            for artist in song['artists']:
                if self._unquote_name(artist['name']) != artist_name:
                    continue
                alias = artist['id']
                if alias is None:
                    continue
                yield alias

    def get_ytm_id_aliases(self, youtube_id: str) -> tuple[str, list[str]]:
        logger.info('RetrievingYoutubeMusicAliases', youtube_id=youtube_id)

        try:
            response = self.client.get_artist(youtube_id)
        except KeyError as exc:
            # Different channel type
            raise InvalidYoutubeMusicAccountTypeError(youtube_id, reason=str(exc)) from exc

        artist_name = self._unquote_name(response['name'])
        if artist_name is None:
            raise InvalidYoutubeMusicAccountTypeError(youtube_id, reason='No artist name found')
        channel_id = response['channelId']

        aliases: set[str] = set()

        if channel_id is not None:
            aliases.add(channel_id)

        song_results = response['songs'].get('results', [])
        if not song_results:
            logger.warning('NoSongsFound', youtube_id=youtube_id, artist_name=artist_name)

        for song in song_results:
            aliases.update(self._get_alias_from_song(song, artist_name))

        aliases_list = list(aliases - {youtube_id})
        logger.info('FoundAliases', youtube_id=youtube_id, name=artist_name, aliases=aliases_list)
        return artist_name, aliases_list
