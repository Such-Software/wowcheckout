from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import logging
import os
import threading
import time
from typing import Any

import requests

NONLOGS_MARKETS_URL = "https://api.nonlogs.io/api/markets"
KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
CEXSWAP_MARKETS_URL = "https://cexswap.cc/api/public/markets/summary"
# Canonical Such Software price oracle (hash-wallet-prices Worker): Nonlogs +
# volume-weighted CexSwap, averaged. Replaces the ad-hoc neroswap-wow-prices
# Worker, which froze on 2026-07-28 and has served price_usd=null since.
UNIFIED_WOW_URL = os.getenv(
    "UNIFIED_WOW_URL", "https://prices.neroswap.com/v2/rates?base=WOW&quote=USD"
)
# Default to the unified feed; RATE_PROVIDER=nonlogs|cexswap forces a legacy
# single source first (debugging).
RATE_PROVIDER = os.getenv("RATE_PROVIDER", "unified").strip().lower()
RATE_TTL_SECONDS = 60
RATE_STALE_TTL_SECONDS = max(0, int(os.getenv("RATE_STALE_TTL_SECONDS", "300")))
MIN_WOW_USD_RATE = Decimal("0.001")
CEXSWAP_MIN_VOLUME_USD = Decimal("1")

logger = logging.getLogger(__name__)

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


def _get_nonlogs_usd() -> Decimal:
    headers = {
        "Accept": "application/json",
        "User-Agent": "wowcheckout/1.0",
    }
    resp = requests.get(NONLOGS_MARKETS_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    markets = data.get("markets", {})
    wow_btc = markets.get("WOW-BTC", {}) if isinstance(markets, dict) else {}
    if not wow_btc.get("last_price"):
        raise ValueError("Could not get WOW-BTC rate from Nonlogs")
    return Decimal(str(wow_btc["last_price"])) * _get_btc_usd()


def _get_xmr_usd() -> Decimal:
    resp = requests.get(KRAKEN_TICKER_URL, params={"pair": "XXMRZUSD"}, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"Kraken API error: {data['error']}")
    return Decimal(str(data["result"]["XXMRZUSD"]["c"][0]))


def _get_cexswap_usd() -> Decimal:
    headers = {
        "Accept": "application/json",
        "User-Agent": "wowcheckout/1.0",
    }
    resp = requests.get(CEXSWAP_MARKETS_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    markets = data.get("items", []) if isinstance(data, dict) else data
    market = next(
        (
            item
            for item in markets
            if isinstance(item, dict) and str(item.get("pair", "")).upper() == "WOW-XMR"
        ),
        None,
    )
    if not market:
        raise ValueError("CexSwap did not return the WOW-XMR market")
    volume_usd = Decimal(str(market.get("volume24h_usd", "0")))
    if volume_usd < CEXSWAP_MIN_VOLUME_USD:
        raise ValueError("CexSwap WOW-XMR market has insufficient 24-hour volume")
    wow_xmr = Decimal(str(market.get("last", "0")))
    return wow_xmr * _get_xmr_usd()


def _get_unified_usd() -> Decimal:
    """WOW-USD from the canonical oracle at prices.neroswap.com — Nonlogs plus
    volume-weighted CexSwap, averaged, KV-cached each minute (the primary
    provider). Accepts the legacy neroswap-wow-prices shape too so the
    UNIFIED_WOW_URL env override keeps working either way."""
    headers = {"Accept": "application/json", "User-Agent": "wowcheckout/1.0"}
    resp = requests.get(UNIFIED_WOW_URL, headers=headers, timeout=6)
    resp.raise_for_status()
    data = resp.json()
    price = data.get("results", {}).get("WOW_USD") if isinstance(data.get("results"), dict) else None
    if price is None:
        price = data.get("price_usd")
    if price is None or Decimal(str(price)) <= 0:
        # null / zero = oracle has nothing; fall through to the direct providers.
        raise ValueError("unified price API returned no WOW-USD price")
    return Decimal(str(price))


def _providers() -> list[tuple[str, Callable[[], Decimal]]]:
    unified = ("unified", _get_unified_usd)
    nonlogs = ("nonlogs+kraken", _get_nonlogs_usd)
    cexswap = ("cexswap+kraken", _get_cexswap_usd)
    # Unified first, with the direct single-source paths as fallbacks. An
    # operator can force a legacy source first for debugging via RATE_PROVIDER.
    if RATE_PROVIDER == "nonlogs":
        return [nonlogs, cexswap, unified]
    if RATE_PROVIDER == "cexswap":
        return [cexswap, nonlogs, unified]
    return [unified, nonlogs, cexswap]


def get_wow_rate(currency: str) -> QuoteResult:
    global _cached_quote, _cached_at
    normalized_currency = currency.strip().lower()
    if normalized_currency != "usd":
        raise ValueError(f"Unsupported fiat currency: {currency} (supported: usd)")

    with _cache_lock:
        if _cached_quote and _cached_at:
            if (
                time.monotonic() - _cached_at < RATE_TTL_SECONDS
                and _cached_quote.rate >= MIN_WOW_USD_RATE
            ):
                return _cached_quote

    for source, provider in _providers():
        try:
            rate = provider()
            if rate < MIN_WOW_USD_RATE:
                raise ValueError(
                    f"{source} returned Wownero below the ${MIN_WOW_USD_RATE} safety floor"
                )
            quote = QuoteResult(
                rate=rate,
                currency="USD",
                source=source,
                quoted_at=datetime.now(timezone.utc),
            )
            with _cache_lock:
                _cached_quote = quote
                _cached_at = time.monotonic()
            return quote
        except (KeyError, TypeError, ValueError, RuntimeError, requests.RequestException) as error:
            logger.warning("Wownero rate provider %s failed: %s", source, error)

    with _cache_lock:
        if _cached_quote and _cached_at and RATE_STALE_TTL_SECONDS > 0:
            if (
                time.monotonic() - _cached_at < RATE_STALE_TTL_SECONDS
                and _cached_quote.rate >= MIN_WOW_USD_RATE
            ):
                return QuoteResult(
                    rate=_cached_quote.rate,
                    currency=_cached_quote.currency,
                    source=f"{_cached_quote.source}:stale",
                    quoted_at=_cached_quote.quoted_at,
                )

    raise RuntimeError("Wownero rate providers unavailable")
