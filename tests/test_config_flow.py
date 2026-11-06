"""Guided native UI acceptance exercised from the real HA harness."""


async def exercise_guided_flow(test):
    manager = test.hass.config_entries.flow
    before = len(test.hass.config_entries.async_entries("person_presence"))
    form = await manager.async_init("person_presence", context={"source": "user"})
    form = await manager.async_configure(form["flow_id"], {"person": "person.alex"})
    test.assertEqual(form["step_id"], "device")
    form = await manager.async_configure(
        form["flow_id"], {"name": "Band", "device_type": "watch"}
    )
    test.assertEqual(form["step_id"], "source_mode")
    form = await manager.async_configure(
        form["flow_id"], {"next_step_id": "manual_sources"}
    )
    test.assertEqual(form["step_id"], "sources")
    form = await manager.async_configure(
        form["flow_id"],
        {
            "room": "sensor.band_area",
            "worn": "binary_sensor.band_worn",
            "manual_sources": True,
        },
    )
    test.assertEqual(form["step_id"], "rules")
    form = await manager.async_configure(
        form["flow_id"], {"priority": 1, "wearable": True, "exclude_charging": False}
    )
    test.assertEqual(form["type"], "menu")
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "finish"})
    test.assertEqual(form["step_id"], "preview")
    test.assertIn("Library", form["description_placeholders"]["summary"])
    test.assertEqual(
        len(test.hass.config_entries.async_entries("person_presence")), before
    )
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "menu"})
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "finish"})
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "save"})
    test.assertEqual(form["type"], "create_entry")
    await test.hass.async_block_till_done()
    test.assertEqual(form["result"].data["name"], "Alex Person Presence")


async def exercise_options_compatibility(test):
    from copy import deepcopy

    entry = await test.create()
    data = deepcopy(dict(entry.data))
    data["future_setting"] = {"keep": True}
    data["devices"][0]["future_field"] = "keep"
    test.hass.config_entries.async_update_entry(entry, data=data)
    await test.hass.config_entries.async_reload(entry.entry_id)
    await test.hass.async_block_till_done()
    manager = test.hass.config_entries.options
    form = await manager.async_init(entry.entry_id)
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "edit"})
    form = await manager.async_configure(
        form["flow_id"], {"device": data["devices"][0]["key"]}
    )
    form = await test.configure_device(
        manager,
        form,
        {"name": "Band revised", "priority": 7, "room": "sensor.band_area"},
    )
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "finish"})
    await manager.async_configure(form["flow_id"], {"next_step_id": "save"})
    await test.hass.async_block_till_done()
    test.assertEqual(entry.options["future_setting"], {"keep": True})
    test.assertEqual(entry.options["devices"][0]["future_field"], "keep")
    test.assertNotIn("charging", entry.options["devices"][0])
    test.hass.states.async_set("sensor.second_area", "Hall")
    form = await manager.async_init(entry.entry_id)
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "add"})
    form = await test.configure_device(
        manager, form, {"name": "Phone", "priority": 99, "room": "sensor.second_area"}
    )
    form = await manager.async_configure(
        form["flow_id"], {"next_step_id": "move_earlier"}
    )
    choices = next(iter(form["data_schema"].schema.values())).container
    key = next(key for key, label in choices.items() if label == "99: Phone")
    form = await manager.async_configure(form["flow_id"], {"device": key})
    form = await manager.async_configure(form["flow_id"], {"next_step_id": "finish"})
    await manager.async_configure(form["flow_id"], {"next_step_id": "save"})
    await test.hass.async_block_till_done()
    ordered = sorted(entry.options["devices"], key=lambda d: d["priority"])
    test.assertEqual([d["name"] for d in ordered], ["Phone", "Band revised"])
    test.assertEqual({d["priority"] for d in ordered}, {7, 99})


async def exercise_timestamp_override_edit(test):
    from copy import deepcopy

    entry = await test.create()
    data = deepcopy(dict(entry.data))
    data["devices"][0]["timestamp_attribute"] = "located"
    test.hass.config_entries.async_update_entry(entry, data=data)
    await test.hass.config_entries.async_reload(entry.entry_id)
    await test.hass.async_block_till_done()
    manager = test.hass.config_entries.options
    for mode, clear in [("sources", False), ("manual_sources", True)]:
        form = await manager.async_init(entry.entry_id)
        form = await manager.async_configure(form["flow_id"], {"next_step_id": "edit"})
        form = await manager.async_configure(
            form["flow_id"], {"device": data["devices"][0]["key"]}
        )
        form = await manager.async_configure(
            form["flow_id"], {"name": "Band renamed", "device_type": "watch"}
        )
        form = await manager.async_configure(form["flow_id"], {"next_step_id": mode})
        payload = {"room": "sensor.band_area", "manual_sources": clear}
        if clear:
            payload["timestamp_attribute"] = ""
        form = await manager.async_configure(form["flow_id"], payload)
        form = await manager.async_configure(
            form["flow_id"],
            {"priority": 1, "wearable": True, "exclude_charging": False},
        )
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "finish"}
        )
        await manager.async_configure(form["flow_id"], {"next_step_id": "save"})
        await test.hass.async_block_till_done()
        if clear:
            test.assertNotIn("timestamp_attribute", entry.options["devices"][0])
        else:
            test.assertEqual(
                entry.options["devices"][0]["timestamp_attribute"], "located"
            )
