from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Bar


async def upsert_bars(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(Bar).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Bar.symbol, Bar.date],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def list_bars(session: AsyncSession, symbol: str) -> list[Bar]:
    stmt = select(Bar).where(Bar.symbol == symbol).order_by(Bar.date.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())
