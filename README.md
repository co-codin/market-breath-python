# Market Breadth — Live Candles

A small FastAPI service that proxies Barchart's historical-EOD endpoint and
serves a dashboard of live daily candlestick charts for market-breadth
indicators across the S&P 500, Nasdaq 100, and NYSE Composite.

The frontend polls the proxy every 5 seconds and renders a **3 × 5 grid of
independent candlestick charts** — one per symbol — using
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
docker compose up -d          # build + start on http://localhost:8000
docker compose down           # stop
```

Locally (requires Python 3.12+):

```bash
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

### Persistence

Historical bars are stored in Postgres. On startup:

1. `init_db` creates the `bars` table if missing (no migrations).
2. A background task (`app/tasks.py`) fetches every symbol in
   `ALLOWED_SYMBOLS` on a `SYNC_INTERVAL_SECONDS` interval (default **300 s**)
   and upserts them with `INSERT ... ON CONFLICT (symbol, date) DO UPDATE`.

The frontend calls `/api/data?symbol=$S5FD` every 5 s per cell; that endpoint
now reads from the DB rather than proxying live — so client polls never hit
Barchart, and the rate at which we touch Barchart is a fixed 15 requests every
5 minutes no matter how many viewers are connected.

Schema:

```sql
CREATE TABLE bars (
  symbol  VARCHAR(16)  NOT NULL,
  date    DATE         NOT NULL,
  open    NUMERIC(12,4),
  high    NUMERIC(12,4),
  low     NUMERIC(12,4),
  close   NUMERIC(12,4),
  volume  BIGINT DEFAULT 0,
  PRIMARY KEY (symbol, date)
);
```

## Project layout

```
app/
  __init__.py
  __main__.py        # `python -m app` → uvicorn entry
  config.py          # env, allow-listed symbols, query defaults
  barchart.py        # async cookie-primed httpx client (BarchartClient)
  db.py              # async SQLAlchemy engine + DeclarativeBase + init_db
  models.py          # Bar(symbol PK, date PK, open/high/low/close/volume)
  repository.py      # upsert_bars (ON CONFLICT), list_bars
  tasks.py           # background sync_loop → upsert all symbols every N sec
  api.py             # FastAPI router: GET /api/data?symbol=... (reads DB)
  main.py            # FastAPI app + lifespan + static mount at /
static/
  index.html         # lightweight-charts grid UI (no build step)
compose.yaml         # postgres:16-alpine + app container, wired via DATABASE_URL
Dockerfile
Makefile
requirements.txt
```

## API

### `GET /api/data?symbol=<SYMBOL>`

- `symbol` — must be one of the 15 symbols above. Unknown symbols return `400`.
- Response body: raw CSV from Barchart in the form
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
  http://localhost:8000/
```

Name convention used in this README:

- `docs/screenshots/overview.png` — full 3 × 5 grid
- `docs/screenshots/cell.png` — one cell close-up

## Configuration

| Env var                 | Default                                                          | Notes                                           |
|-------------------------|------------------------------------------------------------------|-------------------------------------------------|
| `HOST`                  | `127.0.0.1`                                                      | Set to `0.0.0.0` inside Docker                  |
| `PORT`                  | `8000`                                                           |                                                 |
| `DATABASE_URL`          | `postgresql+asyncpg://barchart:barchart@localhost:5432/barchart` | Compose overrides host to `db`                  |
| `SYNC_INTERVAL_SECONDS` | `300`                                                            | How often the background task hits Barchart     |

The symbol allow-list lives in `app/config.py:ALLOWED_SYMBOLS`. Add new
symbols there to expose them through `/api/data`.
