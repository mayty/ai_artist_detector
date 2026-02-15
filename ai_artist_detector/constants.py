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


class RedisNamespaces(StrEnum):
    VERDICTS = auto()
