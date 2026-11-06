# Candidate validation — 0.2.0b1

This is a locally validated beta candidate. A household pilot is installed separately. The public 0.2.0b1 prerelease is published from validated commit `80b07bd57d134b3a7de52696b793ad4dac780081`. Its downloaded install ZIP and checksum were verified independently.

## Automated evidence

- 71 tests pass on stable Home Assistant Core 2026.11.0, Python 3.14.8, in a clean task-owned environment. No borrowed project dependencies or live HA connection are required.
- Coverage includes phone/watch decisions, conflicting and stale evidence, timestamp ambiguity, capability filtering, canonical room/zone identity, additive Whereabouts, six fictional legacy entries with preserved entity IDs and user enablement choices, repairs, configuration preview, diagnostic redaction and deterministic exports.
- A real temporary SQLite recorder verifies unchanged source heartbeats do not produce repeated semantic history writes. The optional observation-time diagnostic updates independently.
- The shipped notification and automation examples run against real HA templates, including Unknown and Unavailable.
- Ruff lint, formatting and mypy cover the source; the standalone repository export independently passed all 71 tests, lint, formatting and type checks.
- An independent review identified capability, freshness, timestamp-override, settling, place-identity, diagnostic-update and packaging issues. Regression checks cover the fixes; no reported minor findings are deferred.

The dependency inventory in requirements-test.lock records the observed macOS environment. CI installs requirements-test.txt for its own platform; the inventory is not a universal cross-platform lock.

## Scope and remaining gates

Native browser checks passed for the per-person device page, options preview and filtered source form in a localhost-bound fictional household; the preview and form screenshots were visually inspected. Private test credentials, session storage, logs, screenshots and household deployment scripts are excluded from the exact release-file manifest.

Repository identity, documentation/issue URLs and codeowner are now set locally with the owner’s approval. An original icon is included for review. MIT licensing is included with owner approval. The owner approved the prepared public upload and created the repository. Private security reporting and broader field acceptance remain open. GitHub Actions has now passed hassfest and the full Linux test/build job at commit `7445f51b193250dec1de9f352a63a454e7d4b583` (run 42197572188). Marketplace validation also passed after the repository metadata correction, without ignored checks. Catalog approval is separate. Physical tracking accuracy, watch-only location delays and provider coverage require separate field validation. Source providers must supply the needed observations; this integration cannot manufacture an independent Apple Watch outdoor fix.

See PUBLICATION.md for publication requirements and docs/troubleshooting.md for source limitations. The existing household installation remains unchanged.
