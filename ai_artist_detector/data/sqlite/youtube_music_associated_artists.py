# This file has been created with the assistance of an AI tool.
import json
from datetime import datetime, UTC
from typing import TYPE_CHECKING

from loguru import logger

from ai_artist_detector.exceptions import RowNotFoundError

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager


class YouTubeMusicAssociatedArtistsRepository:
    table_name = 'youtube_music_associated_artists'

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

            connection.execute(
                f'CREATE TABLE {self.table_name} (main_id TEXT PRIMARY KEY, associated_artist_ids TEXT, created_at TEXT)'
            )

    def get_associated_artist_ids(self, main_id: str) -> set[str]:
        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT associated_artist_ids FROM {self.table_name} WHERE main_id=:main_id',
                {'main_id': main_id},
            ).fetchone()

        if row is None:
            msg = f'Associated artists for {main_id} not found'
            raise RowNotFoundError(msg)

        return set(json.loads(row[0]))

    def set_associated_artist_ids(self, main_id: str, artist_ids: set[str]) -> None:
        with self.connection_manager as connection:
            try:
                existing_artist_ids = self.get_associated_artist_ids(main_id)
                if existing_artist_ids != artist_ids:
                    logger.info(
                        'ReplacingAssociatedCache',
                        main_id=main_id,
                        old_artist_ids=existing_artist_ids,
                        new_artist_ids=artist_ids,
                    )
                else:
                    logger.debug('NoChangesInAssociatedCache', main_id=main_id)
            except RowNotFoundError:
                pass

            created_at = datetime.now(tz=UTC).isoformat()
            connection.execute(
                f"""
                INSERT INTO {self.table_name} (main_id, associated_artist_ids, created_at)
                VALUES (:main_id, :associated_artist_ids, :created_at)
                ON CONFLICT DO UPDATE SET
                    associated_artist_ids=excluded.associated_artist_ids,
                    created_at=excluded.created_at""",
                {
                    'main_id': main_id,
                    'associated_artist_ids': json.dumps(list(artist_ids), ensure_ascii=False),
                    'created_at': created_at,
                },
            )

            connection.commit()
