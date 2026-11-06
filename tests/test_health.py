import unittest

from test_engine import load

health = load("health")


class Health(unittest.TestCase):
    def test_source_reasons_are_readable_and_not_probability(self):
        result = health.SourceHealth.from_evidence(
            {
                "phone": {
                    "reasons": ["stale_location"],
                    "gps_observed_at": 100,
                    "timestamp_quality": "measurement",
                },
                "watch": {"reasons": ["eligibility_unconfirmed"]},
            }
        )
        self.assertIn("GPS", result.describe("phone", 1000))
        self.assertIn("15 minutes", result.describe("phone", 1000))
        self.assertIn("unconfirmed", result.describe("watch", 1000))
