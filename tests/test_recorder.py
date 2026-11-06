"""Actual SQLite recorder assertions, called from the isolated HA harness."""

import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from homeassistant.components.recorder import get_instance
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util


async def exercise_recorder(test):
    from homeassistant.helpers import recorder as recorder_helper

    recorder_helper.async_initialize_recorder(test.hass)
    db = Path(test.tmp.name) / "history.sqlite"
    test.assertTrue(
        await async_setup_component(
            test.hass,
            "recorder",
            {"recorder": {"db_url": "sqlite:///" + str(db), "commit_interval": 0}},
        )
    )
    entry = await test.create()
    recorded_ids = [
        e.entity_id
        for e in er.async_entries_for_config_entry(
            er.async_get(test.hass), entry.entry_id
        )
        if e.domain == "sensor" and e.disabled_by is None
    ]
    recorder = get_instance(test.hass)
    await recorder.async_block_till_done()

    def rows():
        with closing(sqlite3.connect(db)) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM states JOIN states_meta USING(metadata_id) WHERE states_meta.entity_id IN ("
                + ",".join("?" for _ in recorded_ids)
                + ")",
                recorded_ids,
            ).fetchone()[0]

    before = await test.hass.async_add_executor_job(rows)
    test.assertGreater(before, 0)
    for _ in range(10):
        test.hass.states.async_set("sensor.band_area", "Library", force_update=True)
        await entry.runtime_data.async_refresh_at(dt_util.utcnow())
    await test.hass.async_block_till_done()
    await recorder.async_block_till_done()
    test.assertEqual(await test.hass.async_add_executor_job(rows), before)
    test.hass.states.async_set("sensor.band_area", "Hall")
    await test.hass.async_block_till_done()
    await recorder.async_block_till_done()
    test.assertGreater(await test.hass.async_add_executor_job(rows), before)
    await entry.runtime_data.async_refresh_at(dt_util.utcnow() + timedelta(seconds=61))
    test.assertIsNone(entry.runtime_data.whereabouts().value)

    await test.hass.async_block_till_done()
    await recorder.async_block_till_done()
    stale_rows = await test.hass.async_add_executor_job(rows)
    for seconds in range(65, 90, 5):
        await entry.runtime_data.async_refresh_at(
            dt_util.utcnow() + timedelta(seconds=seconds)
        )
    await test.hass.async_block_till_done()
    await recorder.async_block_till_done()
    test.assertEqual(await test.hass.async_add_executor_job(rows), stale_rows)
