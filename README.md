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

The frontend calls `/api/data?symbol=$S5FD` (etc.) every 5 s for each of the 15
symbols in parallel. Each response is parsed as CSV and pushed into its own
`addCandlestickSeries`. Each cell owns its own chart instance so panning/zoom
are independent.

## Project layout

```
app/
  __init__.py
  __main__.py        # `python -m app` → uvicorn entry
  config.py          # HOST/PORT, USER_AGENT, allow-listed symbols, query defaults
  barchart.py        # async cookie-primed httpx client (BarchartClient)
  api.py             # FastAPI router: GET /api/data?symbol=...
  main.py            # FastAPI app + lifespan + static mount at /
static/
  index.html         # lightweight-charts grid UI (no build step)
compose.yaml
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

| Env var | Default     | Notes                          |
|---------|-------------|--------------------------------|
| `HOST`  | `127.0.0.1` | Set to `0.0.0.0` inside Docker |
| `PORT`  | `8000`      |                                |

The symbol allow-list lives in `app/config.py:ALLOWED_SYMBOLS`. Add new
symbols there to expose them through `/api/data`.
