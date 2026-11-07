import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_engine import load


class Providers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.p = load("providers")
        self.key = "FICTIONAL_KEY_NEVER_A_REAL_CREDENTIAL"

    def test_geoapify_options_request_and_response(self):
        options = self.p.validate_provider_options(
            {"provider": "geoapify", "api_key": self.key}
        )
        url, params = self.p.request_spec(options, 1.234567, 2.345678)
        self.assertEqual(url, "https://api.geoapify.com/v1/geocode/reverse")
        self.assertEqual(params["apiKey"], self.key)
        self.assertEqual(params["format"], "json")
        self.assertEqual(params["lat"], "1.2346")
        self.assertNotIn(self.key, self.p.provider_identity(options))
        answer = self.p.normalize_response(
            options,
            {
                "results": [
                    {
                        "formatted": "Example Square",
                        "datasource": {"attribution": "© OpenStreetMap contributors"},
                    }
                ]
            },
        )
        self.assertEqual(answer["display_name"], "Example Square")
        self.assertEqual(answer["provider"], "geoapify")
        with self.assertRaises(ValueError):
            self.p.validate_provider_options({"provider": "geoapify", "api_key": ""})
        self.assertIsNone(self.p.normalize_response(options, {"results": []}))
        self.assertIsNone(
            self.p.normalize_response(options, {"results": [{"formatted": ["wrong"]}]})
        )

    def test_legacy_custom_options_and_key_rotation(self):
        geo = load("geocoding")
        custom = {"endpoint": "https://custom.example/reverse", "authorized": True}
        self.assertEqual(
            self.p.validate_provider_options(custom),
            custom | {"local_http": False, "contact": ""},
        )

        async def request(url, params):
            return {"display_name": "Square"}

        lookup = geo.PlaceLookup(request)
        lookup.configure({"provider": "geoapify", "api_key": self.key})
        lookup.retry_at = 99999999999
        generation = lookup.generation
        lookup.configure({"provider": "geoapify", "api_key": "FICTIONAL_REPLACEMENT"})
        self.assertGreater(lookup.generation, generation)
        self.assertEqual(lookup.retry_at, 0)
        self.assertEqual(lookup.cache, {})

    async def test_http_failures_do_not_expose_secret_urls(self):
        import homeassistant.helpers.aiohttp_client as client

        options = {"provider": "geoapify", "api_key": self.key}

        class Response:
            def __init__(self, status):
                self.status = status

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        for status, code in [
            (401, "invalid_auth"),
            (403, "invalid_auth"),
            (429, "quota"),
            (503, "cannot_connect"),
            (302, "unexpected_response"),
        ]:
            session = SimpleNamespace(get=lambda *a, **k: Response(status))
            with patch.object(client, "async_get_clientsession", return_value=session):
                with self.assertRaises(self.p.ProviderError) as caught:
                    await self.p.async_request(None, options, {"lat": "1", "lon": "2"})
                self.assertEqual(str(caught.exception), code)
                self.assertNotIn(self.key, str(caught.exception))
                self.assertIsNone(caught.exception.__cause__)

    async def test_cache_and_network_exception_do_not_expose_key(self):
        import aiohttp
        import homeassistant.helpers.aiohttp_client as client

        geo = load("geocoding")
        options = self.p.validate_provider_options(
            {"provider": "geoapify", "api_key": self.key}
        )

        async def request(url, params):
            return self.p.normalize_response(
                options, {"results": [{"formatted": "Square"}]}
            )

        lookup = geo.PlaceLookup(request, spacing=0)
        lookup.configure(options)
        label = await lookup.resolve(1, 2)
        self.assertEqual(label.provider, "geoapify")
        self.assertNotIn(self.key, str(lookup.cache))
        self.assertNotIn(self.key, str(label))

        def fail(*args, **kwargs):
            raise aiohttp.ClientConnectionError("URL contained apiKey=" + self.key)

        with patch.object(
            client, "async_get_clientsession", return_value=SimpleNamespace(get=fail)
        ):
            with self.assertRaises(self.p.ProviderError) as caught:
                await self.p.async_request(None, options, {"lat": "1", "lon": "2"})
        self.assertEqual(str(caught.exception), "cannot_connect")
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertNotIn(self.key, str(caught.exception))
