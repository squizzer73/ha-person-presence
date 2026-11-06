import unittest
from datetime import UTC, datetime

from test_engine import load

sources = load("sources")
places = load("places")
preview = load("preview")


class Preview(unittest.TestCase):
    def test_preview_uses_same_evidence_without_persisting(self):
        catalog = sources.SourceCatalog(
            [
                sources.SourceSnapshot(
                    "sensor.area", "Library", {}, datetime.fromtimestamp(999, UTC)
                )
            ]
        )
        config = {
            "name": "Alex",
            "person": "person.alex",
            "devices": [
                {"key": "phone", "name": "Phone", "priority": 1, "room": "sensor.area"}
            ],
        }
        result = preview.build_preview(config, catalog, places.PlaceCatalog(), 1000)
        self.assertEqual(result.value, "Library")
        self.assertEqual(result.selected_device, "Phone")
        self.assertIn("phone", result.evidence)
        self.assertIn("measurement time", result.summary)
        self.assertIn("sensor.area", result.summary)
        self.assertIn("tracker", result.missing_capabilities["phone"])

    def test_missing_source_is_explained(self):
        config = {
            "name": "Alex",
            "person": "person.alex",
            "devices": [
                {
                    "key": "phone",
                    "name": "Phone",
                    "priority": 1,
                    "tracker": "device_tracker.missing",
                }
            ],
        }
        result = preview.build_preview(
            config, sources.SourceCatalog(), places.PlaceCatalog(), 1000
        )
        self.assertIsNone(result.value)
        self.assertIn("missing", result.summary.lower())
