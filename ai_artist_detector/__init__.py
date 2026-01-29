import logging
from sys import stderr

from loguru import logger

from ai_artist_detector.lib.logging import InterceptHandler


def configure_logging() -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level='INFO', force=True)
    log_format = ' | '.join(  # noqa: FLY002
        (
            '[<lvl>{level:8}</>][<dim>{time:YYYY-MM-DD HH:mm:ss.SSSZ}</>]',
            '{name}:{function}:{line}',
            '<lvl>{message}</>',
            '{extra}',
        )
    )
    logger.remove()
    logger.level('DEBUG', color='<dim>')
    logger.level('INFO', color='<blue>')
    logger.level('SUCCESS', color='<green><bold>')
    logger.level('WARNING', color='<yellow>')
    logger.level('ERROR', color='<red>')
    logger.level('CRITICAL', color='<red><bold>')
    logger.add(stderr, format=log_format, level='DEBUG')


configure_logging()
