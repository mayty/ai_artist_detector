import json
from typing import TYPE_CHECKING

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class YoutubeSearchResultsRepository:
    tablename = 'youtube_search_results'

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
                f'CREATE TABLE {self.tablename} (query TEXT PRIMARY KEY, channel_ids TEXT, version INTEGER)'
            )
            connection.commit()

    def get_or_raise_artist_ids(self, query: str) -> tuple[set[str], int]:
        """
        Return artist IDs if a record exists.
        Raises `RowNotFoundError` otherwise.
        """
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT channel_ids, version FROM {self.tablename} WHERE query=:query',
                {'query': query},
            ).fetchone()
        if row is None:
            msg = f'YouTube channel_ids for {query} not found'
            raise RowNotFoundError(msg)
        return set(json.loads(row[0])), row[1]

    def set_artist_ids(self, query: str, youtube_paths: set[str], version: int) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f"""
                    INSERT INTO {self.tablename} (query, channel_ids, version) VALUES (:query, :channel_ids, :version)
                    ON CONFLICT DO UPDATE SET channel_ids=excluded.channel_ids, version=excluded.version""",
                {
                    'query': query,
                    'channel_ids': json.dumps(list(youtube_paths), ensure_ascii=False),
                    'version': version,
                },
            )
            connection.commit()

    def get_all(self) -> list[tuple[str, set[str]]]:
        with self.connection_manager as connection:
            rows = connection.execute(f'SELECT query, channel_ids FROM {self.tablename}').fetchall()

        return [(row[0], set(json.loads(row[1]))) for row in rows]
