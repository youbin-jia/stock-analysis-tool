import math
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi.testclient import TestClient

from main import app
from services.scenario_service import ScenarioService


SHANGHAI = ZoneInfo("Asia/Shanghai")
NOW = datetime(2026, 10, 29, 10, 0, tzinfo=SHANGHAI)


def history(periods=320):
    dates = pd.bdate_range(end="2026-10-28", periods=periods)
    closes = [1000 + i * 0.5 + 10 * math.sin(i / 5) for i in range(len(dates))]
    return pd.DataFrame({
        "date": dates,
        "open": [v - 1 for v in closes],
        "high": [v + 4 for v in closes],
        "low": [v - 4 for v in closes],
        "close": closes,
        "volume": [10000] * len(dates),
    })


def quote(timestamp="2026-10-29T09:59:50+08:00", price=1200):
    return {
        "price": price, "prev_close": 1165, "open": 1170, "high": 1210,
        "low": 1160, "volume": 7681747, "amount": 75675740000,
        "change": price - 1165, "change_percent": (price / 1165 - 1) * 100,
        "amplitude": (1210 - 1160) / 1165 * 100,
        "timestamp": timestamp, "source": "腾讯财经",
    }


class ScenarioRealtimeTests(unittest.TestCase):
    def setUp(self):
        self.frame = history()
        self.history_patch = patch.object(
            ScenarioService, "_fetch_close", return_value=self.frame
        ).start()
        self.quote_patch = patch.object(
            ScenarioService, "_fetch_quote", return_value=quote()
        ).start()
        patch.object(ScenarioService, "_now", return_value=NOW).start()
        self.addCleanup(patch.stopall)

    def test_intraday_quote_updates_anchor_history_and_indicators(self):
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(data["last_date"], "2026-10-29")
        self.assertEqual(data["last_price"], 1200)
        self.assertEqual(data["history"][-1]["close"], 1200)
        for field in ("open", "high", "low"):
            self.assertEqual(data["history"][-1][field], quote()[field])
        self.assertEqual(data["quote"]["status"], "live")
        self.assertEqual(data["quote"]["timestamp"], quote()["timestamp"])
        expected_ma5 = (self.frame["close"].tail(4).sum() + 1200) / 5
        self.assertAlmostEqual(data["indicators"]["ma5"], expected_ma5, places=3)
        for field in ("dif", "dea", "macd", "rsi14", "k", "d", "j",
                      "boll_upper", "boll_mid", "boll_lower", "atr14", "ma250"):
            self.assertTrue(math.isfinite(data["indicators"][field]), field)

    def test_same_day_is_replaced_not_duplicated_and_does_not_change_volatility(self):
        first = ScenarioService.get_scenario("sh000688")
        self.frame.loc[len(self.frame)] = [
            pd.Timestamp("2026-10-29"), 1170, 1190, 1160, 1180, 1000
        ]
        second = ScenarioService.get_scenario("sh000688")
        self.assertEqual(second["history"][-1]["close"], 1200)
        self.assertEqual(second["history"][-1]["high"], 1210)
        self.assertEqual(sum(r["date"] == "2026-10-29" for r in second["history"]), 1)
        self.assertEqual(first["annualized_vol"], second["annualized_vol"])
        self.assertEqual(second["volatility_as_of"], "2026-10-28")
        self.assertEqual(second["indicators"], first["indicators"])

    def test_history_contains_aligned_daily_indicator_series(self):
        data = ScenarioService.get_scenario("sh000688", history_days=120)
        rows = data["history"]
        expected_dates = [
            d.strftime("%Y-%m-%d") for d in self.frame["date"].tail(119)
        ] + ["2026-10-29"]
        self.assertEqual([row["date"] for row in rows], expected_dates)
        for field, value in data["indicators"].items():
            self.assertEqual(rows[-1][field], value, field)
            self.assertGreater(len({row[field] for row in rows}), 1, field)
        self.assertTrue(all(row["date"] <= data["last_date"] for row in rows))
        self.assertTrue(set(expected_dates).isdisjoint(data["forward_dates"]))

    def test_default_history_includes_every_available_bar_and_indicator(self):
        frame = history(periods=1800)
        self.history_patch.return_value = frame
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(len(data["history"]), 1801)
        self.assertEqual(data["history_count"], 1801)
        self.assertEqual(data["history_start"], frame["date"].iloc[0].strftime("%Y-%m-%d"))
        self.assertEqual(data["history"][0]["date"], data["history_start"])
        for field in ("open", "close", "low", "high"):
            self.assertAlmostEqual(data["history"][0][field], frame[field].iloc[0], places=2)
        self.assertIsNone(data["history"][0]["ma250"])
        self.assertIsNone(data["history"][0]["rsi14"])
        self.assertIsNotNone(data["history"][249]["ma250"])
        self.assertEqual(data["history"][-1]["date"], "2026-10-29")
        self.assertEqual(data["history"][-1]["close"], 1200)
        self.assertEqual(len({row["date"] for row in data["history"]}), 1801)
        for field, value in data["indicators"].items():
            self.assertEqual(data["history"][-1][field], value, field)

        recent = ScenarioService.get_scenario("sh000688", history_days=120)
        self.assertEqual(recent["history"], data["history"][-120:])
        self.assertEqual(recent["indicators"], data["indicators"])
        self.assertEqual(recent["annualized_vol"], data["annualized_vol"])
        self.assertEqual(recent["scenarios"], data["scenarios"])

    def test_indicators_are_computed_before_trimming_visible_history(self):
        data = ScenarioService.get_scenario("sh000688", history_days=40)
        self.assertEqual(len(data["history"]), 40)
        first = data["history"][0]
        preceding = self.frame[self.frame["date"] <= pd.Timestamp(first["date"])]
        for period in (20, 60, 120, 250):
            self.assertAlmostEqual(
                first[f"ma{period}"],
                preceding["close"].tail(period).mean(),
                places=3,
            )
        self.assertIsNotNone(first["rsi14"])
        self.assertIsNotNone(first["atr14"])

    def test_live_update_changes_last_indicator_point_only(self):
        first = ScenarioService.get_scenario("sh000688")
        self.quote_patch.return_value = {**quote(price=1220), "high": 1230, "low": 1150}
        second = ScenarioService.get_scenario("sh000688")
        self.assertEqual(first["history"][:-1], second["history"][:-1])
        self.assertNotEqual(first["history"][-1]["dif"], second["history"][-1]["dif"])
        self.assertNotEqual(first["history"][-1]["rsi14"], second["history"][-1]["rsi14"])
        self.assertEqual(second["history"][-1]["date"], first["history"][-1]["date"])
        self.assertEqual(
            {field: second["history"][-1][field] for field in ("open", "close", "low", "high")},
            {"open": 1170, "close": 1220, "low": 1150, "high": 1230},
        )

    def test_short_history_preserves_missing_warmup_values(self):
        self.history_patch.return_value = self.frame.tail(80)
        data = ScenarioService.get_scenario("sh000688", vol_window=20)
        self.assertEqual(len(data["history"]), 81)
        self.assertIsNone(data["history"][0]["ma20"])
        self.assertIsNone(data["history"][0]["rsi14"])
        self.assertIsNone(data["history"][-1]["ma250"])

    def test_quote_arriving_after_request_started_is_accepted(self):
        ScenarioService._now.side_effect = [NOW - timedelta(seconds=20), NOW]
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(data["quote"]["status"], "live")
        self.assertEqual(data["generated_at"], NOW.isoformat())

    def test_late_partial_quote_after_close_is_not_a_completed_daily_return(self):
        ScenarioService._now.return_value = NOW.replace(hour=15, minute=10)
        self.quote_patch.return_value = quote("2026-10-29T14:55:00+08:00")
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(data["quote"]["status"], "delayed")
        self.assertTrue(data["quote"]["is_intraday"])
        self.assertEqual(data["volatility_as_of"], "2026-10-28")

    def test_closing_quote_is_included_in_realized_volatility(self):
        ScenarioService._now.return_value = NOW.replace(hour=16)
        self.quote_patch.return_value = quote("2026-10-29T15:05:00+08:00")
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(data["quote"]["status"], "closed")
        self.assertFalse(data["quote"]["is_intraday"])
        self.assertEqual(data["volatility_as_of"], "2026-10-29")

    def test_repeated_quote_changes_update_the_whole_snapshot(self):
        first = ScenarioService.get_scenario("sh000688")
        self.quote_patch.return_value = quote(price=1220)
        second = ScenarioService.get_scenario("sh000688")
        self.assertEqual(second["last_price"], 1220)
        self.assertNotEqual(first["indicators"]["macd"], second["indicators"]["macd"])
        self.assertNotEqual(first["scenarios"], second["scenarios"])
        self.assertEqual(len(self.frame), 320)

    def test_before_open_keeps_actual_previous_quote_date(self):
        ScenarioService._now.return_value = NOW.replace(hour=8)
        self.quote_patch.return_value = quote("2026-10-28T15:05:00+08:00")
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(data["last_date"], "2026-10-28")
        self.assertEqual(data["quote"]["status"], "closed")
        self.assertNotEqual(data["quote"]["timestamp"], data["generated_at"])

    def test_old_quote_is_marked_delayed_during_trading(self):
        self.quote_patch.return_value = quote("2026-10-28T15:05:00+08:00")
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(data["quote"]["status"], "delayed")
        self.assertEqual(data["last_date"], "2026-10-28")

    def test_no_quote_falls_back_to_history_without_claiming_realtime(self):
        self.quote_patch.return_value = None
        data = ScenarioService.get_scenario("sh000688")
        self.assertEqual(data["last_date"], "2026-10-28")
        self.assertEqual(data["quote"]["status"], "historical")
        self.assertIsNone(data["quote"]["timestamp"])
        self.assertIsNone(data["quote"]["amount"])
        self.assertIsNone(data["quote"]["volume"])
        self.assertIsNotNone(data["indicators"]["macd"])
        for field in ("open", "close", "low", "high"):
            self.assertEqual(data["history"][-1][field], round(self.frame[field].iloc[-1], 2))

    def test_older_than_history_or_future_quote_is_not_used(self):
        for timestamp in ("2026-10-27T15:05:00+08:00", "2026-10-30T10:00:00+08:00"):
            with self.subTest(timestamp=timestamp):
                self.quote_patch.return_value = quote(timestamp)
                data = ScenarioService.get_scenario("sh000688")
                self.assertEqual(data["last_date"], "2026-10-28")
                self.assertEqual(data["quote"]["status"], "historical")


class QuoteParsingTests(unittest.TestCase):
    def payload(self, timestamp="20261029100000", price="1282.93"):
        fields = [""] * 50
        for index, value in {
            1: "科创50", 2: "000688", 3: price, 4: "1252.28", 5: "1279.90",
            30: timestamp, 33: "1297.09", 34: "1257.96",
            36: "7681747", 37: "7567574",
        }.items():
            fields[index] = value
        return 'v_sh000688="' + "~".join(fields) + '";'

    @patch("services.scenario_service.requests.get")
    def test_index_prefix_provider_time_and_units_are_preserved(self, get):
        get.return_value = Mock(text=self.payload())
        data = ScenarioService._fetch_quote("sh000688")
        self.assertEqual(data["timestamp"], "2026-10-29T10:00:00+08:00")
        self.assertEqual(data["volume"], 7681747)
        self.assertEqual(data["amount"], 75675740000)
        self.assertAlmostEqual(data["change_percent"], 2.45, places=2)
        self.assertIn("sh000688", get.call_args.args[0])
        self.assertLessEqual(get.call_args.kwargs["timeout"], 10)

    @patch("services.scenario_service.requests.get")
    def test_invalid_quote_is_rejected(self, get):
        for text in ('v_sh000688="";', self.payload(price="0"),
                     self.payload(price="nan"), self.payload(timestamp=""),
                     self.payload().replace("v_sh000688", "v_sz000688")):
            with self.subTest(text=text[:35]):
                get.return_value = Mock(text=text)
                self.assertIsNone(ScenarioService._fetch_quote("sh000688"))


class HistoryConcurrencyTests(unittest.TestCase):
    @patch("services.scenario_service.CacheService.set_cached_quant")
    @patch("services.scenario_service.CacheService.get_cached_quant")
    @patch("services.scenario_service.ak.stock_zh_index_daily")
    def test_post_close_refresh_bypasses_old_history_cache(self, fetch, get_cache, set_cache):
        fetch.return_value = history()
        frame = ScenarioService._fetch_close("sh000688", refresh=True)
        get_cache.assert_not_called()
        fetch.assert_called_once_with(symbol="sh000688")
        self.assertEqual(len(frame), 320)
        set_cache.assert_called_once()

    @patch("services.scenario_service.CacheService.set_cached_quant")
    @patch("services.scenario_service.CacheService.get_cached_quant")
    @patch("services.scenario_service.ak.stock_zh_index_daily")
    def test_simultaneous_cold_requests_share_a_single_history_fetch(self, fetch, get_cache, set_cache):
        cache = {}
        get_cache.side_effect = cache.get
        set_cache.side_effect = lambda key, data, ttl: cache.update({key: data})

        def slow_fetch(**kwargs):
            time.sleep(0.03)
            return history()

        fetch.side_effect = slow_fetch
        barrier = threading.Barrier(2)

        def load():
            barrier.wait(timeout=2)
            return ScenarioService._fetch_close("sh000688")

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(load) for _ in range(2)]
            frames = [future.result(timeout=3) for future in futures]
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(len(frames[0]), 320)
        pd.testing.assert_frame_equal(
            frames[0][["date", "close"]], frames[1][["date", "close"]]
        )


class MarketRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @patch("api.market.CacheService.set_cached_quant")
    @patch("api.market.CacheService.get_cached_quant", return_value=None)
    @patch("api.market.ScenarioService.get_scenario", return_value={"last_price": 1234})
    def test_short_cache_and_manual_refresh(self, scenario, get_cache, set_cache):
        response = self.client.get("/api/market/scenario")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(set_cache.call_args.kwargs["ttl"], 15)
        self.assertIn("v4", set_cache.call_args.args[0])
        get_cache.reset_mock()
        self.client.get("/api/market/scenario?refresh=true")
        get_cache.assert_not_called()
        self.assertEqual(scenario.call_count, 2)

    @patch("api.market.CacheService.set_cached_quant")
    @patch("api.market.CacheService.get_cached_quant", return_value=None)
    def test_api_defaults_to_complete_history(self, get_cache, set_cache):
        frame = history(periods=1800)
        with patch.object(ScenarioService, "_fetch_close", return_value=frame), \
                patch.object(ScenarioService, "_fetch_quote", return_value=None), \
                patch.object(ScenarioService, "_now", return_value=NOW):
            response = self.client.get("/api/market/scenario")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["history_count"], 1800)
        self.assertEqual(len(data["history"]), 1800)
        self.assertEqual(data["history_start"], frame["date"].iloc[0].strftime("%Y-%m-%d"))
        for field in ("open", "close", "low", "high"):
            self.assertEqual(data["history"][0][field], round(frame[field].iloc[0], 2))

    @patch("api.market.ScenarioService.get_scenario")
    def test_unsupported_index_is_rejected_before_fetching(self, scenario):
        response = self.client.get("/api/market/scenario?index_code=invalid")
        self.assertEqual(response.status_code, 400)
        scenario.assert_not_called()


if __name__ == "__main__":
    unittest.main()
