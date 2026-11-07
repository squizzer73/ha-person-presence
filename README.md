# Person Presence

![Person Presence icon](custom_components/person_presence/brand/icon.png)

[![Open in the Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=squizzer73&repository=ha-person-presence&category=integration)

[![Set up Person Presence](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=person_presence)

## Why I built this

I built Person Presence because I wanted a more realistic answer to a fairly simple question: **where is everyone?**

In my case, I use it to help show people's actual location on my Home Assistant dashboards, whether they are at home or out and about. At home, I'd like to know which room they are in. Away from home, I'd like to show the zone they are in, or just that they are away if that is all the available information can tell me.

The bit I wanted to try and fix was the difference between knowing where someone's devices are and knowing where the person is. A phone, watch and iPad can all belong to the same person, but they aren't always with them.

For example, I might have my phone in my pocket and my watch on charge in the bedroom, while I'm sitting in the lounge. Or my phone might be in the kitchen while I'm wearing my watch in the lounge. I might even leave my phone charging at home and take the dog for a walk with just my watch. I'd like the dashboard to follow me through those situations, rather than continue showing the location of a device I've left behind.

That is what this integration is trying to do. You associate devices with a person, put them in your preferred order, and give it the location, room, charging and wearing information you already have. It uses that information to decide which device to follow and provides a combined **Whereabouts** sensor for dashboards, automations and notifications. You can also see which device it selected and why.

It still needs useful information from your existing tracking integrations. It can't know that a watch is being worn without a suitable signal, or place you in the woods without a fresh outdoor location from the device you took with you. If the information is too old or conflicting, Unknown can be the right answer. The aim is a more useful location, not a confident guess.

## A note on how this was built

This has been **“Vibe Coded”** using AI assistance, with lots of consultation, questions, back and forth and testing along the way. I started with the situations I wanted it to handle and worked through how it should behave, what information it could use, and what it should do when that information wasn't available.

I'm using it on my own system, but it is still a beta and there will be setups and situations I haven't covered. I'm very much open to suggestions, bugs, changes, ideas, or a better way of doing something. If you try it and something doesn't make sense, please let me know. Feedback from other people's homes and devices will help make it more useful.

You can [report a bug or suggest an idea here](https://github.com/squizzer73/ha-person-presence/issues).

## Before you start

Version **0.3.0b1** is a public beta. [Download the prerelease](https://github.com/squizzer73/ha-person-presence/releases/tag/0.3.0b1), or use the Marketplace button above to add it as a custom repository. It isn't in the shared catalog yet.

You'll need **Home Assistant Core 2026.11 or later**. Testing currently targets 2026.11.0; later releases need compatibility checks. Existing integrations such as the Companion app, iCloud3 and Bermuda supply the observations. Person Presence doesn't add a cloud tracking account or send commands to your devices. Optional place lookup requires a separately configured service and explicit enablement.

## Family card, travel and optional places

This beta adds a bundled **Person Presence** family card, **Distance from home**, **Travel direction**, optional **Place description**, and source suggestions based on existing Person assignments. It also includes separate charging-status timeouts, to better accommodate providers such as iCloud3.

The card clearly separates current, last-known and unknown locations. It can show the selected device, distance/direction and an approximate place label. It does not change existing dashboards or Person assignments. See [family card and travel setup](docs/family-features.md).

Distance and direction use fresh accepted GPS from the selected device. Room updates cannot renew an old GPS fix. A device switch resets movement direction, and old locations remain dashboard history rather than current travel information.

Place lookup is optional and **off by default**. It requires your own authorized or self-hosted Nominatim-compatible service; no public endpoint is bundled. Enabling it sends rounded outdoor coordinates to that service. Existing zones and room names still take precedence, and external labels never change tracking decisions.

## Setup

Add the repository using the Marketplace button above. Select beta/prerelease versions if your client hides them. Alternatively download the install ZIP from the release page and use the manual steps below.

1. Install `custom_components/person_presence` from the candidate ZIP into your HA configuration directory, then restart HA.
2. Open Settings → Devices & services → Add integration → Person Presence.
3. Select an existing Person (a login is not required), name a logical device and select its type.
4. Choose filtered sources, or advanced manual mapping for a generic provider. GPS, charging and room entities for the same physical device may belong to different HA registry devices. Confirm each mapping; similar names do not establish identity.
5. Set preference and charging/wearing rules, review the preview, then Save.
6. Open the new per-person device page to see all current readings. Add another entry for each person.

Configure later to add/edit/remove devices, move their preferences, adjust advanced limits and preview unsaved changes. Deleted source entities create a Repair that links back to configuration. A preview does not save an entry or change current tracking.

## What you get

**Dashboard whereabouts** is the one I would use for a display that stays useful between location updates. It shows the current answer when there is enough fresh information. Otherwise, it shows the last accepted location with an explicit **“(last known)”** label and its original observation timestamp. That history survives a restart. The [dashboard history example](docs/dashboard-history.md) shows how to display its age too.

**Whereabouts** remains the strict current-location sensor. Use this one and its attributes for current-location automations; it can correctly become Unknown while the dashboard still shows an older, labelled location.

**Whereabouts** reports the accepted current location. It shows a room name when there is fresh room information at home, Home when only home is known, a zone name when away in a known zone, Away elsewhere, or Unknown when there isn’t enough reliable information.

Use `presence` (`home` / `away` / `unknown`), `context` (`room` / `zone` / `home` / `away` / `unknown`), `area_id` and `zone_id` for automations. A room and a zone can have the same displayed name. Other attributes identify the selected logical device, source entity, confidence category, wearing status and settling. Confidence is not a numerical probability or proof the device is carried.

Location, Room, Selected device and Decision remain available. The optional tracker and the Last known whereabouts / Last observation time diagnostics are disabled by default. Those legacy diagnostics keep their memory-only behaviour for the current HA run. The new Dashboard whereabouts history is stored separately across restarts and is never substituted for the strict current answer. Volatile timing details are available in diagnostics/preview; unchanged heartbeats do not publish new semantic state.

The integration remains independent of existing Person assignments and automations. Enabling or attaching its optional tracker is a separate user decision. It does not automatically take over household tracking.

## Using iCloud3

One thing that came up while using this was the gap between how often a provider updates and how long a location should count as current. If a phone is sitting in a zone and iCloud3 checks it every 30 minutes or two hours, our default five-minute GPS limit will expire between checks. That doesn't necessarily mean the integration has stopped working.

The new Dashboard whereabouts sensor is there for that situation: it can say **Gym (last known)** and retain the original observation time, while the current Whereabouts sensor says Unknown. It needs at least one accepted observation after upgrading before it has history to keep; it won't copy an already-rejected old fix into a new person's history.

If you're using iCloud3, have a look at the device's **in-zone interval**, its configured Apple device and Companion App mapping, and the actual age of the location it is receiving. iCloud3 can use Apple and Companion App data, and its tracking schedule depends on the device and location. See the [iCloud3 documentation](https://github.com/gcobb321/icloud3).

It may be worth trying a shorter in-zone interval on one phone first, then checking update behaviour and battery use before changing everything. More polling doesn't guarantee Apple will return a newer location. If a device only has a Companion App source, its background location updates need to be working too.

Person Presence uses iCloud3's actual location observation time, not simply the time HA last updated the entity. Increasing the age limit just to keep the sensor populated also makes it willing to accept older information as current, so think about the behaviour you want before changing it. Charging and wearing signals can expire separately as well.

Installing Person Presence doesn't change iCloud3 settings, request extra location updates or fix the provider's delivery. For a watch-only trip, the watch's provider still needs to supply an independent outdoor fix.

## Rules and limits

**Separate charging-status timeouts:** charging status has a separate bounded age. iCloud3 defaults are 30 minutes for wearables and 150 minutes for other devices, with the shared signal age used if longer. Other providers retain the shared signal-age limit. Device rules offer an automatic/custom choice; the numeric charging age is used only with custom enabled. Longer windows tolerate delayed charging reports but also take longer to expire when a provider stops reporting. GPS, room, wearing and local-guard limits are unchanged, and not charging still does not prove worn.

Confirmed worn evidence takes precedence; otherwise lower preference numbers come first. Charging wearables and explicitly unworn devices are excluded. Configured eligibility signals that cannot be assessed exclude the device with an uncertainty explanation. Without a worn sensor, a watch left on a table may still be selected. Not charging does not prove worn.

Phones remain eligible while charging by default, because they may charge in a car or pocket. Turn on charging exclusion only where that matches your use. A confirmed-worn device without a fresh location prevents a confident fallback to an abandoned phone.

Defaults: GPS age 300 seconds, room age 60 seconds, wearing/local signal age 600 seconds, settling 15 seconds and GPS error up to 100 metres. Older entries retain their configured limits. A newer entity update is not necessarily a newer observation: iCloud3 uses its actual located timestamp. Provider/report-only timestamps carry a quality limitation. Ambiguous or nonexistent local timestamps are rejected rather than guessed.

Bermuda room reports are estimates. Use its matching local home/away tracker as a guard; report time alone is not proof of a new radio sighting. Away evidence suppresses an older room, and equal-time contradictory room/away evidence yields Unknown. No Bluetooth disappearance can identify a woodland zone: that needs a fresh outdoor fix from the carried device's existing provider.

## Testing and upgrades

Trying the beta? Start with the [testing guide and feedback checklist](docs/beta-testing.md). Phone-only results, successful tests, confusing setup steps and suggestions are all welcome.

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

I'm [@squizzer73](https://github.com/squizzer73). Suggestions, bug reports, changes and ideas are all welcome. If you're reporting a problem, let me know what you expected, what actually happened, which providers you're using and roughly how long the updates took. Please use fictional names and leave out real coordinates, credentials and Bluetooth identity keys.

See [support](SUPPORT.md), [contributing](CONTRIBUTING.md) and [security reporting](SECURITY.md) for the details.

## Licence

[MIT](LICENSE). Copyright © 2026 squizzer73.
