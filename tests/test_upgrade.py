"""Reusable fictional legacy-upgrade acceptance scenario for the real HA harness."""

from copy import deepcopy

from homeassistant.helpers import entity_registry as er


async def exercise_legacy_upgrade(test):
    registry = er.async_get(test.hass)
    for index, name in enumerate(("alex", "blair", "casey", "drew", "eden", "finley")):
        person = "person." + name
        test.hass.states.async_set(person, "home", {"device_trackers": []})
        entry = await test.create(person)
        await test.hass.config_entries.async_unload(entry.entry_id)
        data = deepcopy(dict(entry.data))
        data["future_option"] = {"keep": True}
        data["devices"][0]["priority"] = 7
        data["devices"][0]["future_device_option"] = "retained"
        data["room_age"] = 75
        test.hass.config_entries.async_update_entry(
            entry, data=data, options={"gps_age": 420, "future_root": "retained"}
        )
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity.unique_id.endswith(("_whereabouts", "_last_observation_time")):
                registry.async_remove(entity.entity_id)
            elif entity.unique_id.endswith("_reason"):
                registry.async_update_entity(
                    entity.entity_id, disabled_by=er.RegistryEntryDisabler.USER
                )
            elif entity.unique_id.endswith("_tracker"):
                registry.async_update_entity(entity.entity_id, disabled_by=None)
            elif entity.unique_id.endswith("_location"):
                registry.async_update_entity(
                    entity.entity_id,
                    new_entity_id=f"sensor.custom_{name}",
                    name="My custom label",
                )
        before = {
            e.unique_id: (e.entity_id, e.name, e.disabled_by, e.device_id)
            for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        original_data, original_options = (
            deepcopy(dict(entry.data)),
            deepcopy(dict(entry.options)),
        )
        test.assertTrue(await test.hass.config_entries.async_setup(entry.entry_id))
        await test.hass.async_block_till_done()
        after = er.async_entries_for_config_entry(registry, entry.entry_id)
        test.assertTrue(set(before).issubset({e.unique_id for e in after}))
        for entity in after:
            if entity.unique_id in before:
                test.assertEqual(
                    (
                        entity.entity_id,
                        entity.name,
                        entity.disabled_by,
                        entity.device_id,
                    ),
                    before[entity.unique_id],
                )
        test.assertEqual(len(after), len(before) + 3)
        test.assertIsNone(
            next(e for e in after if e.unique_id.endswith("_whereabouts")).disabled_by
        )
        test.assertEqual(dict(entry.data), original_data)
        test.assertEqual(dict(entry.options), original_options)
