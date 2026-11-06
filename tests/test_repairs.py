from homeassistant.helpers import issue_registry as ir


async def exercise_repairs(test):
    entry = await test.create()
    registry = ir.async_get(test.hass)
    key = ("person_presence", entry.entry_id + "_missing_sources")
    test.assertNotIn(key, registry.issues)
    test.hass.states.async_remove("sensor.band_area")
    await test.hass.async_block_till_done()
    test.assertIn(key, registry.issues)
    test.hass.states.async_set("sensor.band_area", "Library")
    await test.hass.async_block_till_done()
    test.assertNotIn(key, registry.issues)
    test.hass.states.async_set("sensor.band_area", "unknown")
    await test.hass.async_block_till_done()
    test.assertNotIn(key, registry.issues)
