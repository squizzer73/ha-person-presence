import json
import unittest

from test_engine import load

module = load("diagnostics")


class Diagnostics(unittest.TestCase):
    def test_export_allowlist_excludes_nested_secrets_and_names(self):
        config = {
            "person": "person.SECRET_PERSON",
            "name": "SECRET_NAME",
            "latitude": "SECRET_COORD",
            "devices": [
                {
                    "key": "SECRET_KEY",
                    "name": "SECRET_DEVICE",
                    "priority": 1,
                    "tracker": "device_tracker.SECRET_ENTITY",
                    "raw": {"token": "SECRET_TOKEN"},
                }
            ],
        }
        evidence = {
            "SECRET_KEY": {
                "reasons": ["selected", "SECRET_REASON"],
                "notes": ["SECRET_NOTE"],
                "gps_fresh": True,
                "mac": "SECRET_MAC",
                "latitude": "SECRET_LAT",
            }
        }
        result = module.redact_diagnostics(config, evidence)
        text = json.dumps(result)
        self.assertNotIn("SECRET", text)
        self.assertEqual(result["devices"][0]["alias"], "device_1")
        self.assertEqual(result["devices"][0]["sources"]["tracker"], "entity_1")
        self.assertEqual(result["devices"][0]["health"]["reasons"], ["selected"])

    def test_shared_source_aliases_are_consistent(self):
        config = {
            "devices": [
                {"key": "a", "tracker": "device_tracker.phone"},
                {"key": "b", "tracker": "device_tracker.phone"},
            ]
        }
        result = module.redact_diagnostics(config, {})
        self.assertEqual(
            result["devices"][0]["sources"], result["devices"][1]["sources"]
        )
