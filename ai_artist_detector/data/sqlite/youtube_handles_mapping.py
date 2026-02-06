from typing import TYPE_CHECKING

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class YouTubeHandlesRepository:
    tablename = 'youtube_handles'

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

            connection.execute(f'CREATE TABLE {self.tablename} (youtube_handle TEXT PRIMARY KEY, youtube_id TEXT)')
            connection.commit()

    def get_or_raise_youtube_id(self, youtube_handle: str) -> str | None:
        """
        Return youtube_id or None if a record exists.
        Raises `RowNotFoundError` otherwise.
        """
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT youtube_id FROM {self.tablename} WHERE youtube_handle=:youtube_handle',
                {'youtube_handle': youtube_handle},
            ).fetchone()
        if row is None:
            msg = f'Youtube handle {youtube_handle} not found'
            raise RowNotFoundError(msg)
        return row[0]

    def set_youtube_id(self, youtube_handle: str, youtube_id: str | None) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f'INSERT INTO {self.tablename} (youtube_handle, youtube_id) VALUES (:youtube_handle, :youtube_id)',
                {'youtube_handle': youtube_handle, 'youtube_id': youtube_id},
            )
            connection.commit()
