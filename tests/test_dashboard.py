"""Historical display stays separate from accepted current presence."""

import unittest

from test_engine import load

history = load("history")


class HistoryValidation(unittest.TestCase):
    def test_restore_requires_original_time_person_and_source(self):
        record = {
            "value": "Library",
            "observed_at": 1000,
            "person_entity_id": "person.alex",
            "source_entity_id": "sensor.band_area",
        }
        self.assertIsNotNone(
            history.restore_record(record, "person.alex", {"sensor.band_area"}, 1100)
        )
        for changes in (
            {"observed_at": 1200},
            {"observed_at": float("nan")},
            {"observed_at": True},
            {"observed_at": 10**1000},
            {"person_entity_id": "person.blair"},
            {"source_entity_id": "sensor.removed"},
            {"source_entity_id": []},
            {"value": ""},
            {"value": "x" * 256},
        ):
            self.assertIsNone(
                history.restore_record(
                    {**record, **changes}, "person.alex", {"sensor.band_area"}, 1100
                )
            )
        for invalid in (None, [], "bad", {"value": "Library"}):
            self.assertIsNone(
                history.restore_record(
                    invalid, "person.alex", {"sensor.band_area"}, 1100
                )
            )


async def exercise_dashboard_lifecycle(test):
    from homeassistant.helpers import entity_registry as er
    from homeassistant.util import dt as dt_util

    entry = await test.create()
    runtime = entry.runtime_data
    entities = er.async_entries_for_config_entry(
        er.async_get(test.hass), entry.entry_id
    )
    dashboard = next(
        e for e in entities if e.unique_id.endswith("_dashboard_whereabouts")
    )
    test.assertIsNone(dashboard.disabled_by)
    test.assertEqual(test.hass.states.get(dashboard.entity_id).state, "Library")
    observed = runtime.dashboard_history["observed_at"]
    test.hass.states.async_set("sensor.band_area", "unknown")
    await test.hass.async_block_till_done()
    test.assertIsNone(runtime.whereabouts().value)
    stale = test.hass.states.get(dashboard.entity_id)
    test.assertEqual(stale.state, "Library (last known)")
    test.assertEqual(stale.attributes["freshness"], "last_known")
    test.assertEqual(
        stale.attributes["observed_at"],
        dt_util.utc_from_timestamp(observed).isoformat(),
    )
    test.assertNotIn("age_seconds", stale.attributes)
    test.assertTrue(await test.hass.config_entries.async_reload(entry.entry_id))
    await test.hass.async_block_till_done()
    import json
    from pathlib import Path

    persisted = json.loads(
        (
            Path(test.tmp.name)
            / ".storage"
            / f"person_presence.{entry.entry_id}.history"
        ).read_text()
    )["data"]
    test.assertEqual(persisted["observed_at"], observed)
    test.assertNotIn("latitude", persisted)
    restored = entry.runtime_data
    test.assertIsNone(restored.whereabouts().value)
    test.assertIsNone(restored.last_known_whereabouts)
    test.assertEqual(restored.dashboard_history["observed_at"], observed)
    test.assertEqual(
        test.hass.states.get(dashboard.entity_id).state, "Library (last known)"
    )
    test.hass.states.async_set("sensor.band_area", "Hall")
    await test.hass.async_block_till_done()
    test.assertEqual(test.hass.states.get(dashboard.entity_id).state, "Hall")
    test.assertEqual(
        test.hass.states.get(dashboard.entity_id).attributes["freshness"], "current"
    )
    store = restored.history_store
    await test.hass.config_entries.async_remove(entry.entry_id)
    test.assertIsNone(await store.async_load())


async def exercise_dashboard_remap(test):
    from copy import deepcopy

    entry = await test.create()
    await test.hass.config_entries.async_unload(entry.entry_id)
    data = deepcopy(dict(entry.data))
    data["devices"][0]["room"] = "sensor.other_area"
    test.hass.config_entries.async_update_entry(entry, data=data)
    test.assertTrue(await test.hass.config_entries.async_setup(entry.entry_id))
    await test.hass.async_block_till_done()
    test.assertIsNone(entry.runtime_data.dashboard_history)
