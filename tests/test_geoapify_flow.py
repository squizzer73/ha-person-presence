import unittest
from unittest.mock import AsyncMock, patch

import test_ha as harness

KEY = "FICTIONAL_GEOAPIFY_KEY_FOR_TESTS_ONLY"


class GeoapifyFlow(harness.HomeAssistantTests):
    async def configure_geo(self, entry, key=KEY):
        manager = self.hass.config_entries.options
        form = await manager.async_init(entry.entry_id)
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "geocoding"}
        )
        self.assertEqual(
            {str(k.schema) for k in form["data_schema"].schema},
            {"geocode", "configure_service"},
        )
        form = await manager.async_configure(
            form["flow_id"], {"geocode": True, "configure_service": True}
        )
        form = await manager.async_configure(form["flow_id"], {"provider": "geoapify"})
        self.assertNotIn(KEY, str(form))
        self.assertNotIn(
            "endpoint", {str(k.schema) for k in form["data_schema"].schema}
        )
        return await manager.async_configure(form["flow_id"], {"api_key": key})

    async def finish(self, form):
        manager = self.hass.config_entries.options
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "finish"}
        )
        self.assertNotIn(KEY, str(form))
        form = await manager.async_configure(form["flow_id"], {"next_step_id": "save"})
        await self.hass.async_block_till_done()
        return form

    async def test_geo_draft_skip_save_sharing_and_no_key_exposure(self):
        entry = await self.create()
        form = await self.configure_geo(entry)
        self.assertEqual(form["step_id"], "lookup_test")
        self.assertEqual(entry.runtime_data.lookup.options, {})
        from custom_components.person_presence import lookup_flow

        with patch.object(lookup_flow, "async_request", new=AsyncMock()) as request:
            form = await self.hass.config_entries.options.async_configure(
                form["flow_id"], {"next_step_id": "lookup_skip"}
            )
            await self.finish(form)
            request.assert_not_awaited()
        self.assertEqual(entry.runtime_data.lookup.options["api_key"], KEY)
        self.assertNotIn(KEY, str(dict(entry.options)))
        self.assertNotIn(KEY, str(dict(entry.data)))
        self.assertNotIn(KEY, str(self.hass.states.async_all()))
        self.hass.states.async_set("person.blair", "home", {"device_trackers": []})
        second = await self.create("person.blair")
        manager = self.hass.config_entries.options
        form = await manager.async_init(second.entry_id)
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "geocoding"}
        )
        form = await manager.async_configure(form["flow_id"], {"geocode": True})
        self.assertEqual(form["step_id"], "menu")
        await self.finish(form)
        self.assertIs(second.runtime_data.lookup, entry.runtime_data.lookup)
        self.assertNotIn(KEY, str(dict(second.options)))
        form = await self.configure_geo(second, "FICTIONAL_REPLACEMENT_KEY")
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "lookup_skip"}
        )
        await self.finish(form)
        self.assertEqual(
            entry.runtime_data.lookup.options["api_key"], "FICTIONAL_REPLACEMENT_KEY"
        )

    async def test_connection_test_is_explicit_synthetic_and_unsaved(self):
        entry = await self.create()
        form = await self.configure_geo(entry)
        from custom_components.person_presence import lookup_flow

        with patch.object(
            lookup_flow,
            "async_request",
            new=AsyncMock(return_value={"display_name": "Public example"}),
        ) as request:
            form = await self.hass.config_entries.options.async_configure(
                form["flow_id"], {"next_step_id": "lookup_test_connection"}
            )
            self.assertEqual(form["step_id"], "lookup_test_success")
            self.assertEqual(
                request.call_args.args[2], {"lat": "52.4794", "lon": "13.2139"}
            )
        self.assertEqual(entry.runtime_data.lookup.options, {})
        self.assertNotIn(KEY, str(form))

    async def test_blank_keeps_key_and_explicit_remove_disables_service(self):
        entry = await self.create()
        manager = self.hass.config_entries.options
        form = await self.configure_geo(entry)
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "lookup_skip"}
        )
        await self.finish(form)
        form = await manager.async_init(entry.entry_id)
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "geocoding"}
        )
        form = await manager.async_configure(
            form["flow_id"], {"geocode": True, "configure_service": True}
        )
        form = await manager.async_configure(form["flow_id"], {"provider": "geoapify"})
        self.assertNotIn(KEY, str(form))
        form = await manager.async_configure(form["flow_id"], {})
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "lookup_skip"}
        )
        await self.finish(form)
        self.assertEqual(entry.runtime_data.lookup.options["api_key"], KEY)
        form = await manager.async_init(entry.entry_id)
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "geocoding"}
        )
        form = await manager.async_configure(
            form["flow_id"], {"geocode": True, "configure_service": True}
        )
        form = await manager.async_configure(form["flow_id"], {"provider": "geoapify"})
        form = await manager.async_configure(form["flow_id"], {"remove_key": True})
        await self.finish(form)
        self.assertEqual(entry.runtime_data.lookup.options, {})
        self.assertFalse(entry.runtime_data.config["geocode"])

    async def test_connection_errors_are_actionable_without_leaking_key(self):
        entry = await self.create()
        form = await self.configure_geo(entry)
        from custom_components.person_presence import lookup_flow

        with patch.object(
            lookup_flow,
            "async_request",
            new=AsyncMock(side_effect=lookup_flow.ProviderError("invalid_auth")),
        ):
            form = await self.hass.config_entries.options.async_configure(
                form["flow_id"], {"next_step_id": "lookup_test_connection"}
            )
        self.assertEqual(form["step_id"], "lookup_test_error")
        self.assertIn("rejected", form["description_placeholders"]["reason"])
        self.assertNotIn(KEY, str(form))
        self.assertEqual(entry.runtime_data.lookup.options, {})

    async def test_revisit_preserves_unsaved_service_draft(self):
        entry = await self.create()
        manager = self.hass.config_entries.options
        form = await self.configure_geo(entry)
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "lookup_skip"}
        )
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "geocoding"}
        )
        form = await manager.async_configure(form["flow_id"], {"geocode": False})
        await self.finish(form)
        self.assertEqual(entry.runtime_data.lookup.options.get("api_key"), KEY)
        self.assertFalse(entry.runtime_data.config["geocode"])

    async def test_stale_lookup_form_requires_review_instead_of_silent_refresh(self):
        entry = await self.create()
        manager = self.hass.config_entries.options
        form = await manager.async_init(entry.entry_id)
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "geocoding"}
        )
        from custom_components.person_presence.lookup_settings import (
            async_save,
            async_snapshot,
        )
        from custom_components.person_presence.place_service import sync_lookup

        await async_save(
            self.hass,
            await async_snapshot(self.hass),
            {"provider": "geoapify", "api_key": "OTHER_WINDOW_KEY"},
        )
        sync_lookup(self.hass, entry.runtime_data.lookup)
        form = await manager.async_configure(form["flow_id"], {"geocode": True})
        # The visible form originally had no service. It must not silently consent to the new service.
        if form["step_id"] == "lookup_provider":
            form = await manager.async_configure(
                form["flow_id"], {"provider": "geoapify"}
            )
            form = await manager.async_configure(form["flow_id"], {"api_key": KEY})
            form = await manager.async_configure(
                form["flow_id"], {"next_step_id": "lookup_skip"}
            )
        form = await self.finish(form)
        self.assertEqual(form["type"], "menu")
        self.assertIn("lookup_changed", form["description_placeholders"]["devices"])
        self.assertFalse(entry.runtime_data.config.get("geocode", False))
        form = await manager.async_configure(
            form["flow_id"], {"next_step_id": "geocoding"}
        )
        form = await manager.async_configure(form["flow_id"], {"geocode": True})
        result = await self.finish(form)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(
            entry.runtime_data.lookup.options["api_key"], "OTHER_WINDOW_KEY"
        )


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(
        GeoapifyFlow(name)
        for name in [
            "test_geo_draft_skip_save_sharing_and_no_key_exposure",
            "test_connection_test_is_explicit_synthetic_and_unsaved",
            "test_blank_keeps_key_and_explicit_remove_disables_service",
            "test_connection_errors_are_actionable_without_leaking_key",
            "test_revisit_preserves_unsaved_service_draft",
            "test_stale_lookup_form_requires_review_instead_of_silent_refresh",
        ]
    )
