# Validation — 0.4.0b1 candidate

Local checks: 128 Python tests, four Node card tests, Ruff lint/format and mypy across 23 modules pass. Native isolated HA flows cover shared settings, persisted keys, explicit Test/Skip, blank-key retention, removal, unsaved drafts and concurrent-editor rejection. Tests use fictional keys and synthetic responses; no real Geoapify account or household coordinates were sent. Independent review found a draft reset defect, fixed with two native HA regressions. Public CI and live evidence will be recorded after those steps.

# Validation — 0.3.0b2

115 Python tests and three Node card tests pass locally, with Ruff lint/format and mypy20 modules. Eleven focused regressions cover older away/newer room settling, a GPS fix between accepted/latest rooms, stale-first automatic guards, negative guard precedence, explicit guard preservation, endpoint-specific backoff and same-fix lookup recovery/disable/expiry. The initial regression run reproduced the four bugs before the fixes. An independent review found no material regressions in the scoped fixes. Its three coverage suggestions were added: one-minute retry floor after empty responses, duplicate in-flight request suppression and stopped-runtime suppression. All three external jobs (tests/build, hassfest, Marketplace) passed for tagged source `4cbf35662ffc7e9759267de2a5d8788b5a2d77ef` in [run 42352040290](https://github.com/squizzer73/ha-person-presence/actions/runs/42352040290). [Publisher run 42352196498](https://github.com/squizzer73/ha-person-presence/actions/runs/42352196498) succeeded, and its administration commit passed all jobs in run 42352196480. The public ZIP/checksum, release notes and source target were read back and verified; installed files match the public ZIP.

An authorized backup/install and one restart loaded all six entries with 72 existing registrations, five profiles, six Person assignments and provider settings preserved. No integration errors were reported; the card resource and served bytes were verified. Automated regressions establish the four code fixes; physical presence accuracy and optional real-provider operation still require field observation.

The family card code is unchanged. Existing source mappings, entities and freshness limits remain unchanged by these fixes. Optional lookup stays off unless explicitly enabled.

# Validation — 0.3.0b1

104 Python tests pass in isolated HA/pure harnesses, with three Node card-model tests. Ruff lint/format and mypy (20 modules) pass. Synthetic Chromium browser checks cover a fictional seven-person household at 390px and 900px, current/last-known/unknown displays, more-info, editor changes and text escaping; both screenshots were visually inspected. This is not a live HA frontend or physical presence acceptance check.

Independent review identified concurrent frontend registration, fragmented JSON response handling and retention depending on future lookup requests. Each received a failing regression and a fix. Additional tests prove resource setup can retry without registering the route twice, and expired cache data is removed from private storage without new requests and during startup. Optional endpoint changes remain preview-only until Save; enabling without any configured service is rejected. Existing legacy entries and registry choices remain covered by six-person upgrade tests.

An explicitly approved household pilot installed this exact runtime with one restart. All six entries loaded; 54 existing registrations, five dashboard profiles, six Person assignments and provider settings were preserved. Eighteen sensors were added (72 registrations total, 54 enabled); no enabled entities were missing or unavailable. The card resource was registered once and its served bytes matched the tested build; the integration reported no errors. Browser access was disabled, so no live frontend rendering claim is made. No real geocoding provider or API credentials were used; lookup stayed off. Physical accuracy, watch-only provider coverage and broader household testing remain ongoing. External tests/build, hassfest and Marketplace jobs passed for the exact tagged commit in [run 42324172437](https://github.com/squizzer73/ha-person-presence/actions/runs/42324172437). [Publisher run 42324358041](https://github.com/squizzer73/ha-person-presence/actions/runs/42324358041) succeeded. The public ZIP/checksum, tag and release-note body were read back; installed runtime bytes match the public ZIP. The initial manifest key-order failure was corrected and regression-tested before the successful run. See PUBLICATION.md for commit/checksum evidence.

# Local 0.2.0b3 charging-window candidate

83 tests pass locally, including provider cadence boundaries, explicit charging exclusion, unavailable/invalid source values, unknown-provider compatibility, custom overrides, malformed limits, unchanged wearing expiry and a real-HA automatic/custom options round-trip. The independent review identified automatic limits being pinned by form defaults; an explicit custom toggle now preserves and restores automatic mode. Mutation of the fix back to unconditional save reproduced the intended options assertion failure. Lint, formatting and type checks cover the candidate.

At the original b3 validation point the candidate was local only. A later explicitly approved pilot installed b3 with one restart and preserved the existing configuration. Source mappings were preserved during that pilot. The b3 charging fix is included in this newer candidate.

# Validation — 0.2.0b2

## Automated checks

75 tests pass locally on stable Home Assistant Core 2026.11.0 / Python 3.14.8 in a clean task-owned environment, with Ruff lint/format and mypy covering 16 source modules. The standalone export is validated separately before publication.

The suite covers source decisions, freshness and ambiguous timestamps, canonical places, guided configuration, repairs, privacy redaction and deterministic packaging. New checks cover current versus historical dashboard output, original timestamp preservation through reload, stored-file readback, malformed/future/wrong-person/source-remapped restore rejection and entry deletion cleanup. Real SQLite recorder checks include fresh heartbeats and repeated stale-age evaluation. The documented dashboard card renders current, last-known, Unknown and Unavailable cases inside HA.

An independent static review of the new history implementation reported no actionable correctness/privacy defects after the documentation clarification. A separately approved household pilot loaded all entries with existing entity IDs, settings, user enablement choices, Person assignments and dashboard profiles preserved. Native device pages and the configuration preview passed read-only browser checks. Live history files were observed after accepted readings. Cross-restart history restoration was tested in isolated HA; no additional live restart was performed solely for this check. Physical accuracy and provider coverage remain field-validation tasks.

## Public release evidence

The 0.2.0b1 release passed tests/build, hassfest and Marketplace validation; its published ZIP and checksum were downloaded and verified. The same three jobs passed for the exact 0.2.0b2 release commit `60b4e04c6e5ddaf42c56256a64937f7020126fd7` in [run 42217187794](https://github.com/squizzer73/ha-person-presence/actions/runs/42217187794). The published b2 ZIP, checksum, tag and release-note body were independently downloaded/read back and verified after [publication run 42217311990](https://github.com/squizzer73/ha-person-presence/actions/runs/42217311990) succeeded. The publishing-administration commit also passed all three jobs in run 42217312012.

## Privacy and limits

Only the exact release-file manifest is exported. Private household configuration, backups, credentials, deployment scripts and live screenshots are excluded. Retained display history is stored privately inside the user's HA configuration, never substituted for current presence or included in the integration-owned diagnostic payload. GitHub private vulnerability reporting is enabled and linked in SECURITY.md.

History requires a previously accepted observation: an old rejected provider location does not create a history record. Physical accuracy, wearing detection, watch-only location coverage and observed delays require separate field testing. No Marketplace catalog acceptance is claimed. The macOS dependency inventory is recorded in requirements-test.lock; CI installs requirements-test.txt for its own platform.
