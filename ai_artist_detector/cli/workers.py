import click


@click.group('workers')
def workers_group() -> None:
    """> Workers"""


@workers_group.command('api-dev')
@click.option('--port', '-p', help='Port to run API on', type=click.INT, default=8000, show_default=True)
@click.option('--host', '-h', help='Host to run API on', type=click.STRING, default='0.0.0.0', show_default=True)  # noqa: S104
def api_dev(port: int, host: str) -> None:
    """Start API worker in development mode"""
    from os import execv
    from shutil import which

    from loguru import logger

    from ai_artist_detector.constants import UVICORN_LOGGING_CONFIG_PATH

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
def api(port: int, host: str) -> None:
    """Start API worker in production mode"""
    from os import execv
    from shutil import which

    from loguru import logger

    from ai_artist_detector.constants import UVICORN_LOGGING_CONFIG_PATH

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
