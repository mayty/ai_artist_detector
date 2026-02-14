import json
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class YouTubeMusicAliasesRepository:
    table_name = 'youtube_music_aliases'

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self.connection_manager = connection_manager

        with self.connection_manager as connection:
            table_exists = (
                connection.execute(
                    'SELECT name FROM sqlite_master WHERE type="table" AND name=:table_name',
                    {'table_name': self.table_name},
                ).fetchone()
                is not None
            )

            if table_exists:
                return

            connection.execute(f'CREATE TABLE {self.table_name} (main_id TEXT PRIMARY KEY, name TEXT, aliases TEXT)')

    def get_aliases(self, main_id: str) -> set[str]:
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT aliases FROM {self.table_name} WHERE main_id=:main_id', {'main_id': main_id}
            ).fetchone()

        if row is None:
            msg = f'Aliases for {main_id} not found'
            raise RowNotFoundError(msg)

        return set(json.loads(row[0]))

    def set_aliases(self, main_id: str, name: str, aliases: set[str]) -> None:
        with self.connection_manager as connection:
            try:
                existing_aliases = self.get_aliases(main_id)
                if existing_aliases != aliases:
                    logger.info(
                        'ReplacingAliasesCache', main_id=main_id, old_aliases=existing_aliases, new_aliases=aliases
                    )
                else:
                    logger.debug('NoChangesInAliasesCache', main_id=main_id)
            except RowNotFoundError:
                pass

            connection.execute(
                f"""
                INSERT INTO {self.table_name} (main_id, name, aliases) VALUES (:main_id, :name, :aliases)
                ON CONFLICT DO UPDATE SET name=excluded.name, aliases=excluded.aliases""",
                {'main_id': main_id, 'name': name, 'aliases': json.dumps(list(aliases), ensure_ascii=False)},
            )

            connection.commit()
