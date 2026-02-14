from sqlite3 import connect, Connection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_artist_detector.config import SqliteConfig


class SQLiteConnectionManager:
    def __init__(self, config: SqliteConfig) -> None:
        self.config = config
        self._connection: Connection | None = None
        self._decorator_depth = 0

    def __enter__(self) -> Connection:
        self._connection = connect(self.config.resolved_file_location)
        self._decorator_depth += 1
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._connection is None:
            msg = 'Connection already destroyed'
            raise RuntimeError(msg)

        if self._decorator_depth <= 0:
            msg = 'Broken manager nesting'
            raise RuntimeError(msg)

        self._decorator_depth -= 1

        if self._decorator_depth == 0:
            self._connection.close()
            self._connection = None
