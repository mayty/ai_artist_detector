from contextlib import contextmanager
from typing import Literal, overload, TYPE_CHECKING

from loguru import logger

from ai_artist_detector.exceptions import InvalidYoutubeMusicAccountTypeError, NoSongsFoundError
from ai_artist_detector.lib.helpers import rate_limit, singular_cache
from ai_artist_detector.lib.web_helpers import names_match, normalize_name, unescape_name

if TYPE_CHECKING:
    from collections.abc import Generator

    from ytmusicapi import YTMusic


class YouTubeMusicClient:
    def __init__(self, client: YTMusic) -> None:
        self.client = client

    def _get_alias_from_element(self, element: dict, artist_name: str, *, validate_name: bool = True) -> Generator[str]:
        artists = element['artists']
        if len(artists) == 1:  # If an element has only one artist, assume it's the target artist
            alias = artists[0]['id']
            if alias is None:
                return
            candidate_name = artists[0]['name']
            if candidate_name is None:
                return
            if validate_name and not names_match(artist_name, candidate_name):
                return
            yield alias
        else:
            for artist in element['artists']:
                candidate_name = artist['name']
                if candidate_name is None:
                    continue
                if not names_match(artist_name, candidate_name):
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

    def _get_ytm_profile(self, youtube_id: str) -> dict:
        try:
            return self.client.get_artist(youtube_id)
        except KeyError:
            logger.debug('ChannelIsNotArtist', youtube_id=youtube_id)

        try:
            return self.client.get_user(youtube_id)
        except KeyError:
            logger.debug('ChannelIsNotUser', youtube_id=youtube_id)

        logger.error('FailedToFetchYtmProfile', youtube_id=youtube_id)
        return {}

    def _get_songs(self, browse_id: str) -> set[str]:
        response = self.client.get_playlist(browse_id)

        songs: set[str] = set()
        for track in response.get('tracks', []):
            track_title = track.get('title')
            if not track_title:
                continue
            songs.add(unescape_name(track_title))
        return songs

    @overload
    def _get_ytm_response(self, youtube_id: str, type_: Literal['profile']) -> dict: ...

    @overload
    def _get_ytm_response(self, youtube_id: str, type_: Literal['playlist']) -> set[str]: ...

    @rate_limit(rps=0.2)
    def _get_ytm_response(self, youtube_id: str, type_: Literal['profile', 'playlist']) -> dict | set[str]:
        logger.info('FetchingYoutubeMusicData', youtube_id=youtube_id, type_=type_)
        match type_:
            case 'profile':
                return self._get_ytm_profile(youtube_id)
            case 'playlist':
                return self._get_songs(youtube_id)
        msg = f'Invalid type: {type_}'
        raise ValueError(msg)

    def get_ytm_id_aliases(self, youtube_id: str) -> tuple[str, set[str], bool]:
        logger.debug('RetrievingYoutubeMusicAliases', youtube_id=youtube_id)
        can_cache_empty_results = False

        with self._cache_ytm_request():
            response = self._get_ytm_response(youtube_id, type_='profile')

        artist_name = unescape_name(response.get('name'))
        if artist_name is None:
            raise InvalidYoutubeMusicAccountTypeError(youtube_id, reason='No artist name found')

        logger.info(
            'FetchingForName',
            youtube_id=youtube_id,
            artist_name=artist_name,
            normalized_name=normalize_name(artist_name),
        )

        aliases: set[str] = set()

        if (channel_id := response.get('channelId')) is not None:
            aliases.add(channel_id)

        song_results = response.get('songs', {}).get('results', [])
        if song_results:
            can_cache_empty_results = True
        else:
            logger.warning('NoSongsFound', youtube_id=youtube_id, artist_name=artist_name)

        for song in song_results:
            aliases.update(self._get_alias_from_element(song, artist_name))

        video_results = response.get('videos', {}).get('results', [])
        if video_results:
            can_cache_empty_results = True
        else:
            logger.warning('NoVideosFound', youtube_id=youtube_id, artist_name=artist_name)

        for video in video_results:
            aliases.update(self._get_alias_from_element(video, artist_name, validate_name=True))

        aliases = aliases - {youtube_id}
        if aliases:
            logger.info('FoundAliases', youtube_id=youtube_id, name=artist_name, aliases=aliases)
        else:
            logger.debug('NoAliasesFound', youtube_id=youtube_id, name=artist_name)
        return artist_name, aliases, can_cache_empty_results

    def artist_has_tracks_overlap(self, youtube_id: str, tracks: set[str]) -> bool:
        with self._cache_ytm_request():
            response = self._get_ytm_response(youtube_id, type_='profile')

        songs_data = response.get('songs', {})
        if not songs_data:
            logger.warning('NoSongsFound', youtube_id=youtube_id)
            raise NoSongsFoundError

        if songs_browse_id := songs_data.get('browseId'):
            artist_songs = self._get_ytm_response(songs_browse_id, type_='playlist')
        else:
            # Can happen if an artist has very few songs
            logger.debug('NoSongsBrowseIdFound', youtube_id=youtube_id)
            artist_songs = {
                unescape_name(song_title) for song in songs_data.get('results', []) if (song_title := song.get('title'))
            }

        if not artist_songs:
            logger.warning('NoSongsFound', youtube_id=youtube_id)
            return False

        logger.info(
            'CheckingForTracksOverlap',
            youtube_id=youtube_id,
            known_tracks_count=len(tracks),
            artist_songs_count=len(artist_songs),
        )

        for song in artist_songs:
            for artist_track in tracks:
                if names_match(song, artist_track):
                    logger.info('FoundTracksOverlap', youtube_id=youtube_id, known_track=artist_track, song_title=song)
                    return True

        logger.info('NoTracksOverlap', youtube_id=youtube_id)
        return False
