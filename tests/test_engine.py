"""Behavioral scenarios use fictional households and hand-derived expectations."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/person_presence"


def load(name):
    if "presence_core" not in sys.modules:
        package = types.ModuleType("presence_core")
        package.__path__ = [str(ROOT)]
        sys.modules["presence_core"] = package
    name = "presence_core." + name
    spec = importlib.util.spec_from_file_location(
        name, ROOT / f"{name.rsplit(chr(46), 1)[-1]}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine = load("engine")
Observation = engine.Observation
Resolver = engine.Resolver


class Scenarios(unittest.TestCase):
    def obs(self, key, priority, **kw):
        return Observation(key, priority, **kw)

    def test_four_requested_scenarios(self):
        cases = [
            (
                [
                    self.obs("watch", 1, worn=True, room="Lounge", room_at=990),
                    self.obs("phone", 2, room="Lounge", room_at=990),
                ],
                "home",
                "Lounge",
                "watch",
            ),
            (
                [
                    self.obs(
                        "watch", 1, excluded="charging", room="Bedroom", room_at=990
                    ),
                    self.obs("phone", 2, room="Lounge", room_at=990),
                ],
                "home",
                "Lounge",
                "phone",
            ),
            (
                [
                    self.obs("watch", 1, worn=True, room="Lounge", room_at=990),
                    self.obs("phone", 2, room="Kitchen", room_at=990),
                ],
                "home",
                "Lounge",
                "watch",
            ),
            (
                [
                    self.obs("watch", 1, worn=True, location="Woods", location_at=990),
                    self.obs(
                        "phone", 2, room="Kitchen", room_at=990, excluded="charging"
                    ),
                ],
                "Woods",
                None,
                "watch",
            ),
        ]
        for observations, location, room, selected in cases:
            with self.subTest(location=location, room=room):
                result = Resolver(settle=0).update(observations, 1000)
                self.assertEqual(
                    (result.location, result.room, result.selected),
                    (location, room, selected),
                )

    def test_stale_watch_does_not_override_fresh_phone(self):
        result = Resolver(settle=0).update(
            [
                self.obs("watch", 1, location="Woods", location_at=500),
                self.obs("phone", 2, location="home", location_at=999),
            ],
            1000,
        )
        self.assertEqual(result.selected, "phone")

    def test_known_worn_watch_without_position_blocks_phone_home(self):
        result = Resolver(settle=0).update(
            [
                self.obs("watch", 1, worn=True),
                self.obs("phone", 2, room="Kitchen", room_at=999),
            ],
            1000,
        )
        self.assertIsNone(result.location)
        self.assertIn("worn", result.reason)

    def test_fresh_away_suppresses_old_room(self):
        result = Resolver(settle=0).update(
            [
                self.obs(
                    "watch",
                    1,
                    location="Woods",
                    location_at=999,
                    room="Bedroom",
                    room_at=990,
                )
            ],
            1000,
        )
        self.assertEqual((result.location, result.room), ("Woods", None))

    def test_newer_room_beats_older_home_or_away_fix(self):
        result = Resolver(settle=0).update(
            [
                self.obs(
                    "watch",
                    1,
                    location="Woods",
                    location_at=990,
                    room="Study",
                    room_at=999,
                )
            ],
            1000,
        )
        self.assertEqual((result.location, result.room), ("home", "Study"))

    def test_expiry_and_restart_do_not_restore_location(self):
        resolver = Resolver(settle=0)
        obs = [self.obs("tag", 1, room="Studio", room_at=999)]
        self.assertEqual(resolver.update(obs, 1000).room, "Studio")
        self.assertIsNone(resolver.update(obs, 1060).location)
        self.assertIsNone(Resolver().result.location)

    def test_settling_does_not_flicker_or_preserve_expired_evidence(self):
        resolver = Resolver(settle=15)
        a = [self.obs("watch", 1, room="Studio", room_at=999)]
        self.assertIsNone(resolver.update(a, 1000).location)
        self.assertEqual(resolver.update(a, 1015).room, "Studio")
        b = [self.obs("watch", 1, room="Hall", room_at=1020)]
        self.assertEqual(resolver.update(b, 1020).room, "Studio")
        self.assertEqual(resolver.update(b, 1035).room, "Hall")
        self.assertIsNone(resolver.update(b, 1081).room)

    def test_future_and_missing_evidence_are_rejected(self):
        for at in [None, 1100, float("nan")]:
            self.assertIsNone(
                Resolver(settle=0)
                .update([self.obs("tag", 1, location="home", location_at=at)], 1000)
                .location
            )

    def test_worn_evidence_beats_configured_preference(self):
        result = Resolver(settle=0).update(
            [
                self.obs("phone", 1, room="Kitchen", room_at=999),
                self.obs("watch", 2, worn=True, room="Library", room_at=999),
            ],
            1000,
        )
        self.assertEqual(result.selected, "watch")

    def test_second_household_arbitrary_device_and_area_names(self):
        result = Resolver(settle=0).update(
            [self.obs("pendant", 8, room="Workshop East", room_at=999)], 1000
        )
        self.assertEqual((result.location, result.room), ("home", "Workshop East"))


if __name__ == "__main__":
    unittest.main()
