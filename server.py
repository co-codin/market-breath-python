import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import os
import threading
import time

BARCHART_HOME = "https://www.barchart.com/"
BARCHART_BASE = "https://www.barchart.com/proxies/timeseries/historical/queryeod.ashx"
ALLOWED_SYMBOLS = {"$S5FD", "$S5TW", "$S5FI", "$S5OH", "$S5TH"}

def _build_url(symbol):
    q = urllib.parse.urlencode({
        "symbol": symbol,
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
    })
    return f"{BARCHART_BASE}?{q}"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
ROOT = os.path.dirname(os.path.abspath(__file__))

_cookie_lock = threading.Lock()
_cookie_state = {"jar": None, "xsrf": None, "primed_at": 0}


def _build_opener():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [
        ("User-Agent", UA),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "en-US,en;q=0.9"),
    ]
    return opener, jar


def _xsrf_from_jar(jar):
    for c in jar:
        if c.name == "XSRF-TOKEN" and c.domain.endswith("barchart.com"):
            return urllib.parse.unquote(c.value)
    return None


def _prime(force=False):
    with _cookie_lock:
        now = time.time()
        if not force and _cookie_state["jar"] and now - _cookie_state["primed_at"] < 600:
            return _cookie_state["jar"], _cookie_state["xsrf"]
        opener, jar = _build_opener()
        opener.open(BARCHART_HOME, timeout=10).read()
        xsrf = _xsrf_from_jar(jar)
        _cookie_state.update(jar=jar, xsrf=xsrf, primed_at=now)
        return jar, xsrf


def _do_fetch(symbol, jar, xsrf):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(
        _build_url(symbol),
        headers={
            "User-Agent": UA,
            "Accept": "text/csv,*/*;q=0.8",
            "Referer": f"https://www.barchart.com/stocks/quotes/{symbol}",
            "X-XSRF-TOKEN": xsrf or "",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    with opener.open(req, timeout=10) as resp:
        return resp.status, resp.read()


def _fetch_csv(symbol):
    jar, xsrf = _prime()
    try:
        return _do_fetch(symbol, jar, xsrf)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            jar, xsrf = _prime(force=True)
            return _do_fetch(symbol, jar, xsrf)
        raise


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/api/data"):
            self.proxy_barchart()
            return
        return super().do_GET()

    def proxy_barchart(self):
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        symbol = (params.get("symbol", ["$S5FD"])[0] or "$S5FD").strip()
        if symbol not in ALLOWED_SYMBOLS:
            self.send_response(400)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"symbol not allowed")
            return
        try:
            status, body = _fetch_csv(symbol)
            self.send_response(status)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(f"Upstream error: {e}".encode())
        except Exception as e:
            self.send_response(502)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(f"Proxy error: {e}".encode())


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    with ThreadedServer((HOST, PORT), Handler) as httpd:
        print(f"Serving on http://{HOST}:{PORT}")
        httpd.serve_forever()
