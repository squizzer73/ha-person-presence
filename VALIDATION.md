# Validation — 0.2.0b2

## Automated checks

75 tests pass locally on stable Home Assistant Core 2026.11.0 / Python 3.14.8 in a clean task-owned environment, with Ruff lint/format and mypy covering 16 source modules. The standalone export is validated separately before publication.

The suite covers source decisions, freshness and ambiguous timestamps, canonical places, guided configuration, repairs, privacy redaction and deterministic packaging. New checks cover current versus historical dashboard output, original timestamp preservation through reload, stored-file readback, malformed/future/wrong-person/source-remapped restore rejection and entry deletion cleanup. Real SQLite recorder checks include fresh heartbeats and repeated stale-age evaluation. The documented dashboard card renders current, last-known, Unknown and Unavailable cases inside HA.

An independent static review of the new history implementation reported no actionable correctness/privacy defects after the documentation clarification. A separately approved household pilot loaded all entries with existing entity IDs, settings, user enablement choices, Person assignments and dashboard profiles preserved. Native device pages and the configuration preview passed read-only browser checks. Live history files were observed after accepted readings. Cross-restart history restoration was tested in isolated HA; no additional live restart was performed solely for this check. Physical accuracy and provider coverage remain field-validation tasks.

## Public release evidence

The 0.2.0b1 release passed tests/build, hassfest and Marketplace validation; its published ZIP and checksum were downloaded and verified. The same three jobs must pass for the exact 0.2.0b2 release commit before the publishing workflow runs. Prepared workflows and local tests are not evidence of that external run. The publication receipt and Actions run identify the final tagged commit.

## Privacy and limits

Only the exact release-file manifest is exported. Private household configuration, backups, credentials, deployment scripts and live screenshots are excluded. Retained display history is stored privately inside the user's HA configuration, never substituted for current presence or included in the integration-owned diagnostic payload. GitHub private vulnerability reporting is enabled and linked in SECURITY.md.

History requires a previously accepted observation: an old rejected provider location does not create a history record. Physical accuracy, wearing detection, watch-only location coverage and observed delays require separate field testing. No Marketplace catalog acceptance is claimed. The macOS dependency inventory is recorded in requirements-test.lock; CI installs requirements-test.txt for its own platform.
