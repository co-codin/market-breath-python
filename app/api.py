from fastapi import APIRouter, HTTPException, Query, Response

from .config import ALLOWED_SYMBOLS
from .repository import list_bars

router = APIRouter(prefix="/api")


@router.get("/data")
async def data(symbol: str = Query(default="$S5FD")) -> Response:
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(status_code=400, detail="symbol not allowed")
    bars = list_bars(symbol)
    lines = [
        f"{b['symbol']},{b['date'].isoformat()},{b['open']},{b['high']},{b['low']},{b['close']},{b['volume']}"
        for b in bars
    ]
    return Response(
        content=("\n".join(lines) + "\n").encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
