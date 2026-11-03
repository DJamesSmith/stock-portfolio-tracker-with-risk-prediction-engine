import tempfile
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from accounts.utils import create_access_token
from core.throttles import MarketRefreshThrottle
from .models import PriceHistory
from .selectors import latest_prices
from .tasks import fetch_daily_prices, refresh_single_ticker

TEST_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "test-default"},
    "token_blacklist": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "test-blacklist"},
}

AAPL_CSV = """Date,Open,High,Low,Close,Volume
2025-01-02,100.0,105.0,99.0,104.0,5000000000
2025-01-03,104.0,108.0,103.0,107.5,4000000
not-a-date,1,1,1,1,1
2025-01-06,abc,110.0,106.0,109.0,3000000
2025-01-07,-5,110.0,106.0,109.0,3000000
"""

MSFT_CSV = """Date,Open,High,Low,Close
2025-01-02,400.0,405.0,399.0,404.0
"""


def make_price(ticker, day, close):
    return PriceHistory.objects.create(
        ticker=ticker,
        date=day,
        open_price=close,
        high_price=close,
        low_price=close,
        close_price=close,
        volume=1000,
    )


def provider_frame(rows):
    return pd.DataFrame(rows, columns=["date", "open_price", "high_price", "low_price", "close_price", "volume"])


@override_settings(CACHES=TEST_CACHES)
class LoaderTests(TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        Path(self.folder.name, "AAPL.csv").write_text(AAPL_CSV)
        Path(self.folder.name, "MSFT.csv").write_text(MSFT_CSV)

    def tearDown(self):
        self.folder.cleanup()

    def run_loader(self, *args):
        call_command("load_price_history", self.folder.name, *args, stdout=StringIO())

    def test_loader_skips_bad_rows_and_keeps_big_volume(self):
        self.run_loader("--tickers", "AAPL")
        self.assertEqual(PriceHistory.objects.filter(ticker="AAPL").count(), 2)
        self.assertEqual(PriceHistory.objects.filter(ticker="MSFT").count(), 0)
        first_row = PriceHistory.objects.get(ticker="AAPL", date=date(2025, 1, 2))
        self.assertEqual(first_row.volume, 5000000000)

    def test_loader_can_run_twice_without_duplicates(self):
        self.run_loader()
        self.run_loader()
        self.assertEqual(PriceHistory.objects.count(), 3)

    def test_missing_volume_column_is_saved_as_empty(self):
        self.run_loader("--tickers", "MSFT")
        self.assertIsNone(PriceHistory.objects.get(ticker="MSFT").volume)


@override_settings(CACHES=TEST_CACHES)
class ModelAndSelectorTests(TestCase):
    def test_ticker_and_date_must_be_unique(self):
        make_price("AAPL", date(2025, 1, 2), Decimal("100"))

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_price("aapl", date(2025, 1, 2), Decimal("101"))

    def test_latest_prices_returns_newest_row_per_ticker(self):
        make_price("AAPL", date(2025, 1, 2), Decimal("100"))
        make_price("AAPL", date(2025, 1, 3), Decimal("110"))
        make_price("MSFT", date(2025, 1, 2), Decimal("400"))

        prices = latest_prices(["aapl", "MSFT", "TSLA"])

        self.assertEqual(prices["AAPL"].close_price, Decimal("110"))
        self.assertEqual(prices["MSFT"].close_price, Decimal("400"))
        self.assertNotIn("TSLA", prices)


@override_settings(CACHES=TEST_CACHES)
class MarketApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.investor = User.objects.create_user(username="investor", email="investor@example.com", password="Pass12345!")
        self.analyst = User.objects.create_user(
            username="analyst", email="analyst@example.com", password="Pass12345!", role=User.Role.ANALYST
        )
        make_price("AAPL", date(2025, 1, 2), Decimal("100"))
        make_price("AAPL", date(2025, 1, 3), Decimal("110"))
        make_price("AAPL", date(2025, 1, 6), Decimal("120"))

    def login_as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {create_access_token(user)}")

    def test_latest_price_requires_login(self):
        response = self.client.get("/api/market/prices/AAPL/")
        self.assertEqual(response.status_code, 401)

    def test_latest_price_returns_newest_row(self):
        self.login_as(self.investor)
        response = self.client.get("/api/market/prices/aapl/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["date"], "2025-01-06")
        self.assertEqual(response.data["data"]["close_price"], "120.0000")

    def test_latest_price_returns_404_for_unknown_ticker(self):
        self.login_as(self.investor)
        response = self.client.get("/api/market/prices/TSLA/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["status"], "error")

    def test_invalid_ticker_returns_400(self):
        self.login_as(self.investor)
        response = self.client.get("/api/market/prices/12$$/")
        self.assertEqual(response.status_code, 400)

    def test_history_filters_by_date_range(self):
        self.login_as(self.investor)
        response = self.client.get("/api/market/prices/AAPL/history/?start=2025-01-03&end=2025-01-06")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 2)
        dates = [row["date"] for row in response.data["data"]["results"]]
        self.assertEqual(dates, ["2025-01-06", "2025-01-03"])

    def test_history_is_paginated(self):
        self.login_as(self.investor)
        response = self.client.get("/api/market/prices/AAPL/history/?page_size=2")
        self.assertEqual(len(response.data["data"]["results"]), 2)
        self.assertIsNotNone(response.data["data"]["next"])

    def test_history_rejects_end_before_start(self):
        self.login_as(self.investor)
        response = self.client.get("/api/market/prices/AAPL/history/?start=2025-02-01&end=2025-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("end", response.data["errors"])

    def test_history_rejects_bad_date_format(self):
        self.login_as(self.investor)
        response = self.client.get("/api/market/prices/AAPL/history/?start=03-01-2025")
        self.assertEqual(response.status_code, 400)
        self.assertIn("start", response.data["errors"])

    def test_investor_cannot_refresh(self):
        self.login_as(self.investor)
        response = self.client.post("/api/market/refresh/AAPL/")
        self.assertEqual(response.status_code, 403)

    @patch("market_data.views.refresh_single_ticker.delay")
    def test_analyst_can_queue_refresh(self, mock_delay):
        mock_delay.return_value.id = "fake-task-id"
        self.login_as(self.analyst)
        response = self.client.post("/api/market/refresh/aapl/")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["data"]["task_id"], "fake-task-id")
        mock_delay.assert_called_once_with("AAPL")

    @patch.object(MarketRefreshThrottle, "rate", "2/hour", create=True)
    @patch("market_data.views.refresh_single_ticker.delay")
    def test_too_many_refreshes_return_429(self, mock_delay):
        mock_delay.return_value.id = "fake-task-id"
        self.login_as(self.analyst)
        self.client.post("/api/market/refresh/AAPL/")
        self.client.post("/api/market/refresh/AAPL/")
        response = self.client.post("/api/market/refresh/AAPL/")
        self.assertEqual(response.status_code, 429)


@override_settings(CACHES=TEST_CACHES, MARKET_SEED_TICKERS=["MSFT"])
class TaskTests(TestCase):
    @patch("market_data.tasks.fetch_prices")
    def test_refresh_writes_only_new_rows(self, mock_fetch):
        make_price("AAPL", date(2025, 1, 2), Decimal("100"))
        mock_fetch.return_value = provider_frame([
            [date(2025, 1, 3), 101, 103, 100, 102, 2000],
            [date(2025, 1, 6), 102, 104, 101, 103, 3000],
        ])

        result = refresh_single_ticker.apply(args=["aapl"]).get()

        self.assertEqual(result, {"ticker": "AAPL", "rows_inserted": 2})
        self.assertEqual(mock_fetch.call_args.args[1], date(2025, 1, 3))
        self.assertEqual(PriceHistory.objects.filter(ticker="AAPL").count(), 3)

    @patch("market_data.tasks.fetch_prices")
    def test_refresh_retries_when_provider_fails(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("provider down")
        result = refresh_single_ticker.apply(args=["AAPL"])
        self.assertTrue(result.failed())
        self.assertEqual(mock_fetch.call_count, 4)

    @patch("market_data.tasks.fetch_prices")
    def test_daily_fetch_covers_stored_and_seed_tickers(self, mock_fetch):
        make_price("AAPL", date(2025, 1, 2), Decimal("100"))
        mock_fetch.return_value = provider_frame([[date(2025, 1, 3), 101, 103, 100, 102, 2000]])

        result = fetch_daily_prices.apply().get()

        self.assertEqual(result["tickers_checked"], 2)
        self.assertEqual(result["tickers_updated"], ["AAPL", "MSFT"])
        self.assertEqual(PriceHistory.objects.filter(ticker="MSFT").count(), 1)
