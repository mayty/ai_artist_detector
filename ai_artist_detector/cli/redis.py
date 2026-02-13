import click


@click.group('redis')
def redis_group() -> None:
    """> Redis commands"""


@redis_group.command('shell')
def redis_shell() -> None:
    """Enter redis shell"""
    from os import execv
    from shutil import which

    from loguru import logger

    from ai_artist_detector.containers import core

    redis_cli_path = which('redis-cli')
    if not redis_cli_path:
        msg = 'redis-cli not installed'
        raise FileNotFoundError(msg)

    redis_config = core.config.redis

    args = (redis_cli_path, '-h', redis_config.host, '-p', str(redis_config.port), '-n', str(redis_config.db))

    logger.info('LaunchingRedisShell', executable=redis_cli_path, args=args)
    execv(redis_cli_path, args)  # noqa: S606
