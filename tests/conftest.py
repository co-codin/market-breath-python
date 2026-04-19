import os
import uuid

import httpx
import pytest
from redis.asyncio import Redis

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(autouse=True)
async def _reset_rate_limits():
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis.delete("ratelimit:login:127.0.0.1", "ratelimit:register:127.0.0.1")
        yield
    finally:
        await redis.aclose()


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=False) as c:
        yield c


@pytest.fixture
def new_email():
    def _make() -> str:
        return f"test-{uuid.uuid4().hex[:12]}@example.com"

    return _make


@pytest.fixture
async def registered_user(client, new_email):
    email = new_email()
    password = "password1234"
    r = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"email": email, "password": password, "cookies": dict(client.cookies)}
