# This file has been edited with the assistance of an AI tool.
from loguru import logger


class ExplicitService:
    def __init__(
        self,
        artist_ids: set[str],
    ) -> None:
        self.artist_ids = artist_ids

        self.artists_count = 0
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

    def get_ai_artists(self) -> set[str]:
        artist_ids = set(self.artist_ids)

        self.artists_count = len(self.artist_ids)
        self.unresolved_handles_count = 0
        self.not_matched_count = 0

        logger.info(
            'RetrievalStats',
            artists_count=len(self.artist_ids),
            ytm_ids_count=len(artist_ids),
            unresolved_handles_count=self.unresolved_handles_count,
            not_matched_count=self.not_matched_count,
        )

        return artist_ids
