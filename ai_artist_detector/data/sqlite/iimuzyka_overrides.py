from typing import TYPE_CHECKING

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class IimuzykaOverridesRepository:
    tablename = 'iimuzyka_overrides'

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

            connection.execute(f'CREATE TABLE {self.tablename} (iimuzyka_id INTEGER PRIMARY KEY, youtube_handle TEXT)')
            connection.commit()

    def get_or_raise_override(self, iimuzyka_id: int) -> str:
        """
        Return handle if a record exists.
        Raises `RowNotFoundError` otherwise.
        """
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT youtube_handle FROM {self.tablename} WHERE iimuzyka_id=:iimuzyka_id',
                {'iimuzyka_id': iimuzyka_id},
            ).fetchone()
        if row is None:
            msg = f'YouTube handle for {iimuzyka_id} not found'
            raise RowNotFoundError(msg)
        return row[0]

    def set_override(self, iimuzyka_id: int, youtube_handle: str) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f'INSERT INTO {self.tablename} (iimuzyka_id, youtube_handle) VALUES (:iimuzyka_id, :youtube_handle)',
                {
                    'iimuzyka_id': iimuzyka_id,
                    'youtube_handle': youtube_handle,
                },
            )
            connection.commit()
