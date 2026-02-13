from ai_artist_detector.cli.db import db_group
from ai_artist_detector.cli.iimuzyka import iimuzyka_group
from ai_artist_detector.cli.ingest import ingest_group
from ai_artist_detector.cli.redis import redis_group
from ai_artist_detector.cli.workers import workers_group

__all__ = ('command_groups',)

command_groups = (workers_group, ingest_group, iimuzyka_group, db_group, redis_group)
