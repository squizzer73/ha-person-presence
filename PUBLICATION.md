# Public beta publication status

## Confirmed decisions

- Repository: `squizzer73/ha-person-presence` (public repository created by the owner on 6 November 2026).
- Display name and integration domain: Person Presence / `person_presence`.
- Maintainer: `@squizzer73`.
- Licence: MIT, approved by the owner on 6 November 2026; notice included in both the repository and install ZIP.
- Distribution: prepare a public custom-repository beta before catalog submission.

## Prepared locally

Manifest documentation and issue URLs target the approved repository. Support and contribution guidance, bug/feature issue forms, an original teal person/location icon and least-privilege validation workflow are included. The release-file allowlist excludes household deployment files, live screenshots, private configuration and credentials.

## Still required

The approved 59-file export is uploaded to the public repository. The owner added the description and topics; issues are enabled. No household files are included.

GitHub hassfest and the test/build job passed at commit `7445f51b193250dec1de9f352a63a454e7d4b583`. Marketplace validation also passed after the metadata correction. No checks were ignored.

1. Retain green validation for the release commit.
2. Verify repository metadata and enable GitHub private vulnerability reporting before advertising a private reporting URL.
3. Record final external validation results before publishing a packaged release.
4. Obtain approval for the concrete public repository/release contents, then publish a full GitHub prerelease with the versioned install ZIP and checksums. A tag alone is not a release.
5. Distribute a custom-repository link and collect field feedback. Catalog submission is a separate step after the required checks pass.

Field acceptance remains incomplete, especially wearing detection and watch-only outdoor provider updates. Do not describe this beta as physically proven or catalog approved. The existing household pilot is unchanged by these local preparation edits.

Requirements checked on 6 November 2026:

- https://contributors.home-assistant.io/marketplace/reference/repository-structure/
- https://contributors.home-assistant.io/marketplace/guides/catalog/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/reference/validation/
