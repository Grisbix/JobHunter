#!/usr/bin/env python3
"""Packs the built application (dist/JobHunter) as an MSIX for the Microsoft Store.

    python tools/installer/msix.py            # after build.py: dist/JobHunter.msix

Why: the installer is not Authenticode-signed, so a browser download meets
SmartScreen's « Windows a protégé votre ordinateur ». The Store signs the packages it
distributes with Microsoft's certificate: installed from there, JobHunter opens
without that warning, and the Store installs its updates (jobhunter.frozen.paquet_msix
turns the in-app installer download off).

The package left here is unsigned: it is the file uploaded to Partner Center, which
signs it. It cannot be installed by double-click as is.

Its identity must be the one Partner Center reserved for the app (Product identity
page). It comes from the environment, so that nothing personal is written here:
  MSIX_NOM          Package/Identity/Name           (e.g. 12345Grisbix.JobHunter)
  MSIX_EDITEUR      Package/Identity/Publisher      (e.g. CN=1A2B3C4D-...)
  MSIX_EDITEUR_NOM  Package/Properties/PublisherDisplayName
Without them, placeholders: enough to check the packing, refused by the Store.

Node.js goes back inside the package: the installer leaves Playwright's node.exe out
and the application downloads it at the first browser (jobhunter.playwright_node,
3.62), but the Store's policy 10.2.2 forbids a product to extend itself with code it
downloads. `remettre_node` puts it back from dist/playwright-node-win64.zip, checked
against the build's manifest, which it then removes: the package needs no download.

Needs makeappx.exe (Windows SDK, present on the GitHub Windows runners) and, for
logos at the sizes Windows asks for, Pillow (else the icon is copied unscaled).

Decision: docs/adr/0015-microsoft-store-package.md
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
DIST = RACINE / "dist"
ICONE = RACINE / "src" / "jobhunter" / "assets" / "jobhunter.png"
# File name → side in pixels (scale 100 %).
LOGOS = {"StoreLogo.png": 50, "Square44x44Logo.png": 44, "Square150x150Logo.png": 150}
# The other sizes Windows picks from (3.88). With the three files above only, a screen at
# 150 or 200 % stretched a 44-pixel icon, and the taskbar drew it on a coloured plate
# (audit 2026-11-15). `scale-N`: the same logo for a denser screen. `targetsize-N` with
# `altform-unplated`: the exact icon of the taskbar, the Start list and Alt+Tab, without
# a plate. Windows finds them through resources.pri (makepri), not by their names alone.
ECHELLES = (100, 125, 150, 200, 400)
CIBLES = (16, 24, 32, 48, 256)

MANIFESTE = """<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:uap5="http://schemas.microsoft.com/appx/manifest/uap/windows10/5"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap uap5 rescap">
  <Identity Name="{nom}" Publisher="{editeur}" Version="{version}" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>JobHunter</DisplayName>
    <PublisherDisplayName>{editeur_nom}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="fr-FR" />
    <Resource Language="en-US" />
  </Resources>
  <Applications>
    <Application Id="JobHunter" Executable="JobHunter.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="JobHunter" Description="{description}"
        BackgroundColor="transparent" Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png" />
      <Extensions>
        <!-- jobhunter-cli on the PATH: the scheduled morning collection calls it. -->
        <uap5:Extension Category="windows.appExecutionAlias" Executable="jobhunter-cli.exe"
          EntryPoint="Windows.FullTrustApplication">
          <uap5:AppExecutionAlias>
            <uap5:ExecutionAlias Alias="jobhunter-cli.exe" />
          </uap5:AppExecutionAlias>
        </uap5:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""
DESCRIPTION = "Collecte des offres d'emploi, tri, CV et lettres sur mesure."


def version_msix() -> str:
    """3.33.0 → 3.33.0.0: the Store wants four numbers, the last one 0."""
    v = (RACINE / "VERSION").read_text(encoding="utf-8").strip()
    parties = v.split(".")
    if len(parties) != 3 or not all(p.isdigit() for p in parties):
        raise SystemExit(f"VERSION inattendue : {v!r}")
    return f"{v}.0"


def manifeste() -> str:
    """The AppxManifest.xml text, identity taken from the environment."""
    return MANIFESTE.format(
        nom=escape((os.environ.get("MSIX_NOM") or "JobHunter.Essai"), {'"': "&quot;"}),
        editeur=escape((os.environ.get("MSIX_EDITEUR") or "CN=JobHunter Essai"), {'"': "&quot;"}),
        editeur_nom=escape(os.environ.get("MSIX_EDITEUR_NOM") or "Grisbix"),
        version=version_msix(),
        description=escape(DESCRIPTION, {'"': "&quot;"}),
    )


def logos(dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
    except ImportError:
        print("(Pillow absent : icône copiée sans mise à l'échelle)")
        for nom in LOGOS:
            shutil.copyfile(ICONE, dossier / nom)
        return
    with Image.open(ICONE) as img:
        for nom, cote in LOGOS.items():
            img.convert("RGBA").resize((cote, cote), Image.LANCZOS).save(dossier / nom)


def noms_des_variantes() -> dict[str, int]:
    """File name → side in pixels, for every scale and target size of the logos."""
    noms: dict[str, int] = {}
    for nom, cote in LOGOS.items():
        base = nom.removesuffix(".png")
        for echelle in ECHELLES:
            noms[f"{base}.scale-{echelle}.png"] = round(cote * echelle / 100)
    for cible in CIBLES:
        noms[f"Square44x44Logo.targetsize-{cible}_altform-unplated.png"] = cible
    return noms


def makepri() -> str | None:
    """makepri.exe, beside makeappx.exe in the Windows SDK; None when it is not there."""
    trouve = shutil.which("makepri")
    if trouve:
        return trouve
    voisin = Path(makeappx()).with_name("makepri.exe")
    return str(voisin) if voisin.is_file() else None


def variantes(disposition: Path) -> bool:
    """The logos at every size, and the resources.pri that names them; True when made.

    Built in a folder of their own, then copied: makepri indexes every file under the
    folder it is given, and the application's thousands of files are not resources.
    Anything missing or failing (Pillow, makepri) leaves the package with its three
    plain logos, as before: a package that installs matters more than a sharper icon.
    """
    try:
        from PIL import Image
    except ImportError:
        return False
    outil = makepri()
    if outil is None:
        print("(makepri.exe absent : logos à une seule taille)")
        return False
    projet = DIST / "msix_pri"
    shutil.rmtree(projet, ignore_errors=True)
    (projet / "Assets").mkdir(parents=True)
    with Image.open(ICONE) as img:
        source = img.convert("RGBA")
        for nom, cote in noms_des_variantes().items():
            source.resize((cote, cote), Image.LANCZOS).save(projet / "Assets" / nom)
    config, pri = DIST / "msix_priconfig.xml", DIST / "msix_resources.pri"
    for f in (config, pri):
        f.unlink(missing_ok=True)
    try:
        for commande in (
            [outil, "createconfig", "/cf", str(config), "/dq", "fr-FR", "/pv", "10.0.0", "/o"],
            [outil, "new", "/pr", str(projet), "/cf", str(config), "/of", str(pri), "/o"],
        ):
            subprocess.run(commande, check=True, capture_output=True)  # nosec B603 : SDK tool
            if commande[1] == "createconfig":
                # One package, no resource packs: the <packaging> section would split
                # the scales into files of their own, which nothing here ships.
                import re

                texte = config.read_text(encoding="utf-8")
                config.write_text(
                    re.sub(r"<packaging>.*?</packaging>", "", texte, flags=re.S), encoding="utf-8"
                )
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"(makepri a échoué : logos à une seule taille — {e})")
        return False
    if not pri.is_file():
        return False
    for nom in LOGOS:  # the unqualified file and its scale-100 twin would be one resource
        (disposition / "Assets" / nom).unlink(missing_ok=True)
    shutil.copytree(projet / "Assets", disposition / "Assets", dirs_exist_ok=True)
    shutil.copyfile(pri, disposition / "resources.pri")
    return True


def makeappx() -> str:
    """makeappx.exe: on the PATH, else the newest Windows SDK's x64 one."""
    trouve = shutil.which("makeappx")
    if trouve:
        return trouve
    kits = (
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits/10/bin"
    )
    candidats = sorted(kits.glob("10.*/x64/makeappx.exe"))
    if not candidats:
        raise SystemExit("makeappx.exe introuvable : installer le SDK Windows.")
    return str(candidats[-1])


# Names the package format (OPC) keeps for itself: one of them anywhere in the payload
# stops makeappx with 0x8007007b — a `_rels` folder too, at any depth (found by bisecting
# the payload, 2026-10-27). python-docx ships an unzipped template holding both
# ([Content_Types].xml, _rels/.rels); it reads templates/default.docx, never that folder.
RESERVES = {
    "[content_types].xml",
    "appxmanifest.xml",
    "appxblockmap.xml",
    "appxsignature.p7x",
    "_rels",
}


def _reserves(dossier: str, noms: list[str]) -> set[str]:
    """For copytree: the reserved names of `noms`, left out of the package."""
    return {n for n in noms if n.lower() in RESERVES}


def remettre_node(dossier: Path, archive: Path) -> bool:
    """node.exe back into the package's folder, from the zip the build took it out to.

    Returns:
        True when put back; False when the folder still had it (no manifest).

    Raises:
        SystemExit: manifest without its zip, or a node.exe that does not match it.
    """
    interne = dossier / "_internal"
    manifeste_node = interne / "jobhunter_node.json"
    if not manifeste_node.is_file():
        return False
    attendu = json.loads(manifeste_node.read_text(encoding="utf-8"))["node"]
    if not archive.is_file():
        raise SystemExit(f"{archive} absent : le paquet du Store doit contenir node.exe.")
    with zipfile.ZipFile(archive) as z:
        node = z.read("node.exe")
    if hashlib.sha256(node).hexdigest() != attendu:
        raise SystemExit("node.exe du zip différent de celui de la construction.")
    cible = interne / "playwright" / "driver" / "node.exe"
    cible.write_bytes(node)
    manifeste_node.unlink()
    return True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--app", default=str(DIST / "JobHunter"), help="dossier construit par build.py")
    ap.add_argument("--sortie", default=str(DIST / "JobHunter.msix"))
    a = ap.parse_args()
    app = Path(a.app)
    if not (app / "JobHunter.exe").exists():
        raise SystemExit(f"{app} ne contient pas JobHunter.exe : lancer build.py d'abord.")
    disposition = DIST / "msix"
    shutil.rmtree(disposition, ignore_errors=True)
    shutil.copytree(app, disposition, ignore=_reserves)
    if remettre_node(disposition, DIST / "playwright-node-win64.zip"):
        print("node.exe remis dans le paquet (règle 10.2.2 du Store)")
    logos(disposition / "Assets")
    if variantes(disposition):
        print(f"logos : {len(noms_des_variantes())} tailles, resources.pri")
    (disposition / "AppxManifest.xml").write_text(manifeste(), encoding="utf-8")
    sortie = Path(a.sortie)
    sortie.unlink(missing_ok=True)
    subprocess.run(  # nosec B603 : the SDK's own tool, fixed arguments
        [makeappx(), "pack", "/d", str(disposition), "/p", str(sortie), "/o"], check=True
    )
    print(f"Paquet MSIX (non signé, pour Partner Center) : {sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
