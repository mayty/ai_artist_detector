from ai_artist_detector.cli.ingest import ingest_group
from ai_artist_detector.cli.workers import workers_group

__all__ = ('command_groups',)

command_groups = (workers_group, ingest_group)
