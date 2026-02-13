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
                f'CREATE TABLE {self.tablename} (iimuzyka_id INTEGER PRIMARY KEY, name TEXT, youtube_paths TEXT)'
            )
            connection.commit()

    def _get_paths_from_str(self, value: str) -> list[tuple[str, list[tuple[str, str]]]]:
        decoded = json.loads(value)
        return [
            (path, [(param_name, param_value) for param_name, param_value in query_params])
            for path, query_params in decoded
        ]

    def get_or_raise_youtube_paths(self, iimuzyka_id: int) -> list[tuple[str, list[tuple[str, str]]]]:
        """
        Return youtube_paths if a record exists.
        Raises `RowNotFoundError` otherwise.
        """
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT youtube_paths FROM {self.tablename} WHERE iimuzyka_id=:iimuzyka_id',
                {'iimuzyka_id': iimuzyka_id},
            ).fetchone()
        if row is None:
            msg = f'YouTube paths for {iimuzyka_id} not found'
            raise RowNotFoundError(msg)
        return self._get_paths_from_str(row[0])

    def set_youtube_paths(
        self, iimuzyka_id: int, name: str, youtube_paths: list[tuple[str, list[tuple[str, str]]]]
    ) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f'INSERT INTO {self.tablename} (iimuzyka_id, name, youtube_paths) VALUES (:iimuzyka_id, :name, :youtube_paths)',
                {
                    'iimuzyka_id': iimuzyka_id,
                    'name': name,
                    'youtube_paths': json.dumps(youtube_paths, ensure_ascii=False),
                },
            )
            connection.commit()

    def get_all(self) -> list[tuple[int, str, list[tuple[str, list[tuple[str, str]]]]]]:
        with self.connection_manager as connection:
            rows = connection.execute(f'SELECT iimuzyka_id, name, youtube_paths FROM {self.tablename}').fetchall()

        return [(row[0], row[1], self._get_paths_from_str(row[2])) for row in rows]
