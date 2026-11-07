from test_ha import HomeAssistantTests


class SharedLookupSettings(HomeAssistantTests):
    async def test_settings_are_shared_private_and_revision_checked(self):
        entry = await self.create()
        from custom_components.person_presence.lookup_settings import (
            async_save,
            async_snapshot,
            effective_options,
        )

        first = await async_snapshot(self.hass)
        self.assertEqual(first["options"], {})
        options = {"provider": "geoapify", "api_key": "FICTIONAL_PRIVATE_KEY"}
        saved = await async_save(self.hass, first, options)
        self.assertEqual(
            effective_options(self.hass)["api_key"], "FICTIONAL_PRIVATE_KEY"
        )
        with self.assertRaisesRegex(ValueError, "lookup_changed"):
            await async_save(
                self.hass, first, {"provider": "geoapify", "api_key": "STALE_DRAFT"}
            )
        self.assertNotIn("FICTIONAL_PRIVATE_KEY", str(dict(entry.options)))
        from custom_components.person_presence.lookup_settings import KEY

        del self.hass.data[KEY]
        self.assertEqual(
            (await async_snapshot(self.hass))["options"]["api_key"],
            "FICTIONAL_PRIVATE_KEY",
        )
        await async_save(self.hass, saved, {})
        self.assertEqual(effective_options(self.hass), {})

    async def test_legacy_owner_fallback_and_explicit_empty_override(self):
        entry = await self.create()
        from custom_components.person_presence.lookup_settings import (
            async_save,
            async_snapshot,
            effective_options,
        )

        legacy = {"endpoint": "https://custom.example/reverse", "authorized": True}
        self.hass.config_entries.async_update_entry(
            entry, options={"place_lookup": legacy}
        )
        first = await async_snapshot(self.hass)
        self.assertEqual(first["options"]["endpoint"], legacy["endpoint"])
        await async_save(self.hass, first, {})
        self.assertEqual(effective_options(self.hass), {})
        self.assertEqual(dict(entry.options)["place_lookup"], legacy)

    async def test_last_entry_removal_deletes_private_key(self):
        from homeassistant.helpers.storage import Store

        entry = await self.create()
        from custom_components.person_presence.lookup_settings import (
            async_save,
            async_snapshot,
        )

        await async_save(
            self.hass,
            await async_snapshot(self.hass),
            {"provider": "geoapify", "api_key": "FICTIONAL_PRIVATE_KEY"},
        )
        store = Store(
            self.hass,
            1,
            "person_presence.lookup_settings",
            private=True,
            atomic_writes=True,
        )
        self.assertIn("FICTIONAL_PRIVATE_KEY", str(await store.async_load()))
        await self.hass.config_entries.async_remove(entry.entry_id)
        await self.hass.async_block_till_done()
        self.assertIsNone(await store.async_load())


def load_tests(loader, tests, pattern):
    import unittest

    return unittest.TestSuite(
        SharedLookupSettings(name)
        for name in [
            "test_settings_are_shared_private_and_revision_checked",
            "test_legacy_owner_fallback_and_explicit_empty_override",
            "test_last_entry_removal_deletes_private_key",
        ]
    )
