"""UI setup and editable device priorities. No credentials or household defaults."""

from collections.abc import Callable
from copy import deepcopy
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .inputs import (
    DEFAULTS,
    SOURCE_FIELDS,
    charging_age_limit,
    is_position_source,
    is_string_room_source,
    is_worn_source,
    validate_config,
)
from .lookup_flow import LookupFlow
from .places import PlaceCatalog
from .preview import build_preview
from .sources import SourceCatalog


def entity_selector(domains, include=None):
    config: selector.EntitySelectorConfig = {"domain": domains}
    if include is not None:
        config["include_entities"] = include
    return selector.EntitySelector(config)


def settings_schema(config, *, initial=False):
    fields: dict[Any, Any] = {}
    if initial:
        fields[vol.Required("person")] = entity_selector("person")
    fields[
        vol.Optional("name", description={"suggested_value": config.get("name", "")})
        if initial
        else vol.Required("name", default=config.get("name", "Person Presence"))
    ] = str
    for key, default in () if initial else DEFAULTS.items():
        fields[vol.Optional(key, default=config.get(key, default))] = vol.All(
            vol.Coerce(int),
            vol.Range(
                min=0 if key == "settle" else 1, max=3600 if key == "settle" else 86400
            ),
        )
    return vol.Schema(fields)


def device_schema(config, priority):
    fields = {
        vol.Required("name", default=config.get("name", "")): str,
        vol.Required("priority", default=config.get("priority", priority)): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=999)
        ),
        vol.Optional("wearable", default=config.get("wearable", False)): bool,
        vol.Optional(
            "exclude_charging", default=config.get("exclude_charging", False)
        ): bool,
    }
    for field in SOURCE_FIELDS:
        domains = (
            "device_tracker"
            if field in ("tracker", "local_tracker")
            else ["sensor", "binary_sensor", "input_boolean"]
        )
        marker = (
            vol.Optional(field, description={"suggested_value": config[field]})
            if config.get(field)
            else vol.Optional(field)
        )
        fields[marker] = entity_selector(domains)
    fields[
        vol.Optional(
            "timestamp_attribute",
            description={"suggested_value": config.get("timestamp_attribute", "")},
        )
    ] = str
    return vol.Schema(fields)


class DeviceFlow(LookupFlow):
    """Shared add/edit/remove steps for initial setup and options."""

    hass: HomeAssistant
    if TYPE_CHECKING:
        async_show_form: Callable[..., Any]
        async_show_menu: Callable[..., Any]
        async_abort: Callable[..., Any]
        async_create_entry: Callable[..., Any]
    _config: dict
    _editing: str | None = None

    def _validate_sources(self, config, check_devices=None):
        validate_config(config)
        if config.get("place_lookup") and any(
            {**e.data, **e.options}.get("place_lookup")
            and {**e.data, **e.options}.get("person") != config["person"]
            for e in self.hass.config_entries.async_entries(DOMAIN)
        ):
            raise ValueError("geocoder_owned")
        registry = er.async_get(self.hass)
        for device in config["devices"] if check_devices is None else check_devices:
            for field in SOURCE_FIELDS:
                entity_id = device.get(field)
                if not entity_id:
                    continue
                registered = registry.async_get(entity_id)
                if registered and registered.platform == DOMAIN:
                    raise ValueError("self_reference")
                state = self.hass.states.get(entity_id)
                if state is None:
                    raise ValueError("source_missing")
                if field == "room" and not is_string_room_source(entity_id, state):
                    raise ValueError("unsupported_room_source")
                if field == "tracker" and not is_position_source(state):
                    raise ValueError("unsupported_tracker_source")
                if field == "worn" and not is_worn_source(
                    entity_id, state, manual=True
                ):
                    raise ValueError("unsupported_worn_source")

    def _current_device(self):
        return next(
            (d for d in self._config.get("devices", []) if d["key"] == self._editing),
            {},
        )

    async def async_step_device(self, user_input=None):
        current = self._current_device()
        if user_input is not None:
            # Accept complete explicit mappings too, for existing flow clients and repairs.
            if any(user_input.get(k) for k in ("tracker", "room")):
                return await self._save_device(user_input)
            self._draft = {**current, **user_input}
            self._draft.setdefault(
                "device_type", "watch" if current.get("wearable") else "phone"
            )
            self._draft.setdefault("wearable", self._draft["device_type"] == "watch")
            self._manual = False
            if not current:
                catalog = SourceCatalog.from_hass(self.hass)
                person = self.hass.states.get(self._config["person"])
                assigned = (
                    person.attributes.get("device_trackers", []) if person else []
                )
                gps = [
                    c.entity_id
                    for c in catalog.candidates("tracker")
                    if c.entity_id in assigned
                ]
                if len(gps) == 1:
                    self._draft.setdefault("tracker", gps[0])
                    for role, choices in catalog.suggestions(gps[0]).items():
                        if role != "tracker" and len(choices) == 1:
                            self._draft.setdefault(role, choices[0])
            return await self.async_step_source_mode()
        schema = vol.Schema(
            {
                vol.Required("name", default=current.get("name", "")): str,
                vol.Required(
                    "device_type",
                    default=current.get(
                        "device_type", "watch" if current.get("wearable") else "phone"
                    ),
                ): vol.In(["phone", "watch", "tablet", "tag", "other"]),
            }
        )
        return self.async_show_form(step_id="device", data_schema=schema)

    async def async_step_source_mode(self, user_input=None):
        return self.async_show_menu(
            step_id="source_mode", menu_options=["sources", "manual_sources"]
        )

    async def async_step_manual_sources(self, user_input=None):
        self._manual = True
        return await self.async_step_sources()

    async def async_step_sources(self, user_input=None):
        catalog = SourceCatalog.from_hass(self.hass)
        errors = {}
        if user_input is not None:
            self._manual = bool(user_input.get("manual_sources", False))
            selected = {
                k: v
                for k, v in user_input.items()
                if k in (*SOURCE_FIELDS, "timestamp_attribute") and v
            }
            if selected:
                for field in SOURCE_FIELDS:
                    self._draft.pop(field, None)
                if "timestamp_attribute" in user_input:
                    self._draft.pop("timestamp_attribute", None)
                self._draft.update(selected)
                try:
                    for field in SOURCE_FIELDS:
                        entity = selected.get(field)
                        snapshot = catalog.get_state(entity)
                        if (
                            entity
                            and snapshot
                            and not self._manual
                            and not catalog.supports(snapshot, field)
                            and self._current_device().get(field) != entity
                        ):
                            raise ValueError("unsupported_source")
                    if not (selected.get("tracker") or selected.get("room")):
                        raise ValueError("invalid_device")
                except ValueError as err:
                    errors["base"] = str(err)
                else:
                    return await self.async_step_rules()
            elif not self._manual:
                errors["base"] = "invalid_device"
        fields = {}
        for field in SOURCE_FIELDS:
            candidates = catalog.person_candidates(
                self._config["person"], field, current_entity_id=self._draft.get(field)
            )
            domains = (
                "device_tracker"
                if field in ("tracker", "local_tracker")
                else ["sensor", "binary_sensor", "input_boolean"]
            )
            fields[
                vol.Optional(
                    field, description={"suggested_value": self._draft.get(field)}
                )
            ] = entity_selector(
                domains, None if self._manual else [c.entity_id for c in candidates]
            )
        fields[vol.Optional("manual_sources", default=self._manual)] = bool
        if self._manual:
            fields[
                vol.Optional(
                    "timestamp_attribute",
                    description={
                        "suggested_value": self._draft.get("timestamp_attribute", "")
                    },
                )
            ] = str
        return self.async_show_form(
            step_id="sources",
            data_schema=vol.Schema(fields),
            errors=errors,
            description_placeholders={
                "suggestions": "\n".join(
                    f"{c.entity_id} ({c.provider}; {c.basis})"
                    + (" — " + ", ".join(c.warnings) if c.warnings else "")
                    for c in catalog.person_candidates(
                        self._config["person"], "tracker"
                    )
                    if c.basis in ("person_assignment", "related_registry_device")
                )
                or "No assigned GPS sources found. Choose sources below."
            },
        )

    async def async_step_rules(self, user_input=None):
        if user_input is not None:
            device = {**self._draft, **user_input}
            custom = device.pop(
                "use_custom_charging_age", self._draft.get("charging_age") is not None
            )
            if not custom:
                device.pop("charging_age", None)
            return await self._save_device(device)
        next_priority = (
            max((d["priority"] for d in self._config.get("devices", [])), default=0) + 1
        )
        schema = vol.Schema(
            {
                vol.Required(
                    "priority", default=self._draft.get("priority", next_priority)
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=999)),
                vol.Optional(
                    "wearable", default=self._draft.get("wearable", False)
                ): bool,
                vol.Optional(
                    "exclude_charging",
                    default=self._draft.get("exclude_charging", False),
                ): bool,
                vol.Optional(
                    "use_custom_charging_age",
                    default=self._draft.get("charging_age") is not None,
                ): bool,
                vol.Optional(
                    "charging_age",
                    default=charging_age_limit(
                        self._draft,
                        self._config.get("signal_age", 600),
                        SourceCatalog.from_hass(self.hass),
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=86400,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="seconds",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="rules", data_schema=schema)

    async def _save_device(self, user_input):
        current = self._current_device()
        editable = {
            "name",
            "priority",
            "device_type",
            "wearable",
            "exclude_charging",
            "timestamp_attribute",
            "charging_age",
            *SOURCE_FIELDS,
        }
        device = {k: v for k, v in current.items() if k not in editable}
        device.update(
            {
                k: v
                for k, v in user_input.items()
                if v != "" and v is not None and k != "manual_sources"
            }
        )
        device["key"] = current.get("key", uuid4().hex)
        candidate = {
            **self._config,
            "devices": [
                d for d in self._config.get("devices", []) if d["key"] != self._editing
            ]
            + [device],
        }
        try:
            self._validate_sources(candidate, [device])
        except ValueError as err:
            return self.async_show_form(
                step_id="device",
                data_schema=device_schema(device, device.get("priority", 1)),
                errors={"base": str(err)},
            )
        self._config = candidate
        self._editing = None
        return await self.async_step_menu()

    async def async_step_add(self, user_input=None):
        self._editing = None
        return await self.async_step_device()

    async def async_step_menu(self, user_input=None):
        return self.async_show_menu(
            step_id="menu",
            menu_options=[
                "add",
                "edit",
                "remove",
                "move_earlier",
                "move_later",
                "settings",
                "geocoding",
                "finish",
            ],
            description_placeholders={
                "devices": "; ".join(
                    str(d["priority"]) + ": " + d["name"]
                    for d in sorted(
                        self._config.get("devices", []), key=lambda d: d["priority"]
                    )
                )
            },
        )

    def _device_choice(self):
        return vol.Schema(
            {
                vol.Required("device"): vol.In(
                    {
                        d["key"]: f"{d['priority']}: {d['name']}"
                        for d in sorted(
                            self._config["devices"], key=lambda d: d["priority"]
                        )
                    }
                )
            }
        )

    async def async_step_edit(self, user_input=None):
        if user_input is not None:
            if user_input.get("device") not in {
                d["key"] for d in self._config["devices"]
            }:
                return self.async_abort(reason="invalid_device")
            self._editing = user_input["device"]
            return await self.async_step_device()
        return self.async_show_form(step_id="edit", data_schema=self._device_choice())

    async def async_step_remove(self, user_input=None):
        error = {}
        if user_input is not None:
            if len(self._config["devices"]) <= 1:
                error["base"] = "last_device"
            else:
                self._config["devices"] = [
                    d
                    for d in self._config["devices"]
                    if d["key"] != user_input["device"]
                ]
                return await self.async_step_menu()
        return self.async_show_form(
            step_id="remove", data_schema=self._device_choice(), errors=error
        )

    async def async_step_settings(self, user_input=None):
        error = {}
        if user_input is not None:
            candidate = {**self._config, **user_input}
            try:
                candidate = validate_config(candidate)
            except ValueError as err:
                error["base"] = str(err)
            else:
                self._config = candidate
                return await self.async_step_menu()
        return self.async_show_form(
            step_id="settings", data_schema=settings_schema(self._config), errors=error
        )

    async def async_step_finish(self, user_input=None):
        try:
            self._validate_sources(self._config)
        except ValueError as err:
            return self.async_show_menu(
                step_id="menu",
                menu_options=["add", "edit", "remove", "settings", "finish"],
                description_placeholders={
                    "devices": "Some sources need repair: " + str(err)
                },
            )
        return await self.async_step_preview()

    async def async_step_preview(self, user_input=None):
        preview = build_preview(
            {**self._config, "timezone": self.hass.config.time_zone},
            SourceCatalog.from_hass(self.hass),
            PlaceCatalog.from_hass(self.hass),
            dt_util.utcnow().timestamp(),
        )
        return self.async_show_menu(
            step_id="preview",
            menu_options=["save", "menu"],
            description_placeholders={"summary": preview.summary},
        )

    async def async_step_save(self, user_input=None):
        try:
            self._validate_sources(self._config)
            await self._commit_lookup()
        except ValueError as err:
            return self.async_show_menu(
                step_id="menu",
                menu_options=["geocoding", "finish"],
                description_placeholders={
                    "devices": "Settings could not be saved: "
                    + str(err)
                    + ". Open Place lookup to review."
                },
            )
        return self.async_create_entry(title=self._config["name"], data=self._config)

    async def _move(self, direction, user_input):
        if user_input is None:
            return self.async_show_form(
                step_id="move_earlier" if direction < 0 else "move_later",
                data_schema=self._device_choice(),
            )
        devices = sorted(self._config["devices"], key=lambda d: d["priority"])
        index = next(
            (i for i, d in enumerate(devices) if d["key"] == user_input.get("device")),
            None,
        )
        if index is None:
            return self.async_abort(reason="invalid_device")
        adjacent = index + direction
        if 0 <= adjacent < len(devices):
            devices[index]["priority"], devices[adjacent]["priority"] = (
                devices[adjacent]["priority"],
                devices[index]["priority"],
            )
        return await self.async_step_menu()

    async def async_step_move_earlier(self, user_input=None):
        return await self._move(-1, user_input)

    async def async_step_move_later(self, user_input=None):
        return await self._move(1, user_input)


class PresenceConfigFlow(DeviceFlow, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input["person"])
            self._abort_if_unique_id_configured()
            person_state = self.hass.states.get(user_input["person"])
            if person_state is None:
                return self.async_show_form(
                    step_id="user",
                    data_schema=settings_schema(user_input, initial=True),
                    errors={"base": "invalid_person"},
                )
            self._config = {
                **DEFAULTS,
                **user_input,
                "name": user_input.get("name")
                or person_state.name + " Person Presence",
                "devices": [],
            }
            self._editing = None
            return await self.async_step_device()
        return self.async_show_form(
            step_id="user", data_schema=settings_schema({}, initial=True)
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PresenceOptionsFlow()


class PresenceOptionsFlow(DeviceFlow, config_entries.OptionsFlowWithReload):
    async def async_step_init(self, user_input=None):
        self._config = deepcopy({**self.config_entry.data, **self.config_entry.options})
        self._editing = None
        return await self.async_step_menu()
