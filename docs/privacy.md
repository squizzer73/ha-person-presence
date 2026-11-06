# Privacy

Person Presence processes existing HA entity states locally. It sends no telemetry, does not request device locations or account credentials, and creates no external service connection.

Normal entity states and history can reveal sensitive room/zone information. HA permissions and recorder settings govern access and retention. Last-known data is in memory for the current run; restarting does not restore a current presence assertion.

The integration-owned diagnostics payload is allowlisted. Home Assistant wraps it with its own system/integration metadata and internal configuration-entry identifiers; review the complete download before sharing. They omit real entity/device/person names and identifiers, coordinates/home geometry, account data, Bluetooth addresses/IRKs, raw payloads and free-form notes. Consistent aliases allow sources to be compared within one export. Reason codes and boolean quality flags remain useful for troubleshooting.
