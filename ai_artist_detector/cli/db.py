import click


@click.group('db')
def db_group() -> None:
    """> Database commands"""


@db_group.command('shell')
def db_shell() -> None:
    """Enter sqlite shell"""
    from os import execv
    from shutil import which

    from loguru import logger

    from ai_artist_detector.containers import core

    sqlite_path = which('sqlite3')
    if not sqlite_path:
        msg = 'sqlite3 not installed'
        raise FileNotFoundError(msg)

    args = (sqlite_path, '-box', str(core.config.sqlite.file_location.resolve()))

    logger.info('LaunchingSqliteShell', executable=sqlite_path, args=args)
    execv(sqlite_path, args)  # noqa: S606
