import asyncio
import threading
import unittest
from unittest.mock import MagicMock, patch

import httpx

from main import app


class RequestConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_responds_while_page_data_is_loading(self):
        cases = [
            ("/api/quant/screen?type=cxg",
             "api.quant.QuantService.get_smart_screen", []),
            ("/api/quant/recommend?limit=30",
             "api.quant.QuantService.get_stock_recommendation", []),
            ("/api/quant/fund-recommend?limit=20",
             "api.quant.QuantService.get_fund_recommend", []),
            ("/api/quant/market-valuation",
             "api.quant.QuantService.get_market_valuation", {}),
            ("/api/quant/market-cycle",
             "api.quant.QuantService.get_market_valuation", {}),
            ("/api/quant/hot-stocks",
             "api.quant.QuantService.get_hot_stocks", []),
            ("/api/quant/score/600519",
             "api.quant.QuantService.get_stock_score", None),
            ("/api/quant/style-score/600519",
             "api.quant.QuantService.get_stock_score", None),
            ("/api/funds/list",
             "api.funds.FundService.get_fund_list", []),
        ]
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            for path, target, result in cases:
                with self.subTest(path=path):
                    await self._check_concurrent_health(client, path, target, result)

            await self._check_concurrent_health(
                client,
                "/api/quant/fundamental-screen",
                "api.quant.QuantService.get_stock_fundamental_screen",
                [],
                method="POST",
                json={},
            )

    async def test_health_responds_while_stock_data_is_loading(self):
        cases = [
            ("/api/stocks/realtime/600519",
             "api.stocks.StockService.get_realtime_data", None),
            ("/api/stocks/info/600519",
             "api.stocks.StockService.get_stock_info", None),
            ("/api/stocks/history/600519?period=1y&frequency=d",
             "api.stocks.load_history_with_warmup", []),
            ("/api/stocks/list",
             "api.stocks.StockService.get_stock_list", []),
            ("/api/stocks/search?keyword=600519",
             "api.stocks.StockService.get_stock_list", []),
            ("/api/stocks/batch-realtime?codes=600519",
             "api.stocks.StockService.get_realtime_data", None),
            ("/api/strategy/signals/600519?period=1y&frequency=d",
             "api.strategy.load_history_with_warmup", []),
        ]
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            with patch(
                "api.stocks.CacheService.get_cached_realtime", return_value=None
            ), patch(
                "api.stocks.CacheService.get_cached_history", return_value=None
            ), patch(
                "api.strategy.CacheService.get_cached_strategy", return_value=None
            ), patch(
                "api.stocks.get_db", side_effect=lambda: iter([db])
            ):
                for path, target, result in cases:
                    with self.subTest(path=path):
                        await self._check_concurrent_health(
                            client, path, target, result
                        )

    async def _check_concurrent_health(
        self, client, path, target, result, method="GET", json=None
    ):
        started = threading.Event()
        release = threading.Event()

        def slow_fetch(*args, **kwargs):
            started.set()
            release.wait(timeout=2)
            return result

        # Release even if a blocking route prevents the event loop from progressing.
        watchdog = threading.Timer(1, release.set)
        with patch(target, side_effect=slow_fetch), patch(
            "api.funds.CacheService.get_cached_fund_list", return_value=None
        ):
            pending = asyncio.create_task(client.request(method, path, json=json))
            watchdog.start()
            try:
                async def wait_until_started():
                    while not started.is_set():
                        await asyncio.sleep(0.001)

                await asyncio.wait_for(wait_until_started(), timeout=2)
                response = await asyncio.wait_for(client.get("/health"), timeout=0.5)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "ok")
                self.assertFalse(
                    release.is_set(),
                    f"{path} blocked health until the data fetch finished",
                )
                self.assertFalse(pending.done())
            finally:
                release.set()
                watchdog.cancel()
                watchdog.join()
                await asyncio.wait_for(pending, timeout=2)


if __name__ == "__main__":
    unittest.main()
