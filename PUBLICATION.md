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

[0.2.0b2 is published](https://github.com/squizzer73/ha-person-presence/releases/tag/0.2.0b2), following the owner's approval on 6 November 2026. It tags commit `60b4e04c6e5ddaf42c56256a64937f7020126fd7`, validated by [run 42217187794](https://github.com/squizzer73/ha-person-presence/actions/runs/42217187794). All three required jobs passed; no checks were ignored.

[Publication run 42217311990](https://github.com/squizzer73/ha-person-presence/actions/runs/42217311990) built the pinned commit, verified the expected install checksum, attached both assets and published the prerelease. The tag, public download bytes, checksum and release notes were independently read back. Install ZIP SHA256: `c49a555ab399c5d493d43a882fa5e9a24b538310d3f6e4d5334959dfa4956130`. See [what changed](docs/releases/0.2.0b2.md).

The validated release branch `codex/release-0.2.0b2` provides the existing commit reference required by GitHub's workflow-scope rules for this historical target. No additional credentials or token scope were requested. The initial failed publication made no release; its retry succeeded after the reference was created.

## Remaining work

1. Collect field feedback and verify provider/wearing behaviour.
2. Keep the security policy current. GitHub private vulnerability reporting was enabled by the owner and verified on 6 November 2026; SECURITY.md links to the private report form.
3. Follow the existing catalog submission and decide when field feedback supports a stable release. Maintainer acceptance is outstanding.

Publication runs only on a manual dispatch or a change to the explicit versioned release-request path. Routine documentation changes cannot trigger publication. Future versions need their own approved request, reviewed target, validation evidence and checksum.

Field acceptance remains incomplete, especially wearing detection and watch-only outdoor provider updates. Do not describe this beta as physically proven or catalog approved. The existing household pilot is unchanged by these local preparation edits.

Requirements checked on 6 November 2026:

- https://contributors.home-assistant.io/marketplace/reference/repository-structure/
- https://contributors.home-assistant.io/marketplace/guides/catalog/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/reference/validation/

## 0.3.0b1

[0.3.0b1 is published](https://github.com/squizzer73/ha-person-presence/releases/tag/0.3.0b1), following the owner's approval on 7 November 2026. It tags `8f7ecc0306c166d68356ccb2b7270e1b28b1bf78`, validated by [run 42324172437](https://github.com/squizzer73/ha-person-presence/actions/runs/42324172437). All three jobs passed without ignored checks. The initial manifest-ordering failure was corrected with a packaging regression before publication.

[Publisher run 42324358041](https://github.com/squizzer73/ha-person-presence/actions/runs/42324358041) rebuilt the pinned source, checked the expected checksum, attached the ZIP and SHA256SUMS and published the prerelease. Public download bytes, checksum file, tag and notes were independently verified. ZIP SHA256: `eb8c45562e3b40acd53eae5f90e5e24e0474defa6129b41928c8f1669dfd6e87`. The installed pilot runtime matches this public ZIP. Only manifest key ordering needed synchronization after the prior pilot restart; parsed settings stayed identical and no further restart was needed. The publisher administration commit passed all three jobs in [run 42324357971](https://github.com/squizzer73/ha-person-presence/actions/runs/42324357971).

See [what changed](docs/releases/0.3.0b1.md). Catalog submission [hacs/default#13509](https://github.com/hacs/default/pull/13509) remains open with no maintainer comments/reviews at the release check. The GitHub connector cannot update the upstream PR description (403); updated release/check links are prepared for the owner to paste. Acceptance and physical accuracy are not claimed.
