import os

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

SYNC_INTERVAL_SECONDS = int(os.environ.get("SYNC_INTERVAL_SECONDS", "3600"))

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

BARCHART_HOME = "https://www.barchart.com/"
BARCHART_QUERY_URL = "https://www.barchart.com/proxies/timeseries/historical/queryeod.ashx"

COOKIE_TTL_SECONDS = 600

QUERY_DEFAULTS = {
    "data": "daily",
    "maxrecords": "640",
    "volume": "contract",
    "order": "asc",
    "dividends": "false",
    "backadjust": "false",
    "daystoexpiration": "1",
    "contractroll": "combined",
    "splits": "true",
    "padded": "false",
}

ALLOWED_SYMBOLS = frozenset({
    "$S5FD", "$S5TW", "$S5FI", "$S5OH", "$S5TH",
    "$NDFD", "$NDTW", "$NDFI", "$NDOH", "$NDTH",
    "$NCFD", "$NCTW", "$NCFI", "$NCOH", "$NCTH",
})
