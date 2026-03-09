from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import threading
import time
from typing import Any

import requests

NONLOGS_MARKETS_URL = "https://api.nonlogs.io/api/markets"
KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
RATE_SOURCE = "nonlogs"
RATE_TTL_SECONDS = 60

_cache_lock = threading.Lock()
_cached_quote: QuoteResult | None = None
_cached_at: float | None = None

_btc_cache_lock = threading.Lock()
_cached_btc_usd: Decimal | None = None
_cached_btc_at: float | None = None
BTC_CACHE_TTL = 30


@dataclass(frozen=True)
class QuoteResult:
    rate: Decimal
    currency: str
    source: str
    quoted_at: datetime


def _get_btc_usd() -> Decimal:
    global _cached_btc_usd, _cached_btc_at
    with _btc_cache_lock:
        if _cached_btc_usd and _cached_btc_at:
            if time.monotonic() - _cached_btc_at < BTC_CACHE_TTL:
                return _cached_btc_usd

    resp = requests.get(KRAKEN_TICKER_URL, params={"pair": "XXBTZUSD"}, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"Kraken API error: {data['error']}")
    price = data["result"]["XXBTZUSD"]["c"][0]
    result = Decimal(str(price))
    with _btc_cache_lock:
        _cached_btc_usd = result
        _cached_btc_at = time.monotonic()
    return result


def get_wow_rate(currency: str) -> QuoteResult:
    global _cached_quote, _cached_at
    normalized_currency = currency.strip().lower()
    if normalized_currency != "usd":
        raise ValueError(f"Unsupported fiat currency: {currency} (supported: usd)")

    with _cache_lock:
        if _cached_quote and _cached_at:
            if time.monotonic() - _cached_at < RATE_TTL_SECONDS:
                return _cached_quote

    headers = {
        "Accept": "application/json",
        "User-Agent": "wowcheckout/1.0",
    }
    resp = requests.get(NONLOGS_MARKETS_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    markets = data.get("markets", {})

    # Use WOW-BTC price converted via Kraken BTC/USD
    wow_btc = markets.get("WOW-BTC", {})
    if not wow_btc.get("last_price"):
        raise ValueError("Could not get WOW-BTC rate from Nonlogs")

    btc_usd = _get_btc_usd()
    rate = Decimal(str(wow_btc["last_price"])) * btc_usd

    quote = QuoteResult(
        rate=rate,
        currency="USD",
        source=RATE_SOURCE,
        quoted_at=datetime.now(timezone.utc),
    )
    with _cache_lock:
        _cached_quote = quote
        _cached_at = time.monotonic()
    return quote
