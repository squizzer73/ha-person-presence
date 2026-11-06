import unittest

from test_engine import load

engine = load("engine")
places = load("places")
where = load("whereabouts")


class Whereabouts(unittest.TestCase):
    def test_values_context_and_automation_identity(self):
        catalog = places.PlaceCatalog(
            {"library": "Library"},
            [
                places.Zone("zone.home", "Home", 0, 0, 100),
                places.Zone("zone.woods", "Woods", 1, 1, 100),
            ],
        )
        cases = [
            (
                engine.Result(
                    location="home",
                    room="Library",
                    selected="phone",
                    area_id="library",
                    zone_id="zone.home",
                    context="room",
                ),
                "Library",
                "room",
                "home",
            ),
            (engine.Result(location="home", context="home"), "Home", "home", "home"),
            (
                engine.Result(location="Woods", zone_id="zone.woods", context="zone"),
                "Woods",
                "zone",
                "away",
            ),
            (
                engine.Result(location="not_home", context="away"),
                "Away",
                "away",
                "away",
            ),
            (engine.Result(), None, "unknown", "unknown"),
        ]
        for result, value, context, presence in cases:
            projected = where.project_whereabouts(
                result, catalog, "person.alex", {"phone": "Phone"}
            )
            self.assertEqual(
                (
                    projected.value,
                    projected.attributes["context"],
                    projected.attributes["presence"],
                ),
                (value, context, presence),
            )
            self.assertNotIn("latitude", projected.attributes)
            self.assertNotIn("evidence", projected.attributes)

    def test_deleted_zone_does_not_retain_place_label(self):
        result = engine.Result(
            location="Old place", zone_id="zone.deleted", context="zone"
        )
        projected = where.project_whereabouts(
            result, places.PlaceCatalog(), "person.alex", {}
        )
        self.assertEqual(projected.value, "Away")
        self.assertIsNone(projected.attributes["zone_id"])

    def test_identically_named_places_remain_distinguishable(self):
        catalog = places.PlaceCatalog(
            {"woods": "Woods"}, [places.Zone("zone.woods", "Woods", 0, 0, 10)]
        )
        room = where.project_whereabouts(
            engine.Result(
                location="home", room="Woods", area_id="woods", context="room"
            ),
            catalog,
            "person.alex",
            {},
        )
        zone = where.project_whereabouts(
            engine.Result(location="Woods", zone_id="zone.woods", context="zone"),
            catalog,
            "person.alex",
            {},
        )
        self.assertEqual(room.value, zone.value)
        self.assertNotEqual(room.attributes["context"], zone.attributes["context"])
