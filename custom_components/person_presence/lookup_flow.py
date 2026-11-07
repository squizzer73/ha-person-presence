"""Guided optional address lookup; only final Save commits shared settings."""

from collections.abc import Callable
from copy import deepcopy
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import selector

from .lookup_settings import async_save, async_snapshot
from .providers import (
    TEST_COORDINATES,
    ProviderError,
    async_request,
    validate_provider_options,
)


class LookupFlow:
    if TYPE_CHECKING:
        async_show_form: Callable[..., Any]
        async_show_menu: Callable[..., Any]
        async_step_menu: Callable[..., Any]
    hass: Any
    _config: dict
    _lookup_snapshot: dict | None = None
    _lookup_draft: dict
    _lookup_dirty = False

    async def async_step_geocoding(self, user_input=None):
        if self._lookup_snapshot is None:
            self._lookup_snapshot = await async_snapshot(self.hass)
            self._lookup_draft = deepcopy(self._lookup_snapshot["options"])
            self._lookup_dirty = False
        if user_input is not None:
            self._config["geocode"] = bool(user_input.get("geocode", False))
            if (
                user_input.get("configure_service")
                or self._config["geocode"]
                and not self._lookup_draft
            ):
                return await self.async_step_lookup_provider()
            return await self.async_step_menu()
        service = (
            (
                "Geoapify configured"
                if self._lookup_draft.get("provider") == "geoapify"
                else "Custom service configured"
            )
            if self._lookup_draft
            else "Not set up yet"
        )
        return self.async_show_form(
            step_id="geocoding",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "geocode", default=self._config.get("geocode", False)
                    ): bool,
                    vol.Optional("configure_service", default=False): bool,
                }
            ),
            description_placeholders={"service": service},
        )

    async def async_step_lookup_provider(self, user_input=None):
        if user_input is not None:
            if user_input["provider"] == "remove":
                self._lookup_draft = {}
                self._config["geocode"] = False
                return await self.async_step_lookup_skip()
            if user_input["provider"] == "custom":
                return await self.async_step_lookup_custom()
            return await self.async_step_lookup_geoapify()
        return self.async_show_form(
            step_id="lookup_provider",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "provider", default="geoapify"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["geoapify", "custom", "remove"],
                            translation_key="lookup_provider",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_lookup_geoapify(self, user_input=None):
        errors = {}
        existing = (
            self._lookup_draft.get("api_key", "")
            if self._lookup_draft.get("provider") == "geoapify"
            else ""
        )
        if user_input is not None:
            if user_input.get("remove_key"):
                self._lookup_draft = {}
                self._config["geocode"] = False
                return await self.async_step_lookup_skip()
            try:
                self._lookup_draft = validate_provider_options(
                    {
                        "provider": "geoapify",
                        "api_key": user_input.get("api_key", "").strip() or existing,
                    }
                )
            except ValueError:
                errors["base"] = "invalid_auth"
            else:
                return await self.async_step_lookup_test()
        fields: dict[Any, Any] = {
            vol.Optional("api_key"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            )
        }
        if existing:
            fields[vol.Optional("remove_key", default=False)] = bool
        return self.async_show_form(
            step_id="lookup_geoapify",
            data_schema=vol.Schema(fields),
            errors=errors,
            description_placeholders={
                "saved_key": "A key is saved. Leave blank to keep it, or enter a replacement."
                if existing
                else "No key is saved yet."
            },
        )

    async def async_step_lookup_test(self, user_input=None):
        return self.async_show_menu(
            step_id="lookup_test",
            menu_options=["lookup_test_connection", "lookup_skip", "lookup_geoapify"],
        )

    async def async_step_lookup_test_connection(self, user_input=None):
        try:
            data = await async_request(
                self.hass,
                self._lookup_draft,
                {"lat": str(TEST_COORDINATES[0]), "lon": str(TEST_COORDINATES[1])},
            )
            if not isinstance(data, dict) or not data.get("display_name"):
                raise ProviderError("unexpected_response")
        except ProviderError as err:
            self._lookup_test_reason = {
                "invalid_auth": "The API key was rejected. Check it in your Geoapify account.",
                "quota": "The service reported a quota or rate limit. Try later or check your plan.",
                "cannot_connect": "The service could not be reached. Check your connection or try later.",
                "unexpected_response": "The service returned an unexpected response. Try later.",
            }.get(str(err), "The service could not be checked.")
            return await self.async_step_lookup_test_error()
        return await self.async_step_lookup_test_success()

    async def async_step_lookup_test_error(self, user_input=None):
        return self.async_show_menu(
            step_id="lookup_test_error",
            menu_options=["lookup_geoapify", "lookup_test_connection", "lookup_skip"],
            description_placeholders={"reason": self._lookup_test_reason},
        )

    async def async_step_lookup_test_success(self, user_input=None):
        return self.async_show_menu(
            step_id="lookup_test_success",
            menu_options=["lookup_skip", "lookup_geoapify"],
        )

    async def async_step_lookup_skip(self, user_input=None):
        self._lookup_dirty = True
        return await self.async_step_menu()

    async def async_step_lookup_custom(self, user_input=None):
        current = (
            self._lookup_draft
            if self._lookup_draft.get("provider") != "geoapify"
            else {}
        )
        errors = {}
        if user_input is not None:
            try:
                self._lookup_draft = validate_provider_options(
                    {**user_input, "provider": "custom"}
                )
            except ValueError:
                errors["base"] = "invalid_geocoder"
            else:
                return await self.async_step_lookup_skip()
        return self.async_show_form(
            step_id="lookup_custom",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "endpoint",
                        description={"suggested_value": current.get("endpoint", "")},
                    ): str,
                    vol.Optional(
                        "contact",
                        description={"suggested_value": current.get("contact", "")},
                    ): str,
                    vol.Optional(
                        "authorized", default=current.get("authorized", False)
                    ): bool,
                    vol.Optional(
                        "local_http", default=current.get("local_http", False)
                    ): bool,
                }
            ),
            errors=errors,
        )

    async def _commit_lookup(self):
        current = await async_snapshot(self.hass)
        if (
            self._lookup_snapshot is not None
            and (self._lookup_dirty or self._config.get("geocode"))
            and current != self._lookup_snapshot
        ):
            self._lookup_snapshot = None
            self._lookup_dirty = False
            self._lookup_draft = {}
            raise ValueError("lookup_changed")
        options = self._lookup_draft if self._lookup_dirty else current["options"]
        if self._config.get("geocode") and not options:
            raise ValueError("invalid_geocoder")
        if self._lookup_dirty:
            try:
                await async_save(self.hass, self._lookup_snapshot, options)
            except ValueError as err:
                if str(err) == "lookup_changed":
                    self._lookup_snapshot = None
                    self._lookup_dirty = False
                    self._lookup_draft = {}
                raise
            from .place_service import KEY, sync_lookup

            if KEY in self.hass.data:
                sync_lookup(self.hass, self.hass.data[KEY])
            self._lookup_dirty = False
