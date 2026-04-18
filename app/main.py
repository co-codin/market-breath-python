import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .barchart import BarchartClient
from .db import close_db, init_db
from .tasks import sync_loop

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    client = BarchartClient()
    app.state.barchart = client
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
        await close_db()


app = FastAPI(title="Market Breadth", lifespan=lifespan)
app.include_router(api_router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
