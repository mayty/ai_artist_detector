from enum import auto, StrEnum
from os import environ
from pathlib import Path

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
