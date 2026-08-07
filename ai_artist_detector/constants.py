from enum import auto, StrEnum
from os import environ
from pathlib import Path

LOG_LEVEL = environ.get('LOG_LEVEL', default='INFO')
if LOG_LEVEL not in {'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'}:
    msg = f'Invalid LOG_LEVEL: {LOG_LEVEL}'
    raise ValueError(msg)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
UVICORN_LOGGING_CONFIG_PATH = Path(
    environ.get('UVICORN_LOGGING_CONFIG_PATH', default='/app/config/uvicorn_logging.ini')
)
CONFIG_PATH = Path(environ.get('CONFIG_PATH', default='/app/config/config.yaml'))
CONFIG_OVERRIDE_PATH = CONFIG_PATH.parent / 'local.overrides.yaml'


class ArtistStatuses(StrEnum):
    AI = auto()
    HUMAN = auto()
    UNKNOWN = auto()


class DataSources(StrEnum):
    SOUL_OVER_AI = auto()
    IIMUZYKA_TOP = auto()
    EXPLICIT = auto()


class QueryUpdatePolicies(StrEnum):
    IGNORE = auto()
    UPDATE_EMPTY = auto()
    UPDATE_ALL = auto()


class RedisNamespaces(StrEnum):
    VERDICTS = auto()
    METRICS = auto()


class EndpointLabels(StrEnum):
    CHECK = auto()
    BATCH = auto()


class MetricName(StrEnum):
    HTTP_REQUESTS_TOTAL = auto()
    HTTP_REQUEST_DURATION_SECONDS = auto()
    ARTIST_IDS_REQUESTED_TOTAL = auto()
    ARTIST_IDS_CHECKED_AI_TOTAL = auto()
    REDIS_UP = auto()
    AI_ARTISTS_IN_DB = auto()
    INGESTION_RUN_DURATION_SECONDS = auto()
    INGESTION_LAST_RUN_TIMESTAMP_SECONDS = auto()
    INGESTION_ARTISTS_CACHED = auto()
    INGESTION_ARTISTS_NEW = auto()
    INGESTION_ARTIST_IDS_ADDED = auto()
    INGESTION_UNMATCHED_COUNT = auto()
