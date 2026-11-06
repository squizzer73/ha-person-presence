# Changelog

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
