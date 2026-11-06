# Person Presence

![Person Presence icon](custom_components/person_presence/brand/icon.png)

[![Open in the Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=squizzer73&repository=ha-person-presence&category=integration)

[![Set up Person Presence](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=person_presence)

Turn existing phone, watch and room-tracking entities into an explainable answer to “where is this person?” Version 0.2.0b1 is a beta. [Download the 0.2.0b1 prerelease](https://github.com/squizzer73/ha-person-presence/releases/tag/0.2.0b1). Catalog inclusion is pending.

Requires Home Assistant Core 2026.11 or later. Validation targets 2026.11.0; later releases need compatibility checks. No new account, cloud service or device commands. Existing providers such as the Companion app, iCloud3 and Bermuda supply observations.

## Setup

Add the repository using the Marketplace button above. Select beta/prerelease versions if your client hides them. Alternatively download the install ZIP from the release page and use the manual steps below.

1. Install `custom_components/person_presence` from the candidate ZIP into your HA configuration directory, then restart HA.
2. Open Settings → Devices & services → Add integration → Person Presence.
3. Select an existing Person (a login is not required), name a logical device and select its type.
4. Choose filtered sources, or advanced manual mapping for a generic provider. GPS, charging and room entities for the same physical device may belong to different HA registry devices. Confirm each mapping; similar names do not establish identity.
5. Set preference and charging/wearing rules, review the preview, then Save.
6. Open the new per-person device page to see all current readings. Add another entry for each person.

Configure later to add/edit/remove devices, move their preferences, adjust advanced limits and preview unsaved changes. Deleted source entities create a Repair that links back to configuration. A preview does not save an entry or change current tracking.

## Outputs

**Whereabouts** is the primary sensor: an actual room name when home with fresh room evidence, Home when only home is known, an actual zone name when away in a zone, Away elsewhere, or native Unknown when evidence is insufficient.

Use `presence` (`home` / `away` / `unknown`), `context` (`room` / `zone` / `home` / `away` / `unknown`), `area_id` and `zone_id` for automations. A room and a zone can have the same displayed name. Other attributes identify the selected logical device, source entity, confidence category, wearing status and settling. Confidence is not a numerical probability or proof the device is carried.

Location, Room, Selected device and Decision remain available. The optional tracker and the Last known whereabouts / Last observation time diagnostics are disabled by default. Last-known data is historical, held only during the current HA run, and never substituted for the current answer. Volatile timing details are available in diagnostics/preview; unchanged heartbeats do not publish new semantic state.

The integration remains independent of existing Person assignments and automations. Enabling or attaching its optional tracker is a separate user decision. It does not automatically take over household tracking.

## Rules and limits

Confirmed worn evidence takes precedence; otherwise lower preference numbers come first. Charging wearables and explicitly unworn devices are excluded. Configured eligibility signals that cannot be assessed exclude the device with an uncertainty explanation. Without a worn sensor, a watch left on a table may still be selected. Not charging does not prove worn.

Phones remain eligible while charging by default, because they may charge in a car or pocket. Turn on charging exclusion only where that matches your use. A confirmed-worn device without a fresh location prevents a confident fallback to an abandoned phone.

Defaults: GPS age 300 seconds, room age 60 seconds, eligibility signal age 600 seconds, settling 15 seconds and GPS error up to 100 metres. Older entries retain their configured limits. A newer entity update is not necessarily a newer observation: iCloud3 uses its actual located timestamp. Provider/report-only timestamps carry a quality limitation. Ambiguous or nonexistent local timestamps are rejected rather than guessed.

Bermuda room reports are estimates. Use its matching local home/away tracker as a guard; report time alone is not proof of a new radio sighting. Away evidence suppresses an older room, and equal-time contradictory room/away evidence yields Unknown. No Bluetooth disappearance can identify a woodland zone: that needs a fresh outdoor fix from the carried device's existing provider.

## Testing and upgrades

Test both devices carried, watch charging elsewhere, phone left elsewhere, watch-only departure, watch removed without charging, stale/offline sources and a restart. Compare observations with physical reality and measure delays. Passing automated tests is not physical acceptance.

Upgrades preserve the integration domain, existing entries, device identifiers, entity IDs, custom names, enabled/disabled settings, mappings, priorities and explicit timing limits. Whereabouts is additive. Back up HA before installing; rollback must preserve newer user settings rather than blindly restoring old registry/config snapshots.

See [usage examples](docs/usage.md), [troubleshooting](docs/troubleshooting.md), [privacy](docs/privacy.md), [validation](VALIDATION.md) and [publication gates](PUBLICATION.md).

## Development

From this standalone repository root:

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy custom_components/person_presence
.venv/bin/python scripts/build_release.py --output dist/beta
```

Tests use fictional households and a real temporary HA Core instance, including recorder SQLite checks. No household connection or credentials are required. The release builder exports from an allowlist, excluding development environments, private files and household deployment scripts.

## Support and contributions

Maintained by [@squizzer73](https://github.com/squizzer73). See [support](SUPPORT.md), [contributing](CONTRIBUTING.md) and [security reporting](SECURITY.md). Field reports should include expected versus observed behaviour and delays; never include real coordinates, credentials or Bluetooth identity keys.

## Licence

[MIT](LICENSE). Copyright © 2026 squizzer73.
