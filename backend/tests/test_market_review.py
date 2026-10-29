import inspect
import math
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from apscheduler.triggers.cron import CronTrigger
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from models.database import IndexCloseReview
from services.market_review_service import MarketReviewService, build_close_review
from services.scenario_service import INDEX_MAP, SHANGHAI, ScenarioService
from tasks.scheduler import start_scheduler, update_daily_data, update_market_reviews

NOW = datetime(2026, 10, 29, 10, 0, tzinfo=SHANGHAI)


def bars(direction=0, periods=320, end="2026-10-28"):
    dates = pd.bdate_range(end=end, periods=periods)
    closes = [1000 + direction * i + 2 * math.sin(i / 3) for i in range(periods)]
    return [
        {"date": day.strftime("%Y-%m-%d"), "open": close - 1, "close": close,
         "high": close + 4, "low": close - 4}
        for day, close in zip(dates, closes)
    ]


def dataframe(rows):
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def closing_quote(timestamp="2026-10-29T15:05:00+08:00"):
    return {
        "open": 1000, "price": 1010, "low": 990, "high": 1020,
        "timestamp": timestamp, "source": "腾讯财经",
    }


class ReviewRulesTests(unittest.TestCase):
    def test_strong_weak_and_mixed_trends_have_conditional_strategies(self):
        for direction, expected in ((2, "bullish"), (-2, "bearish"), (0, "neutral")):
            with self.subTest(direction=direction):
                rows = bars(direction)
                report = build_close_review("sh000688", rows)
                self.assertEqual(report["trend"], expected)
                self.assertEqual(report["trade_date"], "2026-10-28")
                self.assertEqual(len(report["strategies"]), 3)
                self.assertEqual(len(report["evidence"]), 4)
                self.assertNotIn("confidence", report)
                self.assertIn("不换算上涨概率", report["methodology"])
                self.assertNotIn("ma20", rows[-1], "the builder must not mutate source bars")

    def test_levels_use_previous_twenty_bars_not_the_current_bar(self):
        rows = bars()
        rows[-1].update(open=1000, close=1100, high=1105, low=990)
        report = build_close_review("sh000688", rows)
        high = next(level for level in report["levels"] if level["name"] == "前20日高点")
        self.assertEqual(high["value"], round(max(row["high"] for row in rows[-21:-1]), 2))
        self.assertEqual(high["role"], "支撑观察")
        self.assertEqual(report["evidence"][-1]["signal"], "收盘突破前 20 日最高价")

    def test_oversold_is_not_presented_as_an_unconditional_buy(self):
        report = build_close_review("sh000688", bars(-2))
        self.assertEqual(report["stance"], "防守优先，等待转强")
        self.assertTrue(any("超卖不等于见底" in risk for risk in report["risks"]))
        self.assertIn("保持观望", report["strategies"][1]["detail"])

    def test_incomplete_or_invalid_bars_do_not_generate_recommendations(self):
        self.assertIsNone(build_close_review("sh000688", bars(periods=64)))
        for change in ({"close": float("nan")}, {"low": 2000}, {"high": None}, {"open": 0}):
            with self.subTest(change=change):
                rows = bars()
                rows[-1].update(change)
                self.assertIsNone(build_close_review("sh000688", rows))


class ReviewLifecycleTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = create_engine(f"sqlite:///{Path(directory.name) / 'reviews.db'}")
        self.addCleanup(self.engine.dispose)
        IndexCloseReview.__table__.create(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        patch("services.market_review_service.SessionLocal", self.sessions).start()
        self.clock = patch.object(MarketReviewService, "_now", return_value=NOW).start()
        self.history = patch.object(ScenarioService, "_fetch_close", return_value=dataframe(bars())).start()
        self.quote = patch.object(ScenarioService, "_fetch_quote", return_value=None).start()
        self.cache = patch("services.market_review_service.CacheService.get_cached_quant", return_value=None).start()
        self.write_cache = patch("services.market_review_service.CacheService.set_cached_quant").start()
        self.addCleanup(patch.stopall)

    def test_intraday_uses_previous_completed_session_even_if_today_is_in_history(self):
        self.history.return_value = dataframe(bars(end="2026-10-29"))
        result = MarketReviewService.get_review("sh000688")
        self.assertEqual(result["state"], "waiting_close")
        self.assertEqual(result["report"]["trade_date"], "2026-10-28")
        self.history.assert_called_once_with("sh000688", refresh=False)
        self.quote.assert_not_called()

    def test_partial_today_prices_cannot_change_previous_session_strategy(self):
        baseline = MarketReviewService.get_review("sh000688")["report"]
        rows = bars() + [{
            "date": "2026-10-29", "open": 1000, "close": 2000, "high": 2100, "low": 990,
        }]
        self.history.return_value = dataframe(rows)
        result = MarketReviewService.get_review("sh000688", refresh=True)
        self.assertEqual(result["report"], baseline)

    def test_close_cutoff_and_timestamped_quote_are_required(self):
        for hour, minute, quote_time, expected in (
            (15, 29, "15:05", "2026-10-28"),
            (15, 30, "14:55", "2026-10-28"),
            (15, 30, "15:05", "2026-10-29"),
        ):
            with self.subTest(hour=hour, minute=minute, quote_time=quote_time):
                self.clock.return_value = NOW.replace(hour=hour, minute=minute)
                self.quote.return_value = closing_quote(f"2026-10-29T{quote_time}:00+08:00")
                result = MarketReviewService.get_review("sh000688", refresh=True)
                self.assertEqual(result["report"]["trade_date"], expected)
        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["report"]["close"], 1010)
        self.history.assert_called_with("sh000688", refresh=True)

    def test_delayed_intraday_quote_does_not_confirm_a_partial_today_bar(self):
        self.clock.return_value = NOW.replace(hour=16)
        self.history.return_value = dataframe(bars(end="2026-10-29"))
        self.quote.return_value = closing_quote("2026-10-29T14:55:00+08:00")
        result = MarketReviewService.get_review("sh000688", refresh=True)
        self.assertEqual(result["report"]["trade_date"], "2026-10-28")
        self.assertEqual(result["state"], "pending_data")

    def test_post_close_daily_history_can_supply_a_report_when_quote_is_unavailable(self):
        self.clock.return_value = NOW.replace(hour=16)
        self.history.return_value = dataframe(bars(end="2026-10-29"))
        result = MarketReviewService.get_review("sh000688")
        self.assertEqual(result["report"]["trade_date"], "2026-10-29")
        self.assertEqual(result["report"]["source"], "收盘后更新的历史日线")
        self.assertEqual(result["state"], "ready")

    def test_future_or_previous_session_quote_is_not_used_as_todays_close(self):
        self.clock.return_value = NOW.replace(hour=16)
        for stamp in ("2026-10-30T15:05:00+08:00", "2026-10-29T16:30:00+08:00",
                      "2026-10-28T15:05:00+08:00"):
            self.quote.return_value = closing_quote(stamp)
            result = MarketReviewService.get_review("sh000688", refresh=True)
            self.assertEqual(result["report"]["trade_date"], "2026-10-28")

    def test_weekend_and_missing_holiday_data_do_not_fabricate_a_new_session(self):
        for stamp in ("2026-10-31T16:00:00+08:00", "2026-10-29T16:00:00+08:00"):
            self.clock.return_value = datetime.fromisoformat(stamp)
            result = MarketReviewService.get_review("sh000688", refresh=True)
            self.assertEqual(result["report"]["trade_date"], "2026-10-28")
            self.assertEqual(result["state"], "pending_data")
        self.assertIn("休市日不生成", result["message"])

    def test_persistence_survives_cache_miss_and_refresh_failure(self):
        original = MarketReviewService.get_review("sh000688")["report"]
        self.history.return_value = None
        failed = MarketReviewService.get_review("sh000688", refresh=True)
        self.assertEqual(failed["report"], original)
        self.assertIsNotNone(failed["error"])
        self.assertEqual(MarketReviewService._latest("sh000688"), original)

    def test_repeated_fetches_are_idempotent_and_store_one_record_per_session(self):
        first = MarketReviewService.get_review("sh000688")["report"]
        self.clock.return_value = NOW.replace(hour=11)
        same = MarketReviewService.get_review("sh000688")["report"]
        self.assertEqual(first, same)
        self.clock.return_value = NOW.replace(hour=16)
        self.quote.return_value = closing_quote()
        latest = MarketReviewService.get_review("sh000688", refresh=True)["report"]
        self.assertEqual(latest["trade_date"], "2026-10-29")
        self.quote.return_value["price"] = 1015
        corrected = MarketReviewService.get_review("sh000688", refresh=True)["report"]
        self.assertEqual(corrected["close"], 1015)
        with self.sessions() as db:
            self.assertEqual(db.query(IndexCloseReview).count(), 2)

    def test_old_source_cannot_replace_newer_stored_review(self):
        self.clock.return_value = NOW.replace(hour=16)
        self.quote.return_value = closing_quote()
        latest = MarketReviewService.get_review("sh000688")["report"]
        self.quote.return_value = None
        result = MarketReviewService.get_review("sh000688", refresh=True)
        self.assertEqual(result["report"], latest)

    def test_no_history_returns_an_explicit_empty_state(self):
        self.history.return_value = None
        result = MarketReviewService.get_review("sh000688")
        self.assertIsNone(result["report"])
        self.assertIsNotNone(result["error"])

    def test_report_and_cache_are_isolated_by_index(self):
        first = MarketReviewService.get_review("sh000688")["report"]
        other = MarketReviewService.get_review("sh000001")["report"]
        self.assertNotEqual(first["index_code"], other["index_code"])
        self.assertEqual(MarketReviewService._latest("sh000688"), first)
        self.assertEqual(MarketReviewService._latest("sh000001"), other)
        self.assertIn("sh000001", self.write_cache.call_args.args[0])

    def test_manual_refresh_bypasses_response_cache(self):
        self.cache.return_value = {"cached": True}
        self.assertEqual(MarketReviewService.get_review("sh000688"), {"cached": True})
        self.history.assert_not_called()
        result = MarketReviewService.get_review("sh000688", refresh=True)
        self.assertIn("report", result)
        self.history.assert_called_once()


class ReviewRouteAndSchedulerTests(unittest.TestCase):
    def test_route_validates_index_and_passes_refresh(self):
        client = TestClient(app)
        self.addCleanup(client.close)
        with patch(
            "api.market.MarketReviewService.get_review", return_value={"report": None}
        ) as service:
            response = client.get("/api/market/close-review?index_code=sh000001&refresh=true")
            self.assertEqual(response.status_code, 200)
            service.assert_called_with("sh000001", refresh=True)
            service.reset_mock()
            self.assertEqual(client.get("/api/market/close-review?index_code=invalid").status_code, 400)
            service.assert_not_called()

    @patch("tasks.scheduler.scheduler")
    def test_schedule_has_shanghai_timezone_retries_and_startup_catchup(self, scheduler):
        start_scheduler()
        jobs = {call.kwargs["id"]: call for call in scheduler.add_job.call_args_list}
        daily = jobs["update_market_reviews"].kwargs
        self.assertEqual(daily["timezone"], SHANGHAI)
        self.assertEqual(daily["max_instances"], 1)
        trigger = CronTrigger(
            day_of_week=daily["day_of_week"], hour=daily["hour"],
            minute=daily["minute"], timezone=daily["timezone"],
        )
        fire = trigger.get_next_fire_time(None, NOW)
        self.assertEqual(fire, NOW.replace(hour=15, minute=30))
        self.assertEqual(trigger.get_next_fire_time(fire, fire), NOW.replace(hour=16, minute=30))
        self.assertIn("catch_up_market_reviews", jobs)
        self.assertFalse(inspect.iscoroutinefunction(update_market_reviews))
        self.assertFalse(inspect.iscoroutinefunction(update_daily_data))

    @patch("tasks.scheduler.MarketReviewService.get_review")
    def test_one_failed_index_does_not_stop_remaining_reviews(self, get_review):
        get_review.side_effect = [RuntimeError("source down")] + [{"error": None}] * (len(INDEX_MAP) - 1)
        update_market_reviews()
        self.assertEqual(get_review.call_count, len(INDEX_MAP))
        self.assertTrue(all(call.kwargs["refresh"] for call in get_review.call_args_list))


if __name__ == "__main__":
    unittest.main()
