import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import SESSION_COOKIE, SESSION_TTL_SECONDS
from .db import SessionLocal
from .models import User
from .security import (
    check_rate_limit,
    create_session,
    delete_session,
    get_session,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth")


async def get_db():
    async with SessionLocal() as session:
        yield session


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v


def _set_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=sid,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register")
async def register(
    body: Credentials,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not await check_rate_limit("register", _client_ip(request)):
        raise HTTPException(status_code=429, detail="too many attempts, try again later")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="email already registered")
    await db.refresh(user)
    sid = await create_session(user.id, user.email)
    _set_cookie(response, sid)
    return {"email": user.email}


@router.post("/login")
async def login(
    body: Credentials,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not await check_rate_limit("login", _client_ip(request)):
        raise HTTPException(status_code=429, detail="too many attempts, try again later")
    row = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if row is None or not verify_password(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    sid = await create_session(row.id, row.email)
    _set_cookie(response, sid)
    return {"email": row.email}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        await delete_session(sid)
    _clear_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(request: Request) -> dict:
    sid = request.cookies.get(SESSION_COOKIE)
    data = await get_session(sid) if sid else None
    if not data:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"email": data["email"]}
