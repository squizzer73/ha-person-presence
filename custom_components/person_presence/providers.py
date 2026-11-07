"""Provider contracts and sanitized transport; no key-bearing errors or public defaults."""

import asyncio
import ipaddress
from urllib.parse import urlsplit

GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/reverse"
TEST_COORDINATES = (52.4794, 13.2139)


class ProviderError(ValueError):
    """Only a safe, translated category leaves the transport boundary."""


def validate_provider_options(options):
    if options.get("provider", "custom") == "geoapify":
        key = options.get("api_key")
        if (
            not isinstance(key, str)
            or not key.strip()
            or len(key) > 512
            or any(ord(c) < 33 for c in key.strip())
        ):
            raise ValueError("invalid_auth")
        return {
            "provider": "geoapify",
            "api_key": key.strip(),
            "endpoint": GEOAPIFY_URL,
        }
    if options.get("provider", "custom") != "custom":
        raise ValueError("invalid_geocoder")
    return _custom_options(options)


def provider_identity(options):
    return options.get("endpoint", "\0")


def request_spec(options, latitude, longitude):
    options = validate_provider_options(options)
    params = {"lat": f"{latitude:.4f}", "lon": f"{longitude:.4f}", "format": "jsonv2"}
    if options.get("provider") == "geoapify":
        params.update(format="json", apiKey=options["api_key"])
    return options["endpoint"], params


def normalize_response(options, data):
    if options.get("provider") != "geoapify":
        return data
    results = data.get("results") if isinstance(data, dict) else None
    row = results[0] if isinstance(results, list) and results else None
    if not isinstance(row, dict):
        return None
    label = row.get("formatted")
    if not isinstance(label, str) or not label.strip():
        return None
    datasource = row.get("datasource", {})
    attribution = (
        datasource.get("attribution", "© OpenStreetMap contributors")
        if isinstance(datasource, dict)
        else "© OpenStreetMap contributors"
    )
    return {
        "display_name": label,
        "licence": attribution
        if isinstance(attribution, str)
        else "© OpenStreetMap contributors",
        "provider": "geoapify",
    }


async def async_request(hass, options, params):
    import aiohttp
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .geocoding import read_json

    url, request_params = request_spec(
        options, float(params["lat"]), float(params["lon"])
    )
    try:
        async with asyncio.timeout(12):
            async with async_get_clientsession(hass).get(
                url,
                params=request_params,
                headers={
                    "User-Agent": "PersonPresence/0.4 (Home Assistant; "
                    + options.get("contact", "")
                    + ")"
                },
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise ProviderError("invalid_auth")
                if response.status == 429:
                    raise ProviderError("quota")
                if response.status >= 400:
                    raise ProviderError("cannot_connect")
                if response.status != 200:
                    raise ProviderError("unexpected_response")
                data = await read_json(response.content)
                return normalize_response(options, data)
    except ProviderError:
        raise
    except aiohttp.ClientError, TimeoutError, OSError:
        raise ProviderError("cannot_connect") from None
    except ValueError, TypeError:
        raise ProviderError("unexpected_response") from None


def _custom_options(options):
    endpoint = str(options.get("endpoint", "")).strip()
    if not endpoint:
        return {}
    parts = urlsplit(endpoint)
    host = (parts.hostname or "").rstrip(".").lower()
    try:
        local = ipaddress.ip_address(host).is_private
    except ValueError:
        local = host == "localhost" or host.endswith(".local")
    if (
        not options.get("authorized")
        or not host
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or host == "nominatim.openstreetmap.org"
        or not (
            parts.scheme == "https"
            or parts.scheme == "http"
            and local
            and options.get("local_http")
        )
    ):
        raise ValueError("invalid_geocoder")
    return {
        "endpoint": endpoint,
        "authorized": True,
        "local_http": bool(options.get("local_http")),
        "contact": str(options.get("contact", ""))[:200],
    }
