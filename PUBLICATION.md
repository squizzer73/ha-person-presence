# Public beta publication status

## Confirmed decisions

- Repository: `squizzer73/ha-person-presence` (public repository created by the owner on 6 November 2026).
- Display name and integration domain: Person Presence / `person_presence`.
- Maintainer: `@squizzer73`.
- Licence: MIT, approved by the owner on 6 November 2026; notice included in both the repository and install ZIP.
- Distribution: prepare a public custom-repository beta before catalog submission.

## Distribution files

Manifest documentation and issue URLs target the approved repository. Support and contribution guidance, bug/feature issue forms, an original teal person/location icon and least-privilege validation workflow are included. The release-file allowlist excludes household deployment files, live screenshots, private configuration and credentials.

## Release history

The owner approved publishing the prerelease on 6 November 2026. [0.2.0b1](https://github.com/squizzer73/ha-person-presence/releases/tag/0.2.0b1) tags commit `80b07bd57d134b3a7de52696b793ad4dac780081`, which passed all three required validation jobs in run 42197883378. No checks were ignored.

The publication workflow verified that exact successful run, rebuilt the pinned commit, checked the expected SHA256, attached the install ZIP and SHA256SUMS to a draft, then published it as a prerelease. Both public downloads, ZIP contents, tag and checksum were independently read back. Install ZIP SHA256: `c4b3ae31fcb8680332898bff496e76bdd054331d75ed292be51c4cb8c364d014`.

The public repository has its description/topics and issues enabled. The exact export excludes household deployment files, live screenshots, private configuration and credentials. The README provides a custom-repository Marketplace link; inclusion in the shared catalog is not claimed.

## 0.2.0b2

The owner approved publishing the Dashboard whereabouts changes, README/provider guidance and release notes on 6 November 2026. The release must use an exact commit with passing tests/build, hassfest and Marketplace validation, then publish the install ZIP and SHA256SUMS as a GitHub prerelease. The one-time publisher is pinned to the verified commit and checksum; publication is read back afterward. See [what changed](docs/releases/0.2.0b2.md).

## Remaining work

1. Collect field feedback and verify provider/wearing behaviour.
2. Keep the security policy current. GitHub private vulnerability reporting was enabled by the owner and verified on 6 November 2026; SECURITY.md links to the private report form.
3. Decide when to issue a stable release and request catalog inclusion. Catalog submission remains a separate authorized action.

The historical publishing workflow is now manual-only so routine documentation changes cannot trigger another publication. Future versions need their own reviewed target, validation evidence and checksum.

Field acceptance remains incomplete, especially wearing detection and watch-only outdoor provider updates. Do not describe this beta as physically proven or catalog approved. The existing household pilot is unchanged by these local preparation edits.

Requirements checked on 6 November 2026:

- https://contributors.home-assistant.io/marketplace/reference/repository-structure/
- https://contributors.home-assistant.io/marketplace/guides/catalog/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/reference/validation/
