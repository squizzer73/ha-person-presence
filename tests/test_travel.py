import unittest
from dataclasses import replace

from test_engine import load

engine = load("engine")
places = load("places")


class Travel(unittest.TestCase):
    def setUp(self):
        self.travel = load("travel").TravelContext()
        self.home = places.Zone("zone.home", "Home", 0, 0, 100)

    def fix(self, at=100, lon=0.01, **kwargs):
        return engine.Result(
            location="not_home",
            selected="phone",
            latitude=0,
            longitude=lon,
            accuracy=10,
            gps_observed_at=at,
            gps_source_entity_id="device_tracker.phone",
            **kwargs,
        )

    def update(self, fix, now=100):
        return self.travel.update(fix, now, 300, self.home)

    def test_distance_first_fix_duplicate_room_reports_and_movement(self):
        first = self.fix()
        value = self.update(first)
        self.assertAlmostEqual(value.distance_m, 1112, delta=2)
        self.assertEqual(value.direction, "unknown")
        self.assertEqual(value.bearing, "E")
        self.assertEqual(self.update(replace(first, observed_at=120), 120), value)
        moving = self.fix(at=140, lon=0.008)
        self.assertEqual(self.update(moving, 140).direction, "towards_home")
        self.assertEqual(self.update(moving, 150).direction, "towards_home")
        self.assertEqual(
            self.update(self.fix(at=160, lon=0.0081), 160).direction, "stationary"
        )

    def test_expiry_pending_missing_room_only_and_source_reset(self):
        self.update(self.fix())
        for bad in [
            replace(self.fix(), pending=True),
            replace(self.fix(), gps_observed_at=None),
            replace(self.fix(), latitude=None),
        ]:
            self.assertIsNone(self.update(bad).distance_m)
        self.assertIsNone(self.update(self.fix(), 401).distance_m)
        self.assertEqual(self.update(self.fix(at=402), 402).direction, "unknown")
        self.assertEqual(
            self.update(replace(self.fix(at=403), selected="watch"), 403).direction,
            "unknown",
        )
        self.assertIsNone(self.travel.update(self.fix(), 100, 300, None).distance_m)

    def test_accuracy_jitter_out_of_order_and_home_reset(self):
        self.update(replace(self.fix(), accuracy=100))
        self.assertEqual(
            self.update(
                replace(self.fix(at=120, lon=0.009), accuracy=100), 120
            ).direction,
            "stationary",
        )
        self.assertEqual(self.update(self.fix(at=110), 130).direction, "unknown")
        self.assertEqual(
            self.update(self.fix(at=120, lon=0.02), 130).direction, "unknown"
        )
        moved = places.Zone("zone.home", "Home", 0, 0.001, 100)
        self.assertEqual(
            self.travel.update(self.fix(at=140), 140, 300, moved).direction, "unknown"
        )

    def test_resolver_keeps_gps_clock_distinct_from_room(self):
        result = engine.Resolver(settle=0).update(
            [
                engine.Observation(
                    key="p",
                    priority=1,
                    location="home",
                    location_at=100,
                    room="Study",
                    room_at=140,
                    latitude=0,
                    longitude=0,
                    gps_source_entity_id="device_tracker.p",
                )
            ],
            140,
        )
        self.assertEqual(result.observed_at, 140)
        self.assertEqual(result.gps_observed_at, 100)
