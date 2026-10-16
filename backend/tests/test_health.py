import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class HealthCheckTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_timestamp_includes_timezone(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        timestamp = datetime.fromisoformat(response.json()["timestamp"])
        self.assertIsNotNone(timestamp.tzinfo)

    def test_timestamp_is_generated_for_each_request(self):
        first = datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc)
        second = datetime(2026, 10, 13, 0, 0, 1, tzinfo=timezone.utc)

        with patch("main.datetime", create=True) as clock:
            clock.now.side_effect = [first, second]
            first_response = self.client.get("/health")
            second_response = self.client.get("/health")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.json()["timestamp"], first.isoformat())
        self.assertEqual(second_response.json()["timestamp"], second.isoformat())
        self.assertEqual(clock.now.call_count, 2)
        clock.now.assert_called_with(timezone.utc)


if __name__ == "__main__":
    unittest.main()
