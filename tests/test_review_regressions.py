"""Fictional probes from the independent beta review."""

import unittest
from datetime import UTC, datetime

from test_engine import load
from test_inputs import state

engine = load("engine")
inputs = load("inputs")
sources = load("sources")
places = load("places")
where = load("whereabouts")


class ReviewRegressions(unittest.TestCase):
    def test_router_coordinates_and_wrist_motion_are_not_supported_capabilities(self):
        at = datetime.fromtimestamp(999, UTC)
        router = sources.SourceSnapshot(
            "device_tracker.router",
            "home",
            {
                "source_type": "router",
                "latitude": 1,
                "longitude": 2,
                "gps_accuracy": 10,
            },
            at,
        )
        motion = sources.SourceSnapshot(
            "binary_sensor.wrist_motion", "on", {"device_class": "motion"}, at
        )
        catalog = sources.SourceCatalog([router, motion])
        self.assertEqual(catalog.candidates("tracker"), [])
        self.assertEqual(catalog.candidates("worn"), [])
        obs = inputs.observe(
            {
                "key": "phone",
                "priority": 1,
                "tracker": router.entity_id,
                "worn": motion.entity_id,
            },
            catalog.get_state,
            1000,
            "UTC",
            600,
            100,
            catalog=catalog,
        )
        self.assertIsNone(obs.location)
        self.assertIsNone(obs.worn)

    def test_non_home_zone_named_home_keeps_away_identity(self):
        catalog = places.PlaceCatalog(
            {},
            [
                places.Zone("zone.home", "Home", 40, 40, 100),
                places.Zone("zone.other", "home", 1, 2, 100),
            ],
        )
        states = {
            "device_tracker.phone": state(
                "home",
                latitude=1,
                longitude=2,
                gps_accuracy=10,
                located="1970-01-01T00:16:39+00:00",
            )
        }
        obs = inputs.observe(
            {"key": "phone", "priority": 1, "tracker": "device_tracker.phone"},
            states.get,
            1000,
            "UTC",
            600,
            100,
            places=catalog,
        )
        result = engine.Resolver(settle=0).update([obs], 1000)
        output = where.project_whereabouts(
            result, catalog, "person.alex", {"phone": "Phone"}
        )
        self.assertEqual(
            (
                output.value,
                output.attributes["presence"],
                output.attributes["context"],
                output.attributes["zone_id"],
            ),
            ("home", "away", "zone", "zone.other"),
        )

    def test_date_only_does_not_invent_midnight_observation(self):
        self.assertIsNone(inputs.timestamp("2026-11-05", "UTC"))

    def test_held_room_is_dropped_when_new_evidence_disqualifies_it(self):
        resolver = engine.Resolver(settle=15)
        room = [engine.Observation("phone", 1, room="Library", room_at=999)]
        resolver.update(room, 1000)
        self.assertEqual(resolver.update(room, 1015).room, "Library")
        result = resolver.update(
            [
                engine.Observation(
                    "phone",
                    1,
                    location="not_home",
                    location_at=1020,
                    reason_codes=("local_guard_away",),
                )
            ],
            1020,
        )
        self.assertIsNone(result.room)
        self.assertIsNone(result.location)
        self.assertTrue(result.pending)
