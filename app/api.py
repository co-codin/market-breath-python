import asyncio
import time
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from .config import ALLOWED_SYMBOLS
from .events import events
from .repository import list_bars

router = APIRouter(prefix="/api")

KEEPALIVE_SECONDS = 30


@router.get("/data")
async def data(symbol: str = Query(default="$S5FD")) -> Response:
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(status_code=400, detail="symbol not allowed")
    bars = await list_bars(symbol)
    lines = [
        f"{b['symbol']},{b['date'].isoformat()},{b['open']},{b['high']},{b['low']},{b['close']},{b['volume']}"
        for b in bars
    ]
    return Response(
        content=("\n".join(lines) + "\n").encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/events")
async def events_stream() -> StreamingResponse:
    queue = events.subscribe()

    async def gen() -> AsyncIterator[bytes]:
        try:
            yield b"retry: 5000\n\n"
            yield b": hello\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                    yield f"event: {msg}\ndata: {int(time.time())}\n\n".encode()
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
        finally:
            events.unsubscribe(queue)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
