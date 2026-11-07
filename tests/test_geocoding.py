import asyncio
import unittest

from test_engine import load


class Lookup(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_validation_cache_and_lifecycle(self):
        module = load("geocoding")
        with self.assertRaises(ValueError):
            module.validate_options(
                {"endpoint": "http://example.com/reverse", "authorized": True}
            )
        with self.assertRaises(ValueError):
            module.validate_options(
                {
                    "endpoint": "https://nominatim.openstreetmap.org/reverse",
                    "authorized": True,
                }
            )
        calls = []

        async def request(url, params):
            calls.append(params)
            return {"display_name": "Town square", "licence": "Map data attribution"}

        lookup = module.PlaceLookup(request, spacing=0)
        self.assertIsNone(await lookup.resolve(1, 2))
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        label = await lookup.resolve(1, 2)
        self.assertEqual(label.label, "Town square")
        self.assertEqual((await lookup.resolve(1, 2)), label)
        self.assertEqual(len(calls), 1)
        lookup.clear()
        await lookup.resolve(1, 2)
        self.assertEqual(len(calls), 2)
        lookup.configure(
            {"endpoint": "https://other.example/reverse", "authorized": True}
        )
        await lookup.resolve(1, 2)
        self.assertEqual(len(calls), 3)

    async def test_late_reply_after_disable_or_endpoint_change_ignored(self):
        module = load("geocoding")
        gate = asyncio.Event()

        async def request(url, params):
            await gate.wait()
            return {"display_name": "Old place"}

        lookup = module.PlaceLookup(request, spacing=0)
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        task = asyncio.create_task(lookup.resolve(1, 2))
        await asyncio.sleep(0)
        lookup.configure({})
        gate.set()
        self.assertIsNone(await task)
        self.assertEqual(lookup.cache, {})

    async def test_bad_response_and_bounded_persistent_cache(self):
        module = load("geocoding")

        async def request(url, params):
            return {"display_name": ["bad"]}

        lookup = module.PlaceLookup(request, spacing=0)
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        self.assertIsNone(await lookup.resolve(1, 2))
        lookup.restore({"not a valid cache": {}})
        self.assertEqual(lookup.cache, {})
        self.assertEqual(
            module.validate_options(
                {
                    "endpoint": "http://127.0.0.1:8080/reverse",
                    "authorized": True,
                    "local_http": True,
                }
            )["endpoint"],
            "http://127.0.0.1:8080/reverse",
        )

    async def test_rate_limit_backoff_and_expired_cache(self):
        module = load("geocoding")
        now = [1000.0]
        calls = []

        async def request(url, params):
            calls.append(params)
            if len(calls) == 1:
                raise OSError("rate limited")
            return {"display_name": "Square", "licence": "Example"}

        lookup = module.PlaceLookup(request, spacing=0, clock=lambda: now[0])
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        self.assertIsNone(await lookup.resolve(1, 2))
        self.assertIsNone(await lookup.resolve(1, 2))
        self.assertEqual(len(calls), 1)
        now[0] += 601
        await lookup.resolve(1, 2)
        saved = lookup.cache.copy()
        lookup.clear()
        lookup.restore(saved)
        self.assertEqual(len(lookup.cache), 1)
        now[0] += 31 * 86400
        await lookup.resolve(1, 2)
        self.assertEqual(len(calls), 3)
        lookup.clear()
        for i in range(1002):
            await lookup.resolve(1, i / 100)
        self.assertEqual(len(lookup.cache), 1000)

    async def test_serial_requests_share_one_queue(self):
        module = load("geocoding")
        times = []

        async def request(url, params):
            times.append(asyncio.get_running_loop().time())
            return {"display_name": "Square"}

        lookup = module.PlaceLookup(request, spacing=0.02)
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        await asyncio.gather(
            lookup.resolve(1, 1), lookup.resolve(1, 2), lookup.resolve(1, 3)
        )
        self.assertTrue(all(b - a >= 0.015 for a, b in zip(times, times[1:])))

    async def test_fragmented_json_is_read_completely_and_size_bounded(self):
        module = load("geocoding")

        class Content:
            async def iter_chunked(self, size):
                for chunk in [b'{"display_', b'name":"Square"}']:
                    yield chunk

        self.assertEqual((await module.read_json(Content()))["display_name"], "Square")

        class Huge:
            async def iter_chunked(self, size):
                for i in range(9):
                    yield b"x" * 8192

        with self.assertRaises(ValueError):
            await module.read_json(Huge())

    async def test_retention_prunes_without_another_lookup_and_notifies_storage(self):
        module = load("geocoding")
        now = [100.0]

        async def request(url, params):
            return {"display_name": "Square"}

        lookup = module.PlaceLookup(request, spacing=0, clock=lambda: now[0])
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        await lookup.resolve(1, 2)
        writes = []
        lookup.on_change = lambda: writes.append(lookup.cache.copy())
        now[0] += 30 * 86400
        lookup.prune()
        self.assertEqual(lookup.cache, {})
        self.assertEqual(writes, [{}])
