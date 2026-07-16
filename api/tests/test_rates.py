import time
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import requests

from app import rates


def response(payload):
    result = Mock()
    result.raise_for_status.return_value = None
    result.json.return_value = payload
    return result


class WowneroRateTests(unittest.TestCase):
    def setUp(self):
        rates._cached_quote = None
        rates._cached_at = None
        rates._cached_btc_usd = None
        rates._cached_btc_at = None
        rates.RATE_PROVIDER = "nonlogs"

    @patch("app.rates.requests.get")
    def test_uses_nonlogs_and_kraken_as_primary_quote(self, get):
        get.side_effect = [
            response({"markets": {"WOW-BTC": {"last_price": "0.000001"}}}),
            response({"error": [], "result": {"XXBTZUSD": {"c": ["60000"]}}}),
        ]

        quote = rates.get_wow_rate("USD")

        self.assertEqual(quote.rate, Decimal("0.060000"))
        self.assertEqual(quote.source, "nonlogs+kraken")

    @patch("app.rates.requests.get")
    def test_falls_back_to_a_traded_cexswap_market(self, get):
        get.side_effect = [
            requests.ConnectionError("nonlogs unavailable"),
            response(
                {
                    "items": [
                        {
                            "pair": "WOW-XMR",
                            "last": "0.00002",
                            "volume24h_usd": "10",
                        }
                    ]
                }
            ),
            response({"error": [], "result": {"XXMRZUSD": {"c": ["300"]}}}),
        ]

        quote = rates.get_wow_rate("usd")

        self.assertEqual(quote.rate, Decimal("0.00600"))
        self.assertEqual(quote.source, "cexswap+kraken")

    @patch("app.rates.requests.get")
    def test_rejects_quotes_below_the_wownero_safety_floor(self, get):
        get.side_effect = [
            response({"markets": {"WOW-BTC": {"last_price": "0.000000001"}}}),
            response({"error": [], "result": {"XXBTZUSD": {"c": ["100"]}}}),
            response(
                {
                    "items": [
                        {
                            "pair": "WOW-XMR",
                            "last": "0.000001",
                            "volume24h_usd": "10",
                        }
                    ]
                }
            ),
            response({"error": [], "result": {"XXMRZUSD": {"c": ["100"]}}}),
        ]

        with self.assertRaisesRegex(RuntimeError, "rate providers unavailable"):
            rates.get_wow_rate("usd")

    @patch("app.rates.requests.get", side_effect=requests.ConnectionError("offline"))
    def test_marks_a_bounded_last_known_good_quote_as_stale(self, _get):
        rates._cached_quote = rates.QuoteResult(
            rate=Decimal("0.04"),
            currency="USD",
            source="cexswap+kraken",
            quoted_at=datetime.now(timezone.utc),
        )
        rates._cached_at = time.monotonic() - rates.RATE_TTL_SECONDS - 1

        quote = rates.get_wow_rate("usd")

        self.assertEqual(quote.rate, Decimal("0.04"))
        self.assertEqual(quote.source, "cexswap+kraken:stale")

    @patch("app.rates.requests.get", side_effect=requests.ConnectionError("offline"))
    def test_fails_closed_when_the_cached_quote_is_too_old(self, _get):
        rates._cached_quote = rates.QuoteResult(
            rate=Decimal("0.04"),
            currency="USD",
            source="cexswap+kraken",
            quoted_at=datetime.now(timezone.utc),
        )
        rates._cached_at = time.monotonic() - rates.RATE_STALE_TTL_SECONDS - 1

        with self.assertRaisesRegex(RuntimeError, "rate providers unavailable"):
            rates.get_wow_rate("usd")

    @patch("app.rates.requests.get", side_effect=requests.ConnectionError("offline"))
    def test_rejects_a_stale_quote_below_the_safety_floor(self, _get):
        rates._cached_quote = rates.QuoteResult(
            rate=Decimal("0.0009"),
            currency="USD",
            source="cexswap+kraken",
            quoted_at=datetime.now(timezone.utc),
        )
        rates._cached_at = time.monotonic() - rates.RATE_TTL_SECONDS - 1

        with self.assertRaisesRegex(RuntimeError, "rate providers unavailable"):
            rates.get_wow_rate("usd")


if __name__ == "__main__":
    unittest.main()
