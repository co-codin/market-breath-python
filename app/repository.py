import json
from datetime import date as _date

from redis.asyncio import Redis

from .config import REDIS_URL, SYNC_INTERVAL_SECONDS

_client: Redis | None = None


def _redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(REDIS_URL, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _key(symbol: str) -> str:
    return f"bars:{symbol}"


async def set_bars(symbol: str, rows: list[dict]) -> int:
    rows = sorted(rows, key=lambda r: r["date"])
    payload = json.dumps(
        [{**r, "date": r["date"].isoformat()} for r in rows],
        separators=(",", ":"),
    )
    await _redis().set(_key(symbol), payload, ex=SYNC_INTERVAL_SECONDS * 2)
    return len(rows)


async def list_bars(symbol: str) -> list[dict]:
    raw = await _redis().get(_key(symbol))
    if not raw:
        return []
    rows = json.loads(raw)
    for r in rows:
        r["date"] = _date.fromisoformat(r["date"])
    return rows
