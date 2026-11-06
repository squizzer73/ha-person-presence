# Privacy

Person Presence processes existing HA entity states locally. It sends no telemetry, does not request device locations or account credentials, and creates no external service connection.

Normal entity states and history can reveal sensitive room/zone information. HA permissions and recorder settings govern access and retention. The legacy last-known diagnostic remains in memory for the current run. Dashboard whereabouts keeps one accepted location, original observation timestamp and person/source entity IDs in private HA storage per entry so the display can survive a restart. It contains no coordinates or device keys, is removed when the entry is deleted, and is rejected if its person/source mapping no longer matches. Restoring it never restores a current presence assertion.

The integration-owned diagnostics payload is allowlisted. Home Assistant wraps it with its own system/integration metadata and internal configuration-entry identifiers; review the complete download before sharing. They omit real entity/device/person names and identifiers, coordinates/home geometry, account data, Bluetooth addresses/IRKs, raw payloads and free-form notes. Consistent aliases allow sources to be compared within one export. Reason codes and boolean quality flags remain useful for troubleshooting.
