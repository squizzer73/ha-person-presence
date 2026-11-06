"""Selection explains every source and refuses contemporaneous contradictions."""

import unittest

from test_engine import Observation, Resolver


class Decisions(unittest.TestCase):
    def test_all_devices_explained_after_winner(self):
        result = Resolver(settle=0).update(
            [
                Observation("watch", 1, room="Library", room_at=990),
                Observation("phone", 2, room="Hall", room_at=990),
                Observation("tablet", 3, excluded="charging"),
            ],
            1000,
        )
        self.assertEqual(result.selected, "watch")
        self.assertEqual(set(result.evidence), {"watch", "phone", "tablet"})
        self.assertIn("selected", result.evidence["watch"]["reasons"])
        self.assertIn("lower_preference", result.evidence["phone"]["reasons"])
        self.assertIn("charging", result.evidence["tablet"]["reasons"])

    def test_equal_timestamp_away_and_room_is_unknown(self):
        result = Resolver(settle=0).update(
            [
                Observation(
                    "watch",
                    1,
                    location="Woods",
                    location_at=990,
                    room="Library",
                    room_at=990,
                )
            ],
            1000,
        )
        self.assertIsNone(result.location)
        self.assertIsNone(result.room)
        self.assertIn("conflicting_evidence", result.evidence["watch"]["reasons"])

    def test_equal_home_and_room_agree(self):
        result = Resolver(settle=0).update(
            [
                Observation(
                    "watch",
                    1,
                    location="home",
                    location_at=990,
                    room="Library",
                    room_at=990,
                )
            ],
            1000,
        )
        self.assertEqual(result.room, "Library")
        self.assertEqual(result.confidence, "corroborated")

    def test_worn_blocker_still_explains_lower_sources(self):
        result = Resolver(settle=0).update(
            [
                Observation("watch", 1, worn=True),
                Observation("phone", 2, location="home", location_at=999),
            ],
            1000,
        )
        self.assertIsNone(result.location)
        self.assertIn("phone", result.evidence)

    def test_identity_comes_from_selected_measurement(self):
        obs = Observation(
            "tag",
            1,
            room="Studio",
            room_at=990,
            area_id="studio",
            room_source_entity_id="sensor.tag_area",
        )
        result = Resolver(settle=0).update([obs], 1000)
        self.assertEqual(
            (result.context, result.area_id, result.source_entity_id),
            ("room", "studio", "sensor.tag_area"),
        )
