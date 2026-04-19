from datetime import date as _date

_store: dict[str, list[dict]] = {}


def set_bars(symbol: str, rows: list[dict]) -> int:
    _store[symbol] = sorted(rows, key=lambda r: r["date"])
    return len(_store[symbol])


def list_bars(symbol: str) -> list[dict]:
    return _store.get(symbol, [])
