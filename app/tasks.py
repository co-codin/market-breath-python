import asyncio
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from .barchart import BarchartClient
from .config import ALLOWED_SYMBOLS, SYNC_INTERVAL_SECONDS
from .db import SessionLocal
from .repository import upsert_bars

log = logging.getLogger("app.sync")


def parse_csv(body: bytes) -> list[dict]:
    rows: dict[tuple[str, date], dict] = {}
    text = body.decode("utf-8", errors="replace")
    for line in text.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 6:
            continue
        sym, d = parts[0], parts[1]
        try:
            year, month, day = d.split("-")
            bar_date = date(int(year), int(month), int(day))
            row = {
                "symbol": sym,
                "date": bar_date,
                "open": Decimal(parts[2]),
                "high": Decimal(parts[3]),
                "low": Decimal(parts[4]),
                "close": Decimal(parts[5]),
                "volume": int(parts[6]) if len(parts) > 6 and parts[6] else 0,
            }
        except (ValueError, InvalidOperation):
            continue
        rows[(sym, bar_date)] = row
    return list(rows.values())


async def sync_symbol(client: BarchartClient, symbol: str) -> int:
    try:
        _status, body = await client.fetch_csv(symbol)
    except Exception as e:
        log.warning("fetch failed %s: %s", symbol, e)
        return 0
    rows = parse_csv(body)
    async with SessionLocal() as session:
        return await upsert_bars(session, rows)


async def sync_all(client: BarchartClient) -> None:
    results = await asyncio.gather(
        *[sync_symbol(client, s) for s in sorted(ALLOWED_SYMBOLS)],
        return_exceptions=True,
    )
    total = sum(r for r in results if isinstance(r, int))
    log.info("synced %d rows across %d symbols", total, len(ALLOWED_SYMBOLS))


async def sync_loop(client: BarchartClient) -> None:
    while True:
        try:
            await sync_all(client)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("sync loop error: %s", e)
        try:
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise
