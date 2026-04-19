from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .db import SessionLocal
from .repository import _redis

router = APIRouter()


@router.get("/healthz")
async def healthz() -> JSONResponse:
    status = {"db": "ok", "redis": "ok"}
    code = 200

    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        status["db"] = f"error: {type(e).__name__}"
        code = 503

    try:
        await _redis().ping()
    except Exception as e:
        status["redis"] = f"error: {type(e).__name__}"
        code = 503

    return JSONResponse(status, status_code=code)
