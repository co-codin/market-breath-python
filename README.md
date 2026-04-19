# Market Breadth — Live Candles

A small FastAPI service that proxies Barchart's historical-EOD endpoint and
serves a dashboard of daily candlestick charts for market-breadth indicators
across the S&P 500, Nasdaq 100, and NYSE Composite.

The frontend polls the proxy every 5 seconds and renders a labeled **index × MA-period
matrix of candlestick charts** — one per symbol — using
[`lightweight-charts`](https://www.tradingview.com/lightweight-charts/).

![Overview](docs/screenshots/overview.png)

## Symbols

Rows are indexes, columns are the lookback period for "% stocks above the
N-day moving average":

|            | 5-day   | 20-day  | 50-day  | 100-day | 200-day |
|------------|---------|---------|---------|---------|---------|
| S&P 500    | `$S5FD` | `$S5TW` | `$S5FI` | `$S5OH` | `$S5TH` |
| Nasdaq 100 | `$NDFD` | `$NDTW` | `$NDFI` | `$NDOH` | `$NDTH` |
| NYSE       | `$NCFD` | `$NCTW` | `$NCFI` | `$NCOH` | `$NCTH` |

![Cell detail](docs/screenshots/cell.png)

## Run it

With Docker Compose (recommended):

```bash
docker compose up -d          # build + start app and redis on http://localhost:8000
docker compose down           # stop
```

Locally (requires Python 3.12+ and a reachable Redis):

```bash
make redis-up                 # start just the redis container on localhost:6379
make install                  # pip install -r requirements.txt
make run                      # uvicorn with --reload on 127.0.0.1:8000
```

All `make` targets:

```bash
make help
```

## How it works

Barchart's `queryeod.ashx` endpoint is a session-gated AJAX endpoint. A direct
browser fetch fails with **401 Unauthorized** because the request needs both a
session cookie and a matching `X-XSRF-TOKEN` header. The FastAPI proxy
(`app/barchart.py`) primes an anonymous session once per process:

1. `GET https://www.barchart.com/` to receive the `XSRF-TOKEN` cookie.
2. Extract and URL-decode the token.
3. Every subsequent `queryeod.ashx` call is made with the cookie jar **and**
   an `X-XSRF-TOKEN` header set to the decoded token.
4. The session is re-primed every 10 minutes, or on the next `401/403`.

### Cache

Bars are cached in **Redis** as a single JSON blob per symbol
(`bars:$S5FD`, etc.) with a TTL of `2 × SYNC_INTERVAL_SECONDS`. On startup a
background task (`app/tasks.py`) fetches every symbol in `ALLOWED_SYMBOLS` on
a `SYNC_INTERVAL_SECONDS` interval (default **3600 s**) and `SET`s the payload
with the refresh TTL.

The frontend calls `/api/data?symbol=$S5FD` per cell; that endpoint reads
straight from Redis — so client polls never hit Barchart, and the rate at
which we touch Barchart is a fixed 15 requests per hour no matter how many
viewers are connected. The client is notified of fresh data via an SSE stream
at `/api/events`.

### Auth

- User accounts live in Postgres (`users` table: `id`, `email`, `password_hash`,
  `created_at`). Passwords are hashed with bcrypt.
- Sessions are opaque IDs stored in Redis (`session:<sid>` → `{user_id, email}`)
  with a sliding TTL (default 7 days). The cookie is `session`, `httpOnly`,
  `SameSite=Lax`.
- A middleware in `app/main.py` gates `/breadth/*` (redirects to `/login/`) and
  `/api/data` + `/api/events` (401). The landing page `/` is public; `/login/`
  and `/register/` are static pages that POST to `/api/auth/{login,register}`.

## Project layout

```
app/
  __init__.py
  __main__.py        # `python -m app` → uvicorn entry
  config.py          # env, allow-listed symbols, query defaults, session/DB urls
  barchart.py        # async cookie-primed httpx client (BarchartClient)
  db.py              # async SQLAlchemy engine + DeclarativeBase + init_db
  models.py          # User(id, email, password_hash, created_at)
  repository.py      # redis-backed set_bars / list_bars
  security.py        # bcrypt hash/verify + redis-backed session helpers
  auth.py            # /api/auth/{register,login,logout,me}
  tasks.py           # background sync_loop → cache all symbols every N sec
  api.py             # FastAPI router: GET /api/data + SSE at /api/events
  events.py          # in-process pub/sub for sync notifications
  main.py            # FastAPI app + lifespan + auth middleware + static mount
static/
  index.html         # public landing page with cards for each dashboard
  login/index.html   # sign-in form
  register/index.html# sign-up form
  breadth/
    index.html       # lightweight-charts matrix UI (auth required)
compose.yaml         # postgres + redis + app, wired via DATABASE_URL/REDIS_URL
Dockerfile
Makefile
requirements.txt
```

## API

### `GET /api/data?symbol=<SYMBOL>`

- `symbol` — must be one of the 15 symbols above. Unknown symbols return `400`.
- Response body: CSV lines of the form
  `symbol,YYYY-MM-DD,open,high,low,close,volume`.
- Response media type: `text/csv; charset=utf-8`.
- `Cache-Control: no-store` is always set.

Example:

```bash
curl -sS 'http://localhost:8000/api/data?symbol=$S5FD' | tail -3
```

## Capturing screenshots

Replace the placeholders in `docs/screenshots/` with real captures once the
service is running:

```bash
docker compose up -d
# wait ~5s for the first tick
google-chrome --headless --disable-gpu --hide-scrollbars \
  --window-size=1600,900 --screenshot=docs/screenshots/overview.png \
  http://localhost:8000/breadth/
```

Name convention used in this README:

- `docs/screenshots/overview.png` — full matrix
- `docs/screenshots/cell.png` — one cell close-up

## Configuration

| Env var                 | Default                    | Notes                                           |
|-------------------------|----------------------------|-------------------------------------------------|
| `HOST`                  | `127.0.0.1`                | Set to `0.0.0.0` inside Docker                  |
| `PORT`                  | `8000`                     |                                                 |
| `REDIS_URL`             | `redis://localhost:6379/0` | Compose overrides host to `redis`               |
| `DATABASE_URL`          | `postgresql+asyncpg://barchart:barchart@localhost:5432/barchart` | Compose overrides host to `db`                  |
| `SESSION_TTL_SECONDS`   | `604800` (7 days)          | Session cookie + Redis TTL; sliding on each hit |
| `SYNC_INTERVAL_SECONDS` | `3600`                     | How often the background task hits Barchart     |

The symbol allow-list lives in `app/config.py:ALLOWED_SYMBOLS`. Add new
symbols there to expose them through `/api/data`.
