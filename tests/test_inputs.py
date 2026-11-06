import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from test_engine import load

inputs = load("inputs")


def state(value, at=999, **attrs):
    return SimpleNamespace(
        state=value,
        attributes=attrs,
        last_reported=datetime.fromtimestamp(at, UTC),
        last_updated=datetime.fromtimestamp(at, UTC),
    )


class Inputs(unittest.TestCase):
    def config(self, **kw):
        return dict(
            key="wearable",
            name="Wearable",
            priority=1,
            wearable=True,
            tracker="device_tracker.wearable",
            **kw,
        )

    def test_republished_icloud_fix_uses_actual_observation(self):
        states = {
            "device_tracker.wearable": state(
                "home",
                integration="icloud3",
                located="1970-01-01 00:05:00",
                latitude=1,
                longitude=2,
                gps_accuracy=10,
            )
        }
        result = inputs.observe(self.config(), states.get, 1000, "UTC", 600, 100)
        self.assertEqual(result.location_at, 300)

    def test_missing_or_bad_icloud_timestamp_never_falls_back(self):
        for located in [None, "bad", "13:01:09"]:
            result = inputs.observe(
                self.config(),
                {
                    "device_tracker.wearable": state(
                        "home",
                        integration="icloud3",
                        located=located,
                        latitude=1,
                        longitude=2,
                    )
                }.get,
                1000,
                "UTC",
                600,
                100,
            )
            self.assertIsNone(result.location)

    def test_charging_watch_excluded_and_unworn_watch_excluded(self):
        for name, value, want in [
            ("charging", "Charging", "charging"),
            ("worn", "off", "not worn"),
        ]:
            config = self.config(**{name: "sensor.signal"})
            result = inputs.observe(
                config, {"sensor.signal": state(value)}.get, 1000, "UTC", 600, 100
            )
            self.assertEqual(result.excluded, want)

    def test_stale_worn_or_charging_not_used(self):
        result = inputs.observe(
            self.config(charging="sensor.charge", worn="binary_sensor.worn"),
            {
                "sensor.charge": state("Charging", at=1),
                "binary_sensor.worn": state("on", at=1),
            }.get,
            1000,
            "UTC",
            600,
            100,
        )
        self.assertEqual(result.excluded, "wearing status unconfirmed")
        self.assertIsNone(result.worn)

    def test_unknown_worn_never_means_not_worn(self):
        result = inputs.observe(
            self.config(worn="binary_sensor.worn"),
            {"binary_sensor.worn": state("unknown")}.get,
            1000,
            "UTC",
            600,
            100,
        )
        self.assertIsNone(result.worn)
        self.assertEqual(result.excluded, "wearing status unconfirmed")

    def test_fully_charged_watch_is_still_on_charger(self):
        for value in ["Charged", "Full", "Charging"]:
            result = inputs.observe(
                self.config(charging="sensor.charge"),
                {"sensor.charge": state(value)}.get,
                1000,
                "UTC",
                600,
                100,
            )
            self.assertEqual(result.excluded, "charging")

    def test_phone_charging_does_not_exclude_by_default(self):
        config = {
            "key": "phone",
            "name": "Phone",
            "priority": 2,
            "wearable": False,
            "charging": "sensor.charge",
        }
        self.assertIsNone(
            inputs.observe(
                config, {"sensor.charge": state("Charging")}.get, 1000, "UTC", 600, 100
            ).excluded
        )
        config["exclude_charging"] = True
        self.assertEqual(
            inputs.observe(
                config, {"sensor.charge": state("Charging")}.get, 1000, "UTC", 600, 100
            ).excluded,
            "charging",
        )

    def test_room_requires_local_presence_when_configured(self):
        config = self.config(room="sensor.area", local_tracker="device_tracker.ble")
        for present, want in [
            ("not_home", None),
            ("unknown", None),
            ("home", "Library"),
        ]:
            result = inputs.observe(
                config,
                {
                    "sensor.area": state("Library"),
                    "device_tracker.ble": state(present),
                }.get,
                1000,
                "UTC",
                600,
                100,
            )
            self.assertEqual(result.room, want)

    def test_room_actual_last_seen_beats_republication(self):
        result = inputs.observe(
            self.config(room="sensor.area"),
            {
                "sensor.area": state("Library", last_seen="1970-01-01T00:05:00+00:00")
            }.get,
            1000,
            "UTC",
            600,
            100,
        )
        self.assertEqual(result.room_at, 300)

    def test_invalid_coordinates_accuracy_or_restored_state_rejected(self):
        for attrs in [
            {"latitude": 100, "longitude": 1},
            {"latitude": 1, "longitude": 2, "gps_accuracy": 999},
            {"latitude": 1, "longitude": 2, "restored": True},
            {"latitude": float("nan"), "longitude": 2},
        ]:
            result = inputs.observe(
                self.config(),
                {"device_tracker.wearable": state("home", **attrs)}.get,
                1000,
                "UTC",
                600,
                100,
            )
            self.assertIsNone(result.location)

    def test_local_timezone_and_explicit_timestamp_entity(self):
        config = self.config(
            timestamp_entity="sensor.fix", timestamp_attribute="last_located"
        )
        states = {
            "device_tracker.wearable": state("home", latitude=1, longitude=2),
            "sensor.fix": state("12:00", last_located="2026-07-01 12:00:00"),
        }
        result = inputs.observe(
            config, states.get, 2000000000, "Europe/London", 600, 100
        )
        self.assertEqual(result.location_at, 1782903600)

    def test_stale_eligibility_cannot_make_charging_watch_anchor_home(self):
        from test_engine import Resolver

        states = {
            "sensor.charge": state("Charging", at=1000),
            "binary_sensor.worn": state("off", at=1000),
            "sensor.area": state("Bedroom", at=1601),
        }
        obs = inputs.observe(
            self.config(
                charging="sensor.charge", worn="binary_sensor.worn", room="sensor.area"
            ),
            states.get,
            1601,
            "UTC",
            600,
            100,
        )
        result = Resolver(settle=0).update([obs], 1601)
        self.assertIsNone(result.location)
        self.assertIsNone(obs.worn)

    def test_ambiguous_and_nonexistent_local_times_rejected(self):
        self.assertIsNone(inputs.timestamp("2026-10-25 01:30:00", "Europe/London"))
        self.assertIsNone(inputs.timestamp("2026-03-29 01:30:00", "Europe/London"))
        self.assertIsNotNone(
            inputs.timestamp("2026-10-25T01:30:00+00:00", "Europe/London")
        )

    def test_old_contact_with_new_publication_does_not_renew_eligibility(self):
        config = self.config(charging="sensor.charging")
        result = inputs.observe(
            config,
            {
                "sensor.charging": state(
                    "NotCharging", at=1000, last_contact="1970-01-01T00:00:01+00:00"
                )
            }.get,
            1000,
            "UTC",
            600,
            100,
        )
        self.assertEqual(result.excluded, "charging status unconfirmed")

    def test_configuration_rejects_duplicates_bad_timing_and_empty_sources(self):
        valid = {"name": "Alex", "person": "person.alex", "devices": [self.config()]}
        self.assertEqual(inputs.validate_config(valid)["name"], "Alex")
        for changes in [
            {"devices": []},
            {"gps_age": 0},
            {"devices": [self.config(), self.config()]},
            {"devices": [{"key": "x", "name": "X", "priority": 1}]},
            {"devices": [dict(self.config(), priority=-1)]},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                inputs.validate_config(dict(valid, **changes))


if __name__ == "__main__":
    unittest.main()


class RoomValidation(unittest.TestCase):
    def test_numeric_and_binary_room_sources_do_not_imply_home(self):
        for entity, value, attrs in [
            ("sensor.temperature", "21.5", {"unit_of_measurement": "°C"}),
            ("sensor.numeric", "75", {}),
            ("binary_sensor.contact", "on", {}),
        ]:
            result = inputs.observe(
                {"key": "phone", "name": "Phone", "priority": 1, "room": entity},
                {entity: state(value, **attrs)}.get,
                1000,
                "UTC",
                600,
                100,
            )
            self.assertIsNone(result.room)
            self.assertIn("unsupported_room_source", result.reason_codes)

    def test_report_only_bermuda_requires_matching_positive_guard(self):
        from test_engine import load

        sources = load("sources")
        from datetime import UTC, datetime

        rows = [
            sources.SourceSnapshot(
                "sensor.phone_area",
                "Library",
                {},
                datetime.fromtimestamp(999, UTC),
                "bermuda",
                "phone",
            ),
            sources.SourceSnapshot(
                "device_tracker.phone_local",
                "not_home",
                {"tracking_type": "connection"},
                datetime.fromtimestamp(999, UTC),
                "bermuda",
                "phone",
            ),
        ]
        catalog = sources.SourceCatalog(rows)
        result = inputs.observe(
            {
                "key": "phone",
                "name": "Phone",
                "priority": 1,
                "room": "sensor.phone_area",
            },
            catalog.get_state,
            1000,
            "UTC",
            600,
            100,
            catalog=catalog,
        )
        self.assertIsNone(result.room)
        self.assertIn("local_guard_away", result.reason_codes)
