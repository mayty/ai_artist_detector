import json
from typing import TYPE_CHECKING

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class IimuzykaIdsMappingRepository:
    tablename = 'iimuzyka_ids'

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
                f'CREATE TABLE {self.tablename} (iimuzyka_id INTEGER PRIMARY KEY, name TEXT, youtube_handles TEXT)'
            )
            connection.commit()

    def get_or_raise_youtube_handles(self, iimuzyka_id: int) -> set[str]:
        """
        Return youtube_ids or None if a record exists.
        Raises `RowNotFoundError` otherwise.
        """
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT youtube_handles FROM {self.tablename} WHERE iimuzyka_id=:iimuzyka_id',
                {'iimuzyka_id': iimuzyka_id},
            ).fetchone()
        if row is None:
            msg = f'Youtube handles for {iimuzyka_id} not found'
            raise RowNotFoundError(msg)
        return set(json.loads(row[0]))

    def set_youtube_handles(self, iimuzyka_id: int, name: str, youtube_handles: set[str]) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f'INSERT INTO {self.tablename} (iimuzyka_id, name, youtube_handles) VALUES (:iimuzyka_id, :name, :youtube_handles)',
                {
                    'iimuzyka_id': iimuzyka_id,
                    'name': name,
                    'youtube_handles': json.dumps(list(youtube_handles), ensure_ascii=False),
                },
            )
            connection.commit()
