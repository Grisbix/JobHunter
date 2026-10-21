"""The winget manifests of a published version, for microsoft/winget-pkgs.

    uv run python tools/winget.py 3.13.0            # writes dist/winget/3.13.0/
    winget validate --manifest dist/winget/3.13.0   # Windows' own check

Why winget. The installer is not Authenticode-signed (no paid certificate; SignPath
refused the project), so a browser download meets SmartScreen's « Windows a protégé
votre ordinateur ». A package manager downloads the installer itself: the file has no
Mark of the Web, and `winget install Grisbix.JobHunter` installs without that warning.
winget also checks the SHA-256 written here, which is the one the release CI published
next to the installer — this script refuses a version whose checksum is not published.

The installer is the Inno Setup one, per user (no administrator rights); its AppId is
fixed in `tools/installer/JobHunter.iss`, hence the ProductCode `{AppId}_is1` that lets
winget recognise an installation made without it.
"""

import argparse
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

from jobhunter.network import exiger_http  # noqa: E402
from jobhunter.programs import update as maj  # noqa: E402

ID = "Grisbix.JobHunter"
SCHEMA = "1.9.0"
APP_ID = "{6E3F2A41-7C1B-4F0E-9A3D-4B8C5D2E1F70}"  # tools/installer/JobHunter.iss
DEPOT_URL = f"https://github.com/{maj.DEPOT}"


def _entete(type_: str) -> str:
    return f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.{type_}.{SCHEMA}.schema.json\n"


def manifestes(version: str, sha256: str) -> dict[str, str]:
    """{file name: content} of the three manifests (version, installer, locale)."""
    url = maj.ASSET_URL.format(version, maj.SETUP)
    commun = f"PackageIdentifier: {ID}\nPackageVersion: {version}\n"
    return {
        f"{ID}.yaml": _entete("version")
        + commun
        + f"DefaultLocale: en-US\nManifestType: version\nManifestVersion: {SCHEMA}\n",
        f"{ID}.installer.yaml": _entete("installer")
        + commun
        + "InstallerType: inno\n"
        + "Scope: user\n"
        + "InstallModes:\n- interactive\n- silent\n- silentWithProgress\n"
        + "UpgradeBehavior: install\n"
        + f"ProductCode: '{APP_ID}_is1'\n"
        + f"ReleaseDate: {_date(version)}\n"
        + "Installers:\n"
        + "- Architecture: x64\n"
        + f"  InstallerUrl: {url}\n"
        + f"  InstallerSha256: {sha256.upper()}\n"
        + f"ManifestType: installer\nManifestVersion: {SCHEMA}\n",
        f"{ID}.locale.en-US.yaml": _entete("defaultLocale")
        + commun
        + "PackageLocale: en-US\n"
        + "Publisher: Grisbix\n"
        + "PublisherUrl: https://github.com/Grisbix\n"
        + f"PublisherSupportUrl: {DEPOT_URL}/issues\n"
        + "PackageName: JobHunter\n"
        + f"PackageUrl: {DEPOT_URL}\n"
        + "License: MIT\n"
        + f"LicenseUrl: {DEPOT_URL}/blob/main/LICENSE\n"
        + "ShortDescription: Assisted job search - collects offers, ranks them against your "
        "profile, prepares a tailored CV and cover letter.\n"
        + "Description: |-\n"
        + "  JobHunter collects job offers from company career pages, official job APIs and\n"
        + "  job boards, scores each one against your own profile and prepares a tailored CV\n"
        + "  and cover letter for the best ones. Everything stays on your computer: no\n"
        + "  account, no server, no telemetry. It never sends an application on its own.\n"
        + "Moniker: jobhunter\n"
        + "Tags:\n- job-search\n- cv\n- cover-letter\n- career\n- resume\n"
        + f"ReleaseNotesUrl: {DEPOT_URL}/releases/tag/v{version}\n"
        + f"ManifestType: defaultLocale\nManifestVersion: {SCHEMA}\n",
    }


def _date(version: str) -> str:
    """The release date from the CHANGELOG heading (« ## 3.13.0 — 2026-10-21 »)."""
    for ligne in (RACINE / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
        if ligne.startswith(f"## {version} "):
            return ligne.rsplit(" ", 1)[1]
    raise SystemExit(f"{version} absente du CHANGELOG")


def sha_publie(version: str) -> str:
    url = maj.ASSET_URL.format(version, maj.SETUP + ".sha256")
    req = urllib.request.Request(exiger_http(url), headers={"User-Agent": "JobHunter-winget"})
    with urllib.request.urlopen(req, timeout=60) as r:  # nosec B310 : scheme checked
        return bytes(r.read()).decode().split()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("version")
    a = ap.parse_args()
    sortie = RACINE / "dist" / "winget" / a.version
    sortie.mkdir(parents=True, exist_ok=True)
    for nom, texte in manifestes(a.version, sha_publie(a.version)).items():
        (sortie / nom).write_text(texte, encoding="utf-8")
    print(f"Manifestes winget écrits : {sortie}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.exit(main())
