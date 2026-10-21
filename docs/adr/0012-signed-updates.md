# 0012 — Updates signed by the author, outside GitHub

**Status**: accepted on 2026-10-19 (step E2 of the roadmap, JobHunter 2.18.0).
Active as soon as the author has published their public key (`signature.CLE_PUBLIQUE`):
published in JobHunter 3.11.0 (2026-10-21).

## Context

The update downloads executable code: the ZIP of a tag (installation from
sources) or `JobHunterSetup.exe` (installed application). HTTPS proves that the bytes
come from GitHub, not that they come from the author. A stolen GitHub account, a hijacked
workflow token or a compromised action would publish a booby-trapped version that every
installation would pick up at the next launch.

The Sigstore provenance attestation (2.10.1) proves that an executable comes out of the repository's
workflow; it does not protect against a compromised repository, and the application does not verify it.

Options ruled out:
- **tufup**: its purge of the destination folder is incompatible with a folder that
  contains user data, and it brings a TUF repository format to host;
- **WinSparkle**: Windows only, and its DSA/EdDSA signature is the same idea with a
  C library on top;
- **Authenticode signature**: paid certificate, and does not cover the sources ZIP;
- **signature done by the CI**: the key would be a repository secret, hence within reach of
  whoever compromises the repository — exactly the case to cover.

## Decision

- **Ed25519 in pure Python** (`jobhunter.signature`, RFC 8032 section 6, the RFC's vectors
  in tests): no new dependency, neither in the package nor in the installer.
- **The private key never leaves the author's computer** (`~/.jobhunter/cle_signature`,
  created by `tools/signature.py cle`). The public key is written in the code.
- **A manifest is signed**, not an archive: the version, the SHA-256 fingerprint of each
  file in the tag's ZIP, and that of `JobHunterSetup.exe`. The ZIPs that GitHub
  produces are not guaranteed to be identical byte for byte; their content is. The signed
  manifest is attached to the release (`signature.json`), after the installer's CI.
- **On installation**:
  - sources: the ZIP of the announced version's tag; each file must have its signed
    fingerprint, none may be missing or added; otherwise nothing is written;
  - application: the installer must have the signed fingerprint; otherwise it is not opened.
    Once verified, it is opened normally: the user moves it forward.
- **No going backwards**: the manifest carries its version, which must be the one
  announced; an old valid signature does not cause an old version to be reinstalled.
- **Transition**: as long as `CLE_PUBLIQUE` is empty, the update works as before and says
  so; the application checks at least the installer's published fingerprint. The first
  version that carries the key is installed without a signature (it does not have one yet); all
  the following ones require it.

## Consequences

- Publishing a version takes one more step, on the author's side:
  `uv run python tools/signature.py signer X.Y.Z --publier`, once the CI has finished.
  A release without `signature.json` is refused by installations that have the key.
- **Losing the private key** prevents any automatic update: every installation
  would have to take the installer by hand. The author backs it up off the computer.
- A repository cloned with git (developer) is not concerned: `git pull` follows the repository.
