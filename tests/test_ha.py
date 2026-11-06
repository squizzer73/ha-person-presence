"""Run configuration flows and entity lifecycle inside real isolated HA Core."""

import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from homeassistant import loader
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers import frame
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

SOURCE = Path(__file__).parents[1] / "custom_components/person_presence"


class HomeAssistantTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="person-presence-ha-")
        custom = Path(self.tmp.name) / "custom_components"
        custom.mkdir()
        shutil.copytree(
            SOURCE,
            custom / "person_presence",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        for module_name in list(sys.modules):
            if module_name == "custom_components" or module_name.startswith(
                "custom_components.person_presence"
            ):
                sys.modules.pop(module_name, None)
        self.hass = HomeAssistant(self.tmp.name)
        await self.hass.config.async_set_time_zone("Europe/London")
        loader.async_setup(self.hass)
        frame.async_setup(self.hass)
        await fr.async_load(self.hass)
        await ar.async_load(self.hass)
        dr.async_setup(self.hass)
        await dr.async_load(self.hass)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await er.async_load(self.hass)
        await ir.async_load(self.hass)
        await async_setup_component(self.hass, "homeassistant", {})
        await async_setup_component(self.hass, "persistent_notification", {})
        await self.hass.async_start()
        self.hass.states.async_set(
            "person.alex", "home", {"device_trackers": [], "friendly_name": "Alex"}
        )
        self.hass.states.async_set("sensor.band_area", "Library")
        self.hass.states.async_set("binary_sensor.band_worn", "on")
        self.hass.states.async_set("sensor.band_charge", "NotCharging")

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)
        self.tmp.cleanup()

    async def flow(self, person="person.alex"):
        result = await self.hass.config_entries.flow.async_init(
            "person_presence", context={"source": "user"}
        )
        self.assertEqual(result["type"], "form", result)
        return await self.hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"person": person, "name": "Alex comparison"},
        )

    async def configure_device(self, manager, form, payload):
        kind = "watch" if payload.get("wearable") else "phone"
        form = await manager.async_configure(
            form["flow_id"], {"name": payload["name"], "device_type": kind}
        )
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "manual_sources"}
        )
        source = {
            k: v
            for k, v in payload.items()
            if k
            in (
                "tracker",
                "room",
                "local_tracker",
                "charging",
                "worn",
                "timestamp_entity",
                "timestamp_attribute",
            )
        }
        form = await manager.async_configure(
            form["flow_id"], {**source, "manual_sources": True}
        )
        if form.get("step_id") != "rules":
            return form
        return await manager.async_configure(
            form["flow_id"],
            {
                k: payload.get(k, False)
                for k in ("priority", "wearable", "exclude_charging")
            },
        )

    async def create(self, person="person.alex"):
        result = await self.flow(person)
        self.assertEqual(result["step_id"], "device")
        result = await self.configure_device(
            self.hass.config_entries.flow,
            result,
            {
                "name": "Band",
                "priority": 1,
                "wearable": True,
                "room": "sensor.band_area",
                "worn": "binary_sensor.band_worn",
                "charging": "sensor.band_charge",
            },
        )
        self.assertEqual(result["type"], "menu", result)
        result = await self.hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "settings"}
        )
        result = await self.hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": "Alex comparison", "settle": 0}
        )
        result = await self.hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "finish"}
        )
        self.assertEqual(result["step_id"], "preview", result)
        result = await self.hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "save"}
        )
        self.assertEqual(result["type"], "create_entry", result)
        await self.hass.async_block_till_done()
        return result["result"]

    async def test_flow_runtime_charging_and_unload_leave_person_untouched(self):
        original = self.hass.states.get("person.alex")
        entry = await self.create()
        self.assertEqual(entry.state.value, "loaded")
        runtime = entry.runtime_data
        self.assertEqual(runtime.data.room, "Library")
        registry = er.async_get(self.hass)
        entities = er.async_entries_for_config_entry(registry, entry.entry_id)
        self.assertEqual(len(entities), 8)
        tracker = next(e for e in entities if e.domain == "device_tracker")
        self.assertIsNotNone(tracker.disabled_by)
        self.assertIsNone(self.hass.states.get(tracker.entity_id))
        self.hass.states.async_set("sensor.band_charge", "Charging")
        await self.hass.async_block_till_done()
        self.assertIsNone(runtime.data.location)
        self.assertIs(self.hass.states.get("person.alex"), original)
        self.assertTrue(await self.hass.config_entries.async_unload(entry.entry_id))
        self.assertFalse(runtime.running)
        self.hass.states.async_set("sensor.band_charge", "NotCharging")
        await self.hass.async_block_till_done()
        self.assertIsNone(runtime.data.location)

    async def test_all_outputs_share_one_device_and_short_names(self):
        entry = await self.create()
        entities = er.async_entries_for_config_entry(
            er.async_get(self.hass), entry.entry_id
        )
        device_ids = {e.device_id for e in entities}
        self.assertNotIn(None, device_ids)
        self.assertEqual(len(device_ids), 1)
        device = dr.async_get(self.hass).async_get(next(iter(device_ids)))
        self.assertEqual(device.name, "Alex comparison")
        self.assertIn(("person_presence", entry.entry_id), device.identifiers)
        self.assertEqual(
            {e.original_name for e in entities},
            {
                "Whereabouts",
                "Location",
                "Room",
                "Selected device",
                "Decision",
                "Tracker",
                "Last known whereabouts",
                "Last observation time",
            },
        )
        self.assertEqual(len({e.entity_id for e in entities}), 8)

    async def test_grouping_preserves_existing_entity_ids_and_entry_settings(self):
        entry = await self.create()
        registry = er.async_get(self.hass)
        await self.hass.config_entries.async_unload(entry.entry_id)
        entities = er.async_entries_for_config_entry(registry, entry.entry_id)
        location = next(e for e in entities if e.unique_id.endswith("_location"))
        registry.async_update_entity(
            location.entity_id,
            new_entity_id="sensor.custom_alex_position",
            name="My location label",
        )
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            registry.async_update_entity(entity.entity_id, device_id=None)
        before = {
            e.unique_id: (e.entity_id, e.name, e.disabled_by)
            for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        data, options = dict(entry.data), dict(entry.options)
        self.assertTrue(await self.hass.config_entries.async_setup(entry.entry_id))
        await self.hass.async_block_till_done()
        after = er.async_entries_for_config_entry(registry, entry.entry_id)
        self.assertEqual(
            {e.unique_id: (e.entity_id, e.name, e.disabled_by) for e in after}, before
        )
        self.assertTrue(all(e.device_id for e in after))
        self.assertEqual(dict(entry.data), data)
        self.assertEqual(dict(entry.options), options)

    async def test_each_person_has_an_independent_device(self):
        first = await self.create()
        self.hass.states.async_set("person.robin", "home", {"device_trackers": []})
        second = await self.create("person.robin")
        registry = er.async_get(self.hass)
        first_devices = {
            e.device_id
            for e in er.async_entries_for_config_entry(registry, first.entry_id)
        }
        second_devices = {
            e.device_id
            for e in er.async_entries_for_config_entry(registry, second.entry_id)
        }
        self.assertEqual(len(first_devices), 1)
        self.assertEqual(len(second_devices), 1)
        self.assertNotIn(None, first_devices | second_devices)
        self.assertTrue(first_devices.isdisjoint(second_devices))

    async def test_six_legacy_people_upgrade_additively(self):
        from test_upgrade import exercise_legacy_upgrade

        await exercise_legacy_upgrade(self)

    async def test_last_known_is_separate_and_cleared_on_reload(self):
        entry = await self.create()
        runtime = entry.runtime_data
        self.assertEqual(runtime.last_known_whereabouts, "Library")
        self.hass.states.async_set("sensor.band_charge", "Charging")
        await self.hass.async_block_till_done()
        self.assertIsNone(runtime.whereabouts().value)
        self.assertEqual(runtime.last_known_whereabouts, "Library")
        await self.hass.config_entries.async_reload(entry.entry_id)
        await self.hass.async_block_till_done()
        self.assertIsNone(entry.runtime_data.last_known_whereabouts)

    async def test_real_recorder_does_not_store_heartbeats(self):
        from test_recorder import exercise_recorder

        await exercise_recorder(self)

    async def test_guided_setup_previews_before_creating(self):
        from test_config_flow import exercise_guided_flow

        await exercise_guided_flow(self)

    async def test_missing_source_repairs_clear_on_recovery(self):
        from test_repairs import exercise_repairs

        await exercise_repairs(self)

    async def test_options_preserve_unknown_fields_and_reorder_devices(self):
        from test_config_flow import exercise_options_compatibility

        await exercise_options_compatibility(self)

    async def test_filtered_edit_preserves_advanced_timestamp_override(self):
        from test_config_flow import exercise_timestamp_override_edit

        await exercise_timestamp_override_edit(self)

    async def test_enabled_observation_time_updates_without_primary_churn(self):
        self.hass.states.async_set(
            "sensor.band_area",
            "Library",
            {"last_seen": (dt_util.utcnow() - timedelta(seconds=5)).isoformat()},
        )
        entry = await self.create()
        registry = er.async_get(self.hass)
        ours = er.async_entries_for_config_entry(registry, entry.entry_id)
        clock = next(e for e in ours if e.unique_id.endswith("_last_observation_time"))
        primary = next(
            e
            for e in ours
            if e.unique_id.endswith("_whereabouts")
            and not e.unique_id.endswith("_last_known_whereabouts")
        )
        registry.async_update_entity(clock.entity_id, disabled_by=None)
        await self.hass.config_entries.async_reload(entry.entry_id)
        await self.hass.async_block_till_done()
        before = self.hass.states.get(clock.entity_id).state
        primary_before = self.hass.states.get(primary.entity_id).last_updated
        self.hass.states.async_set(
            "sensor.band_area", "Library", {"last_seen": dt_util.utcnow().isoformat()}
        )
        await self.hass.async_block_till_done()
        self.assertNotEqual(self.hass.states.get(clock.entity_id).state, before)
        self.assertEqual(
            self.hass.states.get(primary.entity_id).last_updated, primary_before
        )

    async def test_documented_examples_handle_unknown_and_place_identity(self):
        from test_examples import exercise_documented_templates

        await exercise_documented_templates(self)

    async def test_duplicate_person_aborts(self):
        await self.create()
        result = await self.flow()
        self.assertEqual(result["type"], "abort", result)
        self.assertEqual(result["reason"], "already_configured")

    async def test_options_edit_remove_and_reload(self):
        entry = await self.create()
        result = await self.hass.config_entries.options.async_init(entry.entry_id)
        self.assertEqual(result["type"], "menu", result)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "edit"}
        )
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"device": entry.data["devices"][0]["key"]}
        )
        result = await self.configure_device(
            self.hass.config_entries.options,
            result,
            {
                "name": "Band revised",
                "priority": 4,
                "wearable": True,
                "room": "sensor.band_area",
            },
        )
        self.assertEqual(result["type"], "menu", result)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "finish"}
        )
        self.assertEqual(result["step_id"], "preview", result)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "save"}
        )
        await self.hass.async_block_till_done()
        self.assertEqual(entry.options["devices"][0]["name"], "Band revised")
        self.assertEqual(entry.runtime_data.data.room, "Library")
        result = await self.hass.config_entries.options.async_init(entry.entry_id)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "remove"}
        )
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"device": entry.options["devices"][0]["key"]}
        )
        self.assertEqual(result["errors"], {"base": "last_device"})

    async def test_timer_expires_room_without_source_event(self):
        entry = await self.create()
        runtime = entry.runtime_data
        # Periodic callback uses actual observation age, including when HA receives no updates.
        old = dt_util.utcnow() - timedelta(seconds=61)
        self.hass.states.async_set(
            "sensor.band_area", "Library", {"last_seen": old.isoformat()}
        )
        await self.hass.async_block_till_done()
        self.assertIsNone(runtime.data.location)
        self.hass.states.async_set(
            "sensor.band_area", "Library", {"last_seen": dt_util.utcnow().isoformat()}
        )
        await self.hass.async_block_till_done()
        self.assertEqual(runtime.data.room, "Library")
        await runtime.async_refresh_at(dt_util.utcnow() + timedelta(seconds=61))
        self.assertIsNone(runtime.data.location)

    async def test_enabled_tracker_preserves_unknown_and_named_zones(self):
        entry = await self.create()
        registry = er.async_get(self.hass)
        tracker = next(
            e
            for e in er.async_entries_for_config_entry(registry, entry.entry_id)
            if e.domain == "device_tracker"
        )
        registry.async_update_entity(tracker.entity_id, disabled_by=None)
        await self.hass.config_entries.async_reload(entry.entry_id)
        await self.hass.async_block_till_done()
        self.assertEqual(self.hass.states.get(tracker.entity_id).state, "home")
        self.hass.states.async_set("sensor.band_charge", "Charging")
        await self.hass.async_block_till_done()
        self.assertEqual(self.hass.states.get(tracker.entity_id).state, "unknown")
        self.hass.states.async_set("sensor.band_charge", "NotCharging")
        self.hass.states.async_set(
            "zone.woods",
            "0",
            {
                "friendly_name": "Woods",
                "latitude": 20,
                "longitude": 30,
                "radius": 100,
                "passive": False,
            },
        )
        self.hass.states.async_set(
            "device_tracker.band_gps",
            "Woods",
            {
                "latitude": 20,
                "longitude": 30,
                "gps_accuracy": 10,
                "located": dt_util.utcnow().isoformat(),
            },
        )
        result = await self.hass.config_entries.options.async_init(entry.entry_id)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "edit"}
        )
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"device": entry.data["devices"][0]["key"]}
        )
        result = await self.configure_device(
            self.hass.config_entries.options,
            result,
            {
                "name": "Band",
                "priority": 1,
                "tracker": "device_tracker.band_gps",
                "room": "sensor.band_area",
            },
        )
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "finish"}
        )
        self.assertEqual(result["step_id"], "preview", result)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "save"}
        )
        await self.hass.async_block_till_done()
        self.assertEqual(self.hass.states.get(tracker.entity_id).state, "Woods")
        self.assertEqual(
            self.hass.states.get(tracker.entity_id).attributes["in_zones"],
            ["zone.woods"],
        )
        self.assertIsNone(entry.runtime_data.data.room)

    async def test_decision_uses_device_label_and_source_loops_rejected(self):
        entry = await self.create()
        registry = er.async_get(self.hass)
        decision = next(
            e
            for e in er.async_entries_for_config_entry(registry, entry.entry_id)
            if e.unique_id.endswith("_reason")
        )
        self.assertIn("Band", self.hass.states.get(decision.entity_id).state)
        result = await self.hass.config_entries.options.async_init(entry.entry_id)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add"}
        )
        result = await self.configure_device(
            self.hass.config_entries.options,
            result,
            {"name": "Loop", "priority": 2, "room": decision.entity_id},
        )
        self.assertEqual(result["errors"], {"base": "self_reference"})

    async def test_two_missing_sources_can_be_repaired_sequentially(self):
        entry = await self.create()
        self.hass.states.async_set("sensor.phone_area", "Library")
        result = await self.hass.config_entries.options.async_init(entry.entry_id)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add"}
        )
        result = await self.configure_device(
            self.hass.config_entries.options,
            result,
            {"name": "Phone", "priority": 2, "room": "sensor.phone_area"},
        )
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "finish"}
        )
        self.assertEqual(result["step_id"], "preview", result)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "save"}
        )
        await self.hass.async_block_till_done()
        self.hass.states.async_remove("sensor.band_area")
        self.hass.states.async_remove("sensor.phone_area")
        self.hass.states.async_set("sensor.new_band_area", "Study")
        self.hass.states.async_set("sensor.new_phone_area", "Kitchen")
        result = await self.hass.config_entries.options.async_init(entry.entry_id)
        for device, room in zip(
            entry.options["devices"],
            ["sensor.new_band_area", "sensor.new_phone_area"],
            strict=True,
        ):
            result = await self.hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step_id": "edit"}
            )
            result = await self.hass.config_entries.options.async_configure(
                result["flow_id"], {"device": device["key"]}
            )
            result = await self.configure_device(
                self.hass.config_entries.options,
                result,
                {"name": device["name"], "priority": device["priority"], "room": room},
            )
            self.assertEqual(result["type"], "menu", result)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "finish"}
        )
        self.assertEqual(result["step_id"], "preview", result)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "save"}
        )
        await self.hass.async_block_till_done()
        self.assertEqual(entry.runtime_data.data.room, "Study")

    async def test_invalid_source_is_form_error(self):
        result = await self.flow()
        result = await self.configure_device(
            self.hass.config_entries.flow,
            result,
            {"name": "Bad", "priority": 1, "room": "sensor.missing"},
        )
        self.assertEqual(result["type"], "form", result)
        self.assertEqual(result["errors"], {"base": "source_missing"})


if __name__ == "__main__":
    unittest.main()
