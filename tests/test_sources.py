import unittest
from datetime import UTC, datetime

from test_engine import load

sources = load("sources")
places = load("places")


class Sources(unittest.TestCase):
    def test_role_filters_and_retained_missing_mapping(self):
        rows = [
            sources.SourceSnapshot(
                "device_tracker.gps",
                "home",
                {
                    "latitude": 1,
                    "longitude": 2,
                    "gps_accuracy": 10,
                    "source_type": "gps",
                },
                datetime.fromtimestamp(999, UTC),
                "mobile_app",
                "a",
            ),
            sources.SourceSnapshot(
                "device_tracker.ble",
                "home",
                {"source_type": "bluetooth_le"},
                datetime.fromtimestamp(999, UTC),
                "bermuda",
                "b",
            ),
            sources.SourceSnapshot(
                "sensor.room_area",
                "Library",
                {},
                datetime.fromtimestamp(999, UTC),
                "bermuda",
                "b",
            ),
            sources.SourceSnapshot(
                "sensor.battery",
                "75",
                {"device_class": "battery"},
                datetime.fromtimestamp(999, UTC),
                "mobile_app",
                "a",
            ),
            sources.SourceSnapshot(
                "sensor.charge",
                "Charging",
                {},
                datetime.fromtimestamp(999, UTC),
                "mobile_app",
                "a",
            ),
        ]
        catalog = sources.SourceCatalog(rows)
        self.assertEqual(
            [c.entity_id for c in catalog.candidates("tracker")], ["device_tracker.gps"]
        )
        self.assertEqual(
            [c.entity_id for c in catalog.candidates("room")], ["sensor.room_area"]
        )
        self.assertNotIn(
            "sensor.battery", [c.entity_id for c in catalog.candidates("charging")]
        )
        self.assertEqual(
            catalog.candidates("room", current_entity_id="sensor.deleted")[
                -1
            ].entity_id,
            "sensor.deleted",
        )

    def test_same_names_never_confirm_cross_provider_identity(self):
        catalog = sources.SourceCatalog([])
        self.assertEqual(catalog.suggestions("unknown"), {})


class Places(unittest.TestCase):
    def test_home_precedence_and_passive_zone(self):
        catalog = places.PlaceCatalog(
            {"studio": "Studio"},
            [
                places.Zone("zone.town", "Town", 0, 0, 10000),
                places.Zone("zone.home", "Home", 0, 0, 100),
                places.Zone("zone.passive", "Passive", 0, 0, 1, True),
            ],
        )
        self.assertEqual(catalog.resolve_zone(0, 0, []), "zone.home")
        self.assertEqual(catalog.resolve_zone(0, 0.02, []), "zone.town")
        self.assertIsNone(catalog.resolve_zone(40, 40, ["zone.deleted"]))

    def test_label_changes_preserve_identity(self):
        catalog = places.PlaceCatalog({"studio": "New name"}, [])
        self.assertEqual(catalog.area_name("studio"), "New name")
