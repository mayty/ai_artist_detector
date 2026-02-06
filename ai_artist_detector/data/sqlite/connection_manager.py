from sqlite3 import connect, Connection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_artist_detector.config import SqliteConfig


class SQLiteConnectionManager:
    def __init__(self, config: SqliteConfig) -> None:
        self.config = config
        self._connection: Connection | None = None

    def __enter__(self) -> Connection:
        if self._connection is not None:
            msg = 'Connection already exists'
            raise RuntimeError(msg)

        self._connection = connect(self.config.resolved_file_location)
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._connection is None:
            return

        self._connection.close()
        self._connection = None
