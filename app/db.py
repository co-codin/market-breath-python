import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _run_alembic_upgrade() -> None:
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")


async def init_db() -> None:
    await asyncio.to_thread(_run_alembic_upgrade)


async def close_db() -> None:
    await engine.dispose()
