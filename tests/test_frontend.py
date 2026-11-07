import unittest

from test_engine import load


class Resources(unittest.IsolatedAsyncioTestCase):
    async def test_resource_registration_is_idempotent_updates_owned_url_only(self):
        frontend = load("frontend")

        class Resources:
            def __init__(self):
                self.items = [
                    {"id": "other", "url": "/local/user.js", "type": "module"}
                ]

            def async_items(self):
                return self.items

            async def async_get_info(self):
                pass

            async def async_create_item(self, data):
                self.items.append({"id": "ours", **data})

            async def async_update_item(self, id, data):
                next(x for x in self.items if x["id"] == id).update(data)

        resources = Resources()
        await frontend.ensure_resource(resources)
        await frontend.ensure_resource(resources)
        self.assertEqual(len(resources.items), 2)
        self.assertEqual(resources.items[0]["url"], "/local/user.js")
        resources.items[1]["url"] = "/person_presence/person-presence-card.js?v=old"
        await frontend.ensure_resource(resources)
        self.assertEqual(resources.items[1]["url"], frontend.CARD_URL)

    async def test_concurrent_people_register_static_path_once(self):
        import asyncio
        from types import SimpleNamespace

        frontend = load("frontend")

        class HTTP:
            count = 0

            async def async_register_static_paths(self, paths):
                self.count += 1
                await asyncio.sleep(0)

        hass = SimpleNamespace(data={}, http=HTTP())
        await asyncio.gather(
            frontend.setup_frontend(hass), frontend.setup_frontend(hass)
        )
        self.assertEqual(hass.http.count, 1)

    async def test_resource_failure_can_retry_without_duplicate_route(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch

        frontend = load("frontend")

        class Collection:
            pass

        hass = SimpleNamespace(
            data={frontend.LOVELACE_DATA: SimpleNamespace(resources=Collection())},
            http=SimpleNamespace(async_register_static_paths=AsyncMock()),
        )
        with (
            patch.object(frontend, "ResourceStorageCollection", Collection),
            patch.object(
                frontend,
                "ensure_resource",
                new=AsyncMock(side_effect=[ValueError("transient"), None]),
            ) as register,
        ):
            with self.assertRaises(ValueError):
                await frontend.setup_frontend(hass)
            await frontend.setup_frontend(hass)
            self.assertEqual(register.await_count, 2)
            self.assertEqual(hass.http.async_register_static_paths.await_count, 1)
