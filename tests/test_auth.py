import httpx


async def test_register_sets_cookie_and_me_works(client, new_email):
    r = await client.post(
        "/api/auth/register",
        json={"email": new_email(), "password": "password1234"},
    )
    assert r.status_code == 200
    assert "session" in client.cookies

    r = await client.get("/api/auth/me")
    assert r.status_code == 200


async def test_duplicate_register_returns_409(client, new_email):
    email = new_email()
    await client.post("/api/auth/register", json={"email": email, "password": "password1234"})
    async with httpx.AsyncClient(base_url=str(client.base_url), follow_redirects=False) as c2:
        r = await c2.post("/api/auth/register", json={"email": email, "password": "password1234"})
    assert r.status_code == 409


async def test_login_wrong_password_returns_401(registered_user):
    async with httpx.AsyncClient(base_url="http://localhost:8000", follow_redirects=False) as c:
        r = await c.post(
            "/api/auth/login",
            json={"email": registered_user["email"], "password": "wrongwrongwrong"},
        )
    assert r.status_code == 401


async def test_login_right_password_succeeds_and_me_works(registered_user):
    async with httpx.AsyncClient(base_url="http://localhost:8000", follow_redirects=False) as c:
        r = await c.post(
            "/api/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        assert r.status_code == 200
        r = await c.get("/api/auth/me")
        assert r.status_code == 200


async def test_logout_invalidates_session(client, registered_user):
    r = await client.get("/api/auth/me")
    assert r.status_code == 200
    r = await client.post("/api/auth/logout")
    assert r.status_code == 200
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_protected_html_redirects_when_unauth():
    async with httpx.AsyncClient(base_url="http://localhost:8000", follow_redirects=False) as c:
        r = await c.get("/breadth/")
        assert r.status_code == 302
        assert r.headers["location"].endswith("/login/")


async def test_protected_api_returns_401_when_unauth():
    async with httpx.AsyncClient(base_url="http://localhost:8000", follow_redirects=False) as c:
        r = await c.get("/api/data?symbol=$S5FD")
        assert r.status_code == 401


async def test_protected_routes_ok_when_authed(client, registered_user):
    r = await client.get("/breadth/")
    assert r.status_code == 200
    r = await client.get("/api/data?symbol=$S5FD")
    assert r.status_code == 200


async def test_public_landing_is_open():
    async with httpx.AsyncClient(base_url="http://localhost:8000", follow_redirects=False) as c:
        r = await c.get("/")
        assert r.status_code == 200


async def test_login_is_rate_limited(new_email):
    statuses: list[int] = []
    async with httpx.AsyncClient(base_url="http://localhost:8000", follow_redirects=False) as c:
        for _ in range(20):
            r = await c.post(
                "/api/auth/login",
                json={"email": new_email(), "password": "doesntmatter"},
            )
            statuses.append(r.status_code)

    assert set(statuses) <= {401, 429}, statuses
    assert 429 in statuses, statuses
