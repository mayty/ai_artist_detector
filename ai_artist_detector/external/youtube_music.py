from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from ytmusicapi import YTMusic


class YouTubeMusicClient:
    def __init__(self, client: YTMusic) -> None:
        self.client = client

    def get_ytm_id_aliases(self, youtube_id: str) -> tuple[str, list[str]]:
        logger.debug('RetrievingYoutubeMusicAliases', youtube_id=youtube_id)

        try:
            response = self.client.get_artist(youtube_id)
        except KeyError as exc:
            # Different channel type
            logger.warning('FailedToFetchArtistData', youtube_id=youtube_id, exc=exc)
            return '', []

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
                if artist['name'] != artist_name:
                    continue
                alias = artist['id']
                if alias == youtube_id:
                    continue
                aliases.add(alias)

        aliases_list = list(aliases)
        logger.debug('FoundAliases', youtube_id=youtube_id, name=artist_name, aliases=aliases_list)
        return artist_name, aliases_list
