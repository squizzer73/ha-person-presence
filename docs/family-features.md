# Family card, travel context and optional places

These features are included in the 0.3.0b1 beta. Restart Home Assistant after upgrading. Existing dashboards are preserved; add the family card where you want it.

## Card

In storage-mode Lovelace the integration registers its local module resource once. YAML resources or unavailable resource APIs need a manual module resource:

```yaml
url: /person_presence/person-presence-card.js?v=0.3.0b1
type: module
```

Add Person Presence from the card picker, or use:

```yaml
type: custom:person-presence-card
title: Family
people:
  - person.river
  - person.morgan
show_device: true
show_travel: true
show_place: true
```

The visual editor accepts comma-separated Person IDs in display order and optional explicit Dashboard whereabouts sensor IDs. The YAML `entities` list overrides `people`, useful if discovery is ambiguous. Entity names can be changed freely: discovery uses association attributes, not entity-ID spelling. Non-admin display needs HA states only. Tapping a row opens its sensor's more-info dialog. No dashboards are created or overwritten.

Current, Last known and Unknown have distinct labels. Last-known rows show original observation age, and do not show travel/place as current. An unavailable/missing source displays Unknown. The card loads no external libraries, fonts or tiles; person pictures use same-origin HA paths only. Card text currently uses English.

## Distance and direction

Distance from home is a numeric HA distance sensor relative to zone.home, supporting HA unit conversion. Travel direction is `towards_home`, `away_from_home`, `stationary` or `unknown`, with an eight-point compass bearing attribute. It describes radial movement, not route, ETA or speed.

A first measurement has unknown direction. Compare distinct actual GPS observations of the same selected device within the GPS age window. Ignore duplicate fixes, including reevaluation caused by BLE room reports. Changes below max(50 metres, the two accuracy radii added together) count as stationary. A device switch, restart, changed home coordinates or expired evidence resets the baseline. Room-only evidence, settling and missing/old GPS produce unknown travel output; dashboard history never supplies current coordinates.

## Optional place lookup

Open Configure → Optional place lookup. One entry owns the shared endpoint/contact configuration; other people have their own enable toggle. Editing a preview makes no changes until Save. To remove the endpoint, clear its URL in the owner entry and save; all lookup requests/results are invalidated. A different owner can then configure the service.

Provide an authorized Nominatim-compatible `/reverse` endpoint. HTTPS is required except explicitly permitted local self-hosted HTTP. Confirm you are authorized to send automated location requests. The public OSMF Nominatim endpoint is rejected; its public-service policy is unsuitable as a bundled automatic household backend. No hosted provider is recommended or preconfigured.

Only fresh accepted GPS outside known zones is submitted, rounded to four decimal places. Requests are serialized across people, at least two seconds apart, with a 12-second lookup timeout and ten-minute backoff after transport/provider errors. The service's own terms still apply. Reverse geocoding describes an approximate address/place; it cannot prove someone entered a building.

Place description is a separate optional output. Errors preserve normal Away tracking. Attribution returned by the provider is shown alongside the label in the card. Replies for an obsolete source, disabled lookup or expired location are ignored.

The private cache retains rounded coordinates/labels for at most 30 days and 1000 records, shared installation-wide. This remains sensitive location information even though it is not a journey archive. `person_presence.clear_place_cache` requires an administrator (or a trusted automation) and deletes it without deleting dashboard last-known history. Changing service configuration also invalidates cached descriptions. Disabling lookup for one person does not erase the shared cache or another person's settings.

## Suggested mappings

Assigned Person trackers rank first, then associated registry devices. Provider and suggestion basis are displayed. Related charging/room suggestions require review. Two providers can represent the same phone; neither similar names nor registry suggestions prove a device is carried. No logical devices are silently created, and existing Person assignments remain unchanged.
