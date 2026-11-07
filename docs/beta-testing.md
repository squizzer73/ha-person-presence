# Trying the beta

Thanks for giving Person Presence a try. I'm interested in how it works in other people's homes, with different devices and tracking integrations. A phone-only setup is just as useful to hear about as a phone and watch.

The main question is: **does Whereabouts follow the person when their devices aren't all in the same place?** Setup feedback, confusing descriptions, bugs and ideas are welcome too.

## Before you start

- Back up before installing or upgrading. Start with one person, then add others once the setup makes sense.
- Note your Person Presence version, Home Assistant Core version and source integrations.
- Check each device's mappings, preference order and charging/wearing rules. Check that the selected sources describe that physical device.
- Open the person's device page so you can see **Whereabouts**, **Selected device** and **Decision** together.
- Use Configure → Review and save to see an unsaved preview with source ages and explanations. Close it without saving if you only want to inspect the current setup.

Compare with where you actually are. A location sensor displaying the expected text doesn't by itself prove that it followed your movement.

## Things to try

Skip anything your setup can't support and tell me what was missing. Don't add artificial wearing or location signals just to make a test pass.

| Check | What to do | What to look for |
| --- | --- | --- |
| Phone only | Carry the phone between rooms, then leave home. | Rooms need a suitable room source. Outdoors needs fresh geographical observations. Home/Away or a zone may be all your sources support. |
| Devices together | Carry your phone and wear your watch between rooms. | Whereabouts should follow fresh room evidence after the configured settling period. Selected device and Decision should explain the choice. |
| Watch charging elsewhere | Leave the watch charging in one room and carry the phone elsewhere. | Once charging is reported, the watch should be excluded and the phone followed if it has fresh evidence. |
| Phone left elsewhere | Leave the phone in one room and wear the watch in another. | With a working worn signal, the watch should take precedence. Without one, preference and other available signals decide; note that limitation in your feedback. |
| Watch-only trip | Leave the phone at home and take the watch outside. | A zone requires a fresh outdoor fix from the watch's provider. Note whether that provider updates without the phone. Bluetooth disappearance alone can't identify a destination. |
| Watch removed | Leave the watch on a table without charging it. | A real unworn signal should exclude it. Without one, it may still be selected: not charging does not prove worn. |
| Stale or unavailable source | Observe a normal source outage or an old location fix. | Old observations shouldn't become fresh merely because HA updates the entity. Whereabouts may correctly become Unknown; a fresh eligible alternative may be selected. |
| Multiple people | Add a second person and inspect both device pages. | Separate devices, mappings and outputs, with no changes to existing Person tracker assignments. |

If you are already planning a restart, also check that your mappings and user enablement choices survive it. Last-known diagnostics start empty after a restart; they aren't a restored current location.

## Record the delay, not just the result

Write down roughly when you moved, when the source changed and when Whereabouts changed. There isn't one fixed end-to-end delay: the provider's update interval comes first, then the integration's settling period (15 seconds by default). Check your configured limits rather than assuming everyone uses the defaults.

If the answer looks wrong, compare the source room/location, charging and worn states, their observation ages, and Decision. This helps separate an inference problem from missing or delayed provider information. Unknown can be the correct answer when evidence is stale, conflicting or insufficient.

## Send feedback

Use the [beta feedback form](https://github.com/squizzer73/ha-person-presence/issues/new?template=beta_feedback.yml) for results, including tests that worked. Use the [bug form](https://github.com/squizzer73/ha-person-presence/issues/new?template=bug_report.yml) for a specific failure, or suggest an idea through [Issues](https://github.com/squizzer73/ha-person-presence/issues).

You can copy this checklist into a report:

```text
Person Presence / HA Core versions:
Devices and source integrations:
Preference order and charging/wearing rules:
Is a real worn/on-body signal available? Yes / No / Not applicable
Scenario tried:
What I did (use fictional rooms/people):
What I expected:
Whereabouts / Selected device / Decision actually showed:
Source states and approximate observation ages:
Delay until source updated / delay until Whereabouts updated:
Result: Worked / Unexpected / Could not test
Can I reproduce it?
Suggestions or anything confusing:
```

Use fictional names and places. Leave out coordinates, routes, credentials, Bluetooth identity keys and raw provider payloads. Screenshots can expose names, maps or other private information, so crop/redact them before sharing. Diagnostics are optional: inspect the whole download, including metadata HA adds, before posting it. See [privacy](privacy.md) and [security reporting](../SECURITY.md).

## Family-features candidate checks

Check card rows at mobile and desktop widths, renamed sensors, last-known age and unavailable sources. For travel, compare real consecutive GPS reports with device switches and expiry; BLE room updates alone must not change direction. Confirm place lookup is off after upgrade. If you have an authorized service, test endpoint configuration, attribution, timeout/disable and the admin cache-clear action without sharing coordinates or endpoint details in public reports. Existing Person assignments and dashboards must remain unchanged.
