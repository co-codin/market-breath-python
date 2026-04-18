import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from .barchart import BarchartClient
from .config import ALLOWED_SYMBOLS

router = APIRouter(prefix="/api")


def get_barchart(request: Request) -> BarchartClient:
    return request.app.state.barchart


@router.get("/data")
async def data(
    symbol: str = Query(default="$S5FD"),
    client: BarchartClient = Depends(get_barchart),
) -> Response:
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(status_code=400, detail="symbol not allowed")
    try:
        status, body = await client.fetch_csv(symbol)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"upstream error: {e}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"proxy error: {e}")
    return Response(
        content=body,
        status_code=status,
        media_type="text/csv; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
