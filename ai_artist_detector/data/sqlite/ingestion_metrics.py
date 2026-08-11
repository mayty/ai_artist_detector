# This file has been created with the assistance of an AI tool.
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.connection_manager import SQLiteConnectionManager
    from ai_artist_detector.domain.metrics_service import IngestionRunStats


class MetricsRepository:
    tablename = 'ingestion_runs'

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

            connection.execute(
                f'CREATE TABLE {self.tablename} ('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'started_at TEXT NOT NULL, '
                'finished_at TEXT NOT NULL, '
                'ingestion_run_duration_seconds REAL NOT NULL, '
                'ingestion_last_run_timestamp_seconds REAL NOT NULL, '
                'ingestion_artists_cached INTEGER NOT NULL, '
                'ingestion_artists_new INTEGER NOT NULL, '
                'ingestion_artist_ids_added INTEGER NOT NULL, '
                'ingestion_artist_alias_ids INTEGER NOT NULL, '
                'ingestion_unmatched_count INTEGER NOT NULL, '
                'stage_metrics TEXT NOT NULL, '
                'source_metrics TEXT NOT NULL)'
            )
            connection.commit()

    def record_run(self, stats: IngestionRunStats) -> None:
        with self.connection_manager as connection:
            connection.execute(
                f'INSERT INTO {self.tablename} ('
                'started_at, finished_at, ingestion_run_duration_seconds, '
                'ingestion_last_run_timestamp_seconds, ingestion_artists_cached, '
                'ingestion_artists_new, ingestion_artist_ids_added, '
                'ingestion_artist_alias_ids, '
                'ingestion_unmatched_count, stage_metrics, source_metrics) '
                'VALUES (:started_at, :finished_at, :duration_seconds, :last_run_timestamp, '
                ':artists_cached, :artists_new, :artist_ids_added, :artist_alias_ids, :unmatched_count, '
                ':stage_metrics, :source_metrics)',
                {
                    'started_at': stats.started_at.isoformat(),
                    'finished_at': stats.finished_at.isoformat(),
                    'duration_seconds': stats.ingestion_run_duration_seconds,
                    'last_run_timestamp': stats.ingestion_last_run_timestamp_seconds,
                    'artists_cached': stats.ingestion_artists_cached,
                    'artists_new': stats.ingestion_artists_new,
                    'artist_ids_added': stats.ingestion_artist_ids_added,
                    'artist_alias_ids': stats.ingestion_artist_alias_ids,
                    'unmatched_count': stats.ingestion_unmatched_count,
                    'stage_metrics': json.dumps(stats.stage_metrics),
                    'source_metrics': json.dumps(stats.source_metrics),
                },
            )
            connection.commit()

    def get_last_run(self) -> IngestionRunStats | None:
        from datetime import datetime

        from ai_artist_detector.domain.metrics_service import IngestionRunStats

        with self.connection_manager as connection:
            row = connection.execute(
                f'SELECT started_at, finished_at, ingestion_run_duration_seconds, '
                'ingestion_last_run_timestamp_seconds, ingestion_artists_cached, '
                'ingestion_artists_new, ingestion_artist_ids_added, '
                'ingestion_artist_alias_ids, '
                'ingestion_unmatched_count, stage_metrics, source_metrics '
                f'FROM {self.tablename} ORDER BY id DESC LIMIT 1'
            ).fetchone()
        if row is None:
            return None
        return IngestionRunStats(
            started_at=datetime.fromisoformat(row[0]),
            finished_at=datetime.fromisoformat(row[1]),
            ingestion_run_duration_seconds=row[2],
            ingestion_last_run_timestamp_seconds=row[3],
            ingestion_artists_cached=row[4],
            ingestion_artists_new=row[5],
            ingestion_artist_ids_added=row[6],
            ingestion_artist_alias_ids=row[7],
            ingestion_unmatched_count=row[8],
            stage_metrics=json.loads(row[9]),
            source_metrics=json.loads(row[10]),
        )
