import json
from typing import TYPE_CHECKING

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class IimuzykaYouTubeMusicArtistMatchesRepository:
    tablename = 'iimuzyka_youtube_music_artist_matches'

    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager

        with self.connection_manager as connection:
            table_exists = (
                connection.execute(
                    'SELECT name FROM sqlite_master WHERE type="table" AND name=:tablename',
                    {'tablename': self.tablename},
                ).fetchone()
                is not None
            )

            if table_exists:
                return

            connection.execute(
                f'CREATE TABLE {self.tablename} (iimuzyka_id INTEGER, youtube_id TEXT, is_match INTEGER, PRIMARY KEY (iimuzyka_id, youtube_id))'
            )
            connection.commit()

    def _get_paths_from_str(self, value: str) -> list[tuple[str, list[tuple[str, str]]]]:
        decoded = json.loads(value)
        return [
            (path, [(param_name, param_value) for param_name, param_value in query_params])
            for path, query_params in decoded
        ]

    def is_match(self, iimuzyka_id: int, youtube_id: str) -> bool:
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT is_match FROM {self.tablename} WHERE iimuzyka_id=:iimuzyka_id AND youtube_id=:youtube_id',
                {'iimuzyka_id': iimuzyka_id, 'youtube_id': youtube_id},
            ).fetchone()
        if row is None:
            msg = f'Match status for {iimuzyka_id} and {youtube_id} not found'
            raise RowNotFoundError(msg)
        return row[0] == 1

    def set_match_status(self, iimuzyka_id: int, youtube_id: str, is_match: bool) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f'INSERT INTO {self.tablename} (iimuzyka_id, youtube_id, is_match) VALUES (:iimuzyka_id, :youtube_id, :is_match)',
                {'iimuzyka_id': iimuzyka_id, 'youtube_id': youtube_id, 'is_match': int(is_match)},
            )
            connection.commit()
