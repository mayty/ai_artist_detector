import click


@click.group('workers')
def workers_group() -> None:
    """> Workers"""


@workers_group.command('api-dev')
@click.option('--port', '-p', help='Port to run API on', type=click.INT, default=8000, show_default=True)
@click.option('--host', '-h', help='Host to run API on', type=click.STRING, default='0.0.0.0', show_default=True)  # noqa: S104
@click.option(
    '--download-soul-over-ai',
    '-d',
    is_flag=True,
    default=False,
    help='Download Soul Over AI data, even if already exists',
)
def api_dev(port: int, host: str, download_soul_over_ai: bool) -> None:
    """Start API worker in development mode"""
    from os import execv
    from shutil import which

    from loguru import logger

    from ai_artist_detector.constants import UVICORN_LOGGING_CONFIG_PATH
    from ai_artist_detector.containers import core, external

    if download_soul_over_ai or not core.config.sources.soul_over_ai.file_location.exists():
        external.soul_over_ai.save_data()

    logger.warning('RunningInDevMode')

    uvicorn_path = which('uvicorn')

    if not uvicorn_path:
        msg = 'uvicorn is not installed'
        raise FileNotFoundError(msg)

    args = (
        uvicorn_path,
        'ai_artist_detector.api_entry:setup_api',
        '--log-config',
        str(UVICORN_LOGGING_CONFIG_PATH),
        '--reload',
        '--factory',
        '--port',
        str(port),
        '--host',
        host,
    )

    logger.info('StartingDevApi', args=args)
    execv(uvicorn_path, args)  # noqa: S606


@workers_group.command('api')
@click.option('--port', '-p', help='Port to run API on', type=click.INT, default=8000, show_default=True)
@click.option('--host', '-h', help='Host to run API on', type=click.STRING, default='0.0.0.0', show_default=True)  # noqa: S104
@click.option(
    '--download-soul-over-ai',
    '-d',
    is_flag=True,
    default=False,
    help='Download Soul Over AI data, even if already exists',
)
def api(port: int, host: str, download_soul_over_ai: bool) -> None:
    """Start API worker in production mode"""
    from os import execv
    from shutil import which

    from loguru import logger

    from ai_artist_detector.constants import UVICORN_LOGGING_CONFIG_PATH
    from ai_artist_detector.containers import core, external

    if download_soul_over_ai or not core.config.sources.soul_over_ai.file_location.exists():
        external.soul_over_ai.save_data()

    uvicorn_path = which('uvicorn')

    if not uvicorn_path:
        msg = 'uvicorn is not installed'
        raise FileNotFoundError(msg)

    args = (
        uvicorn_path,
        'ai_artist_detector.api_entry:setup_api',
        '--log-config',
        str(UVICORN_LOGGING_CONFIG_PATH),
        '--factory',
        '--port',
        str(port),
        '--host',
        host,
    )

    logger.info('StartingDevApi', args=args)
    execv(uvicorn_path, args)  # noqa: S606
