# This file has been edited with the assistance of an AI tool.
import asyncio
from datetime import datetime
from sqlite3 import Error as SQLiteError
from typing import TYPE_CHECKING

from loguru import logger
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest, Histogram
from pydantic import BaseModel, Field

from ai_artist_detector.constants import EndpointLabels, MetricName

if TYPE_CHECKING:
    from ai_artist_detector.data.sqlite.ingestion_metrics import MetricsRepository

CONTENT_TYPE_LATEST = 'text/plain; version=0.0.4; charset=utf-8'

NO_LABELS: list[str] = []


class IngestionRunStats(BaseModel):
    started_at: datetime
    finished_at: datetime
    ingestion_run_duration_seconds: float
    ingestion_last_run_timestamp_seconds: float
    ingestion_artists_cached: int
    ingestion_artists_new: int
    ingestion_artist_ids_added: int
    ingestion_artist_alias_ids: int
    ingestion_unmatched_count: int
    stage_metrics: dict[str, dict[str, int]] = Field(default_factory=dict)
    source_metrics: dict[str, dict[str, int]] = Field(default_factory=dict)


class MetricsSnapshot(BaseModel):
    verdicts_ai_count: int | None = None
    verdicts_associated_count: int | None = None
    last_run: IngestionRunStats | None = None


class MetricsService:
    _INGESTION_METRICS = (
        MetricName.INGESTION_RUN_DURATION_SECONDS,
        MetricName.INGESTION_LAST_RUN_TIMESTAMP_SECONDS,
        MetricName.INGESTION_ARTISTS_CACHED,
        MetricName.INGESTION_ARTISTS_NEW,
        MetricName.INGESTION_ARTIST_IDS_ADDED,
        MetricName.INGESTION_ARTIST_ALIAS_IDS,
        MetricName.INGESTION_UNMATCHED_COUNT,
    )

    def __init__(self, registry: CollectorRegistry, metrics_repository: MetricsRepository) -> None:
        self.registry = registry
        self.metrics_repository = metrics_repository
        self._snapshot: MetricsSnapshot | None = None

        self._http_requests_total = Counter(
            MetricName.HTTP_REQUESTS_TOTAL, 'Total HTTP requests', ['method', 'path', 'status'], registry=self.registry
        )
        self._artist_ids_requested_total = Counter(
            MetricName.ARTIST_IDS_REQUESTED_TOTAL, 'Total artist IDs requested', ['endpoint'], registry=self.registry
        )
        self._artist_ids_checked_ai_total = Counter(
            MetricName.ARTIST_IDS_CHECKED_AI_TOTAL,
            'Requested artist IDs classified as AI',
            ['endpoint'],
            registry=self.registry,
        )
        self._http_request_duration_seconds = Histogram(
            MetricName.HTTP_REQUEST_DURATION_SECONDS,
            'HTTP request latency',
            ['method', 'path'],
            registry=self.registry,
        )
        self._gauges = {
            name: Gauge(name, desc, labels, registry=self.registry)
            for name, desc, labels in (
                (MetricName.AI_ARTISTS_IN_DB, 'Number of AI artists in the verdicts database', NO_LABELS),
                (
                    MetricName.ASSOCIATED_ARTISTS_IN_DB,
                    'Number of associated artists in the verdicts database',
                    NO_LABELS,
                ),
                (
                    MetricName.INGESTION_RUN_DURATION_SECONDS,
                    'Duration of the last ingestion run in seconds',
                    NO_LABELS,
                ),
                (
                    MetricName.INGESTION_LAST_RUN_TIMESTAMP_SECONDS,
                    'Unix timestamp of the last successful ingestion run',
                    NO_LABELS,
                ),
                (
                    MetricName.INGESTION_ARTISTS_CACHED,
                    'Number of AI artists cached after the last ingestion run',
                    NO_LABELS,
                ),
                (
                    MetricName.INGESTION_ARTISTS_NEW,
                    'Number of new AI artists (not previously in DB) from the last run',
                    NO_LABELS,
                ),
                (
                    MetricName.INGESTION_ARTIST_IDS_ADDED,
                    'Total artist IDs retrieved by all sources in the last run',
                    NO_LABELS,
                ),
                (
                    MetricName.INGESTION_ARTIST_ALIAS_IDS,
                    'Total number of alias IDs discovered in the last run',
                    NO_LABELS,
                ),
                (
                    MetricName.INGESTION_UNMATCHED_COUNT,
                    'Number of artists that could not be properly matched in the last run',
                    NO_LABELS,
                ),
            )
        }

    def record_http_request(
        self, method: str, path: str, status: int, duration_seconds: float, *, is_known_path: bool = False
    ) -> None:
        if is_known_path:
            self._http_requests_total.labels(method, path, str(status)).inc()
            self._http_request_duration_seconds.labels(method, path).observe(duration_seconds)
        else:
            self._http_requests_total.labels(method, 'unknown_path', str(status)).inc()

    def record_artist_ids_requested(self, endpoint: EndpointLabels, count: int) -> None:
        self._artist_ids_requested_total.labels(endpoint).inc(count)

    def record_artist_ids_checked_ai(self, endpoint: EndpointLabels, count: int) -> None:
        self._artist_ids_checked_ai_total.labels(endpoint).inc(count)

    async def record_run(self, stats: IngestionRunStats) -> None:
        try:
            await asyncio.to_thread(self.metrics_repository.record_run, stats)
        except SQLiteError:
            logger.exception('FailedToRecordIngestionMetrics')

    async def get_last_run(self) -> IngestionRunStats | None:
        try:
            return await asyncio.to_thread(self.metrics_repository.get_last_run)
        except SQLiteError:
            logger.exception('FailedToReadLastRun')
            return None

    def update_snapshot(self, snapshot: MetricsSnapshot | None) -> None:
        """
        Set every gauge on every call so stale values can never linger.

        Missing data (failed snapshot or no ingestion run) sets NaN — distinct
        from any valid value, since 0 is a legitimate count.
        """
        self._snapshot = snapshot
        if snapshot is None:
            for gauge in self._gauges.values():
                gauge.set(float('nan'))
            return

        if snapshot.verdicts_ai_count is not None:
            self._gauges[MetricName.AI_ARTISTS_IN_DB].set(snapshot.verdicts_ai_count)
        else:
            self._gauges[MetricName.AI_ARTISTS_IN_DB].set(float('nan'))

        if snapshot.verdicts_associated_count is not None:
            self._gauges[MetricName.ASSOCIATED_ARTISTS_IN_DB].set(snapshot.verdicts_associated_count)
        else:
            self._gauges[MetricName.ASSOCIATED_ARTISTS_IN_DB].set(float('nan'))

        if snapshot.last_run is not None:
            run = snapshot.last_run
            for metric in self._INGESTION_METRICS:
                self._gauges[metric].set(getattr(run, metric))
        else:
            for metric in self._INGESTION_METRICS:
                self._gauges[metric].set(float('nan'))

    def render_latest(self) -> tuple[bytes, str]:
        output = generate_latest(self.registry)

        if self._snapshot is not None and self._snapshot.last_run is not None:
            run = self._snapshot.last_run
            manual = self._render_stage_metrics(run) + self._render_source_metrics(run)
            if manual:
                # generate_latest does not emit `# EOF`; stage/source metrics are
                # appended as additional metric families before the EOF marker
                output = output.removesuffix(b'# EOF\n') + manual.encode() + b'# EOF\n'

        return output, CONTENT_TYPE_LATEST

    @staticmethod
    def _render_stage_metrics(run: IngestionRunStats) -> str:
        """Render per-stage metrics: `ingestion_stage_<category>{stage=...}` gauges."""
        return MetricsService._render_category_metrics(run.stage_metrics, 'ingestion_stage', 'stage')

    @staticmethod
    def _render_source_metrics(run: IngestionRunStats) -> str:
        """Render per-source aggregates: `ingestion_source_<metric>{source=...}` gauges."""
        return MetricsService._render_category_metrics(run.source_metrics, 'ingestion_source', 'source')

    @staticmethod
    def _render_category_metrics(metrics: dict[str, dict[str, int]], metric_prefix: str, label_name: str) -> str:
        """Render `{category}` gauges labeled by stage/source, emitting only what the run recorded."""
        lines: list[str] = []
        categories: dict[str, list[tuple[str, int]]] = {}

        for label_value, category_counts in metrics.items():
            for category, count in category_counts.items():
                categories.setdefault(category, []).append((label_value, count))

        for category, entries in sorted(categories.items()):
            metric_name = f'{metric_prefix}_{category}'
            lines.append(f'# HELP {metric_name} {category.replace("_", " ")} by {label_name} in the last run')
            lines.append(f'# TYPE {metric_name} gauge')
            for label_value, count in entries:
                lines.append(f'{metric_name}{{{label_name}="{label_value}"}} {count}')

        return ('\n'.join(lines) + '\n') if lines else ''
