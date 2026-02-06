from datetime import datetime, UTC
from enum import auto, StrEnum
from typing import TYPE_CHECKING

from ai_artist_detector.constants import RedisNamespaces

if TYPE_CHECKING:
    from redis.asyncio import Redis


class VerdictKeys(StrEnum):
    HUMANS = auto()
    AI = auto()


class VerdictsRepository:
    namespace = RedisNamespaces.VERDICTS

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def _set(self, key: VerdictKeys, ids: set[str]) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            await (
                pipe.delete(f'{self.namespace}:{key}')
                .sadd(f'{self.namespace}:{key}', *(id_.encode('utf-8') for id_ in ids))
                .set(f'{self.namespace}:{key}_updated_at', datetime.now(tz=UTC).isoformat())
                .execute()
            )

    async def _get(self, key: VerdictKeys) -> set[str]:
        return {id_.decode('utf-8') for id_ in await self.redis.smembers(f'{self.namespace}:{key}')}

    async def _get_updated_at(self, key: VerdictKeys) -> datetime | None:
        updated_at = await self.redis.get(f'{self.namespace}:{key}_updated_at')
        return datetime.fromisoformat(updated_at.decode('utf-8')) if updated_at else None

    async def set_humans(self, human_ids: set[str]) -> None:
        await self._set(VerdictKeys.HUMANS, human_ids)

    async def get_humans(self) -> set[str]:
        return await self._get(VerdictKeys.HUMANS)

    async def get_humans_updated_at(self) -> datetime | None:
        return await self._get_updated_at(VerdictKeys.HUMANS)

    async def set_ai(self, ai_ids: set[str]) -> None:
        await self._set(VerdictKeys.AI, ai_ids)

    async def get_ai(self) -> set[str]:
        return await self._get(VerdictKeys.AI)

    async def get_ai_updated_at(self) -> datetime | None:
        return await self._get_updated_at(VerdictKeys.AI)
