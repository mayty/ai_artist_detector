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

    def get_ids(self, key: str) -> set[str]:
        with self.connection_manager as connection:
            row = connection.execute(f'SELECT artist_ids FROM {self.tablename} WHERE key=:key', {'key': key}).fetchone()
        if row is None:
            return set()
        return set(json.loads(row[0]))

    def set_ids(self, key: str, artist_ids: set[str]) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f"""
                    INSERT INTO {self.tablename} (key, artist_ids) VALUES (:key, :artist_ids)
                    ON CONFLICT DO UPDATE SET artist_ids=excluded.artist_ids""",
                {'key': key, 'artist_ids': json.dumps(sorted(artist_ids))},
            )
            connection.commit()

    def get_ai(self) -> set[str]:
        return self.get_ids('ai')

    def set_ai(self, ai_ids: set[str]) -> None:
        self.set_ids('ai', ai_ids)

    def get_associated(self) -> set[str]:
        return self.get_ids('associated')

    def set_associated(self, associated_ids: set[str]) -> None:
        self.set_ids('associated', associated_ids)
