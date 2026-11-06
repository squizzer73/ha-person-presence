# Contributing

Open an issue to discuss substantial behaviour changes before implementation. Preserve the person_presence domain, existing entity/device identities, explicit user settings and the read-only relationship to source providers. Do not add household-specific names, entity IDs, locations or credentials.

Use the commands in README.md to run tests, lint, format and type checks. Add focused regressions for changed decisions, timestamp interpretation or provider capabilities. Use fictional households and temporary HA instances. Do not connect automated tests to a live home.

Update documentation, translations and release notes where relevant. New distributable files must be explicitly added to release-files.json; test the standalone export. CI must pass hassfest and HACS validation without ignored checks before publication.

Physical behaviour and provider coverage are separate from automated test results. Describe what was actually tested and what remains unverified.
