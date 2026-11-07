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


class PersonSuggestions(unittest.TestCase):
    def test_assigned_rank_and_related_sources_do_not_group_devices(self):
        now = datetime.now(UTC)

        def row(id, platform, device, attrs, value="home"):
            return sources.SourceSnapshot(id, value, attrs, now, platform, device)

        gps = {"latitude": 1, "longitude": 2, "source_type": "gps"}
        catalog = sources.SourceCatalog(
            [
                row(
                    "person.river",
                    "person",
                    None,
                    {"device_trackers": ["device_tracker.z", "device_tracker.y"]},
                ),
                row("device_tracker.a", "mobile_app", "a", gps),
                row("device_tracker.z", "mobile_app", "z", gps, "unavailable"),
                row("device_tracker.y", "icloud3", "z", gps),
                row("device_tracker.ours", "person_presence", "z", gps),
                row("sensor.z_charge", "mobile_app", "z", {}, "Charging"),
            ]
        )
        candidates = catalog.person_candidates("person.river", "tracker")
        self.assertEqual(
            [c.entity_id for c in candidates],
            ["device_tracker.y", "device_tracker.z", "device_tracker.a"],
        )
        self.assertEqual(candidates[0].basis, "person_assignment")
        self.assertIn("Source unavailable", candidates[1].warnings)
        self.assertEqual(
            catalog.person_candidates("person.river", "charging")[0].basis,
            "related_registry_device",
        )
        self.assertEqual(len(candidates), 3)
