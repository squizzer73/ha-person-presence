"""Delayed charging reports do not extend wearing or location freshness."""

import unittest
from types import SimpleNamespace

from test_engine import load
from test_inputs import state

inputs = load("inputs")


class ChargingWindow(unittest.TestCase):
    def observe(
        self,
        *,
        age=1200,
        value="NotCharging",
        wearable=True,
        override=None,
        provider="icloud3",
        worn=None,
    ):
        device = {
            "key": "band",
            "name": "Band",
            "priority": 1,
            "wearable": wearable,
            "exclude_charging": True,
            "charging": "sensor.charge",
            "room": "sensor.area",
        }
        if override is not None:
            device["charging_age"] = override
        states = {
            "sensor.charge": state(value, at=1000),
            "sensor.area": state("Library", at=1000 + age),
        }
        if worn is not None:
            device["worn"] = "binary_sensor.worn"
            states["binary_sensor.worn"] = state(worn, at=1000)
        catalog = SimpleNamespace(
            snapshots={"sensor.charge": SimpleNamespace(platform=provider)}
        )
        return inputs.observe(
            device, states.get, 1000 + age, "UTC", 600, 100, catalog=catalog
        )

    def test_icloud_watch_accepts_twenty_minute_charging_report(self):
        result = self.observe()
        self.assertIsNone(result.excluded)
        self.assertIn("charging_status_grace", result.reason_codes)
        self.assertIsNone(result.worn)

    def test_explicit_charging_still_excludes_in_extended_window(self):
        for value in ["Charging", "Charged", "Full"]:
            self.assertEqual(self.observe(value=value).excluded, "charging")

    def test_provider_windows_are_bounded(self):
        self.assertIsNone(self.observe(age=1800).excluded)
        self.assertEqual(self.observe(age=1801).excluded, "charging status unconfirmed")
        self.assertIsNone(self.observe(age=7200, wearable=False).excluded)
        self.assertEqual(
            self.observe(age=9001, wearable=False).excluded,
            "charging status unconfirmed",
        )

    def test_unknown_provider_keeps_legacy_window_and_override_wins(self):
        self.assertEqual(
            self.observe(provider="generic").excluded, "charging status unconfirmed"
        )
        self.assertIsNone(self.observe(age=90, override=90).excluded)
        self.assertEqual(
            self.observe(age=91, override=90).excluded, "charging status unconfirmed"
        )

    def test_wearing_signal_is_not_extended_by_charging_grace(self):
        self.assertEqual(self.observe(worn="on").excluded, "wearing status unconfirmed")
        self.assertEqual(self.observe(age=30, worn="off").excluded, "not worn")

    def test_unavailable_or_unrecognized_state_does_not_become_eligible(self):
        for value in ["unknown", "unavailable", "unsupported"]:
            result = self.observe(value=value)
            self.assertEqual(result.excluded, "charging status unconfirmed")
            self.assertNotIn("charging_status_grace", result.reason_codes)

    def test_configuration_rejects_bad_charging_limits(self):
        base = {
            "name": "Alex",
            "person": "person.alex",
            "devices": [
                {
                    "key": "x",
                    "name": "Phone",
                    "priority": 1,
                    "tracker": "device_tracker.phone",
                }
            ],
        }
        for limit in [0, -1, 86401, True, float("nan"), "1800"]:
            with self.assertRaises(ValueError):
                inputs.validate_config(
                    {**base, "devices": [{**base["devices"][0], "charging_age": limit}]}
                )
