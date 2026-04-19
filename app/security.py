import json
import secrets

import bcrypt

from .config import SESSION_TTL_SECONDS
from .repository import _redis

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_ATTEMPTS = 10


async def check_rate_limit(
    scope: str,
    key: str,
    max_attempts: int = RATE_LIMIT_MAX_ATTEMPTS,
    window: int = RATE_LIMIT_WINDOW_SECONDS,
) -> bool:
    bucket = f"ratelimit:{scope}:{key}"
    count = await _redis().incr(bucket)
    if count == 1:
        await _redis().expire(bucket, window)
    return count <= max_attempts


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
    except ValueError:
        return False


def _session_key(sid: str) -> str:
    return f"session:{sid}"


async def create_session(user_id: int, email: str) -> str:
    sid = secrets.token_urlsafe(32)
    payload = json.dumps({"user_id": user_id, "email": email})
    await _redis().set(_session_key(sid), payload, ex=SESSION_TTL_SECONDS)
    return sid


async def get_session(sid: str) -> dict | None:
    raw = await _redis().get(_session_key(sid))
    if not raw:
        return None
    await _redis().expire(_session_key(sid), SESSION_TTL_SECONDS)
    return json.loads(raw)


async def delete_session(sid: str) -> None:
    await _redis().delete(_session_key(sid))
