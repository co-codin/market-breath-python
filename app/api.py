from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .config import ALLOWED_SYMBOLS
from .db import SessionLocal
from .repository import list_bars

router = APIRouter(prefix="/api")


async def get_session():
    async with SessionLocal() as session:
        yield session


@router.get("/data")
async def data(
    symbol: str = Query(default="$S5FD"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(status_code=400, detail="symbol not allowed")
    bars = await list_bars(session, symbol)
    lines = [
        f"{b.symbol},{b.date.isoformat()},{b.open},{b.high},{b.low},{b.close},{b.volume}"
        for b in bars
    ]
    return Response(
        content=("\n".join(lines) + "\n").encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
