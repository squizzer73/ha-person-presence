# 0.3.0b1 — 7 November 2026

- Add a bundled family overview card with explicit current/last-known/unknown states, selected-device detail and a visual editor.
- Add GPS-only distance, compass bearing and coarse direction, with independent GPS observation timestamps and baseline resets.
- Add optional authorized-service place descriptions, shared bounded private cache and an admin cache-clear action. No public service endpoint is bundled or enabled.
- Show Person-assignment and registry-based source suggestions without silently creating devices.
- Include the b3 charging-window fix; preserve existing configuration and entity identities. Three additive sensors per entry.

# Changelog

## 0.2.0b3 — local candidate, unreleased

- Separates charging-state freshness from wearing/local-presence freshness.
- Uses bounded iCloud3 charging defaults (30 minutes for wearables, 150 minutes for other devices, or the shared age if longer).
- Adds automatic/custom per-device charging ages, including returning to automatic without changing other signal limits.
- Keeps explicit charging/unworn exclusions and strict location limits; expired, unknown or unavailable required charging signals remain ineligible.

## 0.2.0b2 — public beta, 6 November 2026

- Adds Dashboard whereabouts, which retains accepted locations with an explicit “last known” label when current evidence expires.
- Keeps strict current Whereabouts unchanged; retained history never becomes a current automation assertion.
- Persists the original observation timestamp privately across restarts, validates mappings on restore and removes history with the entry.
- Avoids ticking-age history writes; dashboard templates can render relative age.
- Adds a tested dashboard card example and iCloud3 guidance on source observation times, polling intervals and stale data.
- Adds regressions for history validation, restore, remapped sources, deletion and recorder behaviour.

## 0.2.0b1 — public beta, 6 November 2026

- Adds an additive Whereabouts sensor and independent last-known diagnostics.
- Explains every configured device and equal-time conflicting evidence.
- Adds capability-filtered source choices, manual mapping, rule guidance and unsaved preview.
- Preserves existing entry/entity identities, configuration and disabled flags.
- Adds source Repairs, private diagnostic exports and deterministic standalone packaging.
- Tightens timestamp/contact handling and prevents age-only recorder churn.

- Prepares approved repository/maintainer metadata, MIT licensing, original branding, support guidance and issue forms.

Published as a GitHub prerelease after tests, hassfest and Marketplace validation passed. Physical acceptance and catalog inclusion remain separate milestones.
