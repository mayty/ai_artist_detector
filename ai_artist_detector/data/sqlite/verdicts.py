# This file has been created with the assistance of an AI tool.
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class VerdictsRepository:
    tablename = 'verdicts'

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
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

            connection.execute(f'CREATE TABLE {self.tablename} (key TEXT PRIMARY KEY, artist_ids TEXT NOT NULL)')
            connection.commit()

    def get_ai(self) -> set[str]:
        with self.connection_manager as connection:
            row = connection.execute(f'SELECT artist_ids FROM {self.tablename} WHERE key="ai"').fetchone()
        if row is None:
            return set()
        return set(json.loads(row[0]))

    def set_ai(self, ai_ids: set[str]) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f"""
                    INSERT INTO {self.tablename} (key, artist_ids) VALUES ("ai", :artist_ids)
                    ON CONFLICT DO UPDATE SET artist_ids=excluded.artist_ids""",
                {'artist_ids': json.dumps(sorted(ai_ids))},
            )
            connection.commit()
