import click
from loguru import logger

from ai_artist_detector.lib.helpers import async_to_sync


@click.group('ingest')
def ingest_group() -> None:
    """> Data ingestion commands"""


@ingest_group.command('all')
@async_to_sync
async def ingest_soul_over_ai() -> None:
    """Ingest artists data"""
    from ai_artist_detector.containers import services

    logger.info('StartingDataIngestion')
    await services.verdict_controller_service.recalculate()
    logger.info('DataIngestionComplete')
