import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .auth import router as auth_router
from .barchart import BarchartClient
from .config import SESSION_COOKIE
from .db import close_db, init_db
from .repository import close_redis
from .security import get_session
from .tasks import sync_all, sync_loop

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

PROTECTED_HTML_PREFIXES = ("/breadth",)
PROTECTED_API_PATHS = {"/api/data", "/api/events"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    client = BarchartClient()
    app.state.barchart = client
    await sync_all(client)
    task = asyncio.create_task(sync_loop(client))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await client.close()
        await close_redis()
        await close_db()


app = FastAPI(title="Market Breadth", lifespan=lifespan)


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    path = request.url.path
    is_html = any(path == p or path.startswith(p + "/") for p in PROTECTED_HTML_PREFIXES)
    is_api = path in PROTECTED_API_PATHS
    if not (is_html or is_api):
        return await call_next(request)

    sid = request.cookies.get(SESSION_COOKIE)
    user = await get_session(sid) if sid else None
    if user is None:
        if is_api:
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        return RedirectResponse("/login/", status_code=302)
    request.state.user = user
    return await call_next(request)


app.include_router(auth_router)
app.include_router(api_router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
