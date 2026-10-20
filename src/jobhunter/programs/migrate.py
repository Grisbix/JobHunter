"""jobhunter migrate — moves a 2.x data folder (French names) to the 3.0 layout (English names).

    Scripts/ -> data/            profil/profil.json -> profile/profile.json
    Mon_CV/  -> My_CV/           Lettres/ -> Letters/
    CV/Par_offre -> CV/By_offer  CV/Modèles -> CV/Templates   suivi.json -> applications.json
    (the full table: jobhunter.root.NOMS)

What makes it safe, in this order:

1. nothing is done while another program holds the queue (exit code 3);
2. a ZIP of everything that cannot be rebuilt (queue, tracking, profile, CV, hand-written
   letters; not the per-offer documents, which `jobhunter regenerate` rebuilds) is
   written at the root first: `_backup_migration_<date>.zip`;
3. folders are RENAMED, never copied: a move on the same disk is instant and loses
   nothing. A file shipped by the update that is already in the way is set aside as
   `<name>.nouveau`; your file takes its place;
4. the links stored in the data are rewritten: the queue's `cv`/`lettre` file:/// URLs
   (they name `CV/Par_offre`, `Lettres/Par_offre`) and the tracking's proof screenshots;
5. it checks: same offers in the same order, tracking identical apart from the rewritten
   paths, no document link lost. Otherwise everything is put back as it was.

Run again, it does nothing. Automatic for a published installation (after the update to
3.0, or when the installed app starts); never automatic in a folder without `VERSION`
(a development copy, or a folder that receives the engine by pip): there, it is your
decision, through this command.
"""

import argparse
import datetime
import filecmp
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from jobhunter import links as _liens
from jobhunter import root as _racine
from jobhunter.storage import atomic as _atomique
from jobhunter.storage import lock as _verrou

OCCUPE = 3
ATTENTE = ".migration_en_attente"  # files that were identical on both sides, held for rollback


class Echec(Exception):
    """The migration cannot finish: everything is put back."""


def a_migrer(r: Path) -> bool:
    """True if `r` is a data folder in the 2.x layout."""
    return not _racine.anglais(r) and any((r / d).exists() for d in _racine.DOSSIERS)


def _base_documents(r: Path) -> Path | None:
    """The documents folder set in `Scripts/chemins.json`, if it is not the root."""
    try:
        cfg = json.loads((r / "Scripts" / "chemins.json").read_text(encoding="utf-8"))
        p = Path((cfg.get("documents") or "").strip())
    except (OSError, ValueError, AttributeError):
        return None
    if (
        not str(p)
        or str(p) == "."
        or os.path.normcase(str(p.resolve())) == os.path.normcase(str(r.resolve()))
    ):
        return None
    return p


def prefixes(r: Path, base: Path | None) -> list[tuple[Path, Path]]:
    """(old folder, new folder) of every folder that moves, for rewriting stored paths."""
    n = _racine.NOMS
    paires = [(r / a, r / b) for a, b in _racine.DOSSIERS.items()]
    paires += [(r / "Scripts" / a, r / "data" / n[a]) for a in ("_sauvegardes", "_preuves")]
    for b in [r, *([base] if base else [])]:
        paires += [(b / "CV" / a, b / "CV" / n[a]) for a in ("Par_offre", "Modèles", "Sur_mesure")]
        paires += [(b / "Lettres", b / "Letters")]
        paires += [
            (b / "Lettres" / a, b / "Letters" / n[a])
            for a in ("Par_offre", "Relances", "Sur_mesure")
        ]
    # longest first: CV/Par_offre before CV
    return sorted(paires, key=lambda p: -len(str(p[0])))


def traduire(p: Path, paires: list[tuple[Path, Path]]) -> Path:
    """The new place of a path under a folder that moved (the path itself, otherwise)."""
    brut = os.path.normpath(str(p))
    s = os.path.normcase(brut)
    for vieux, neuf in paires:
        v = os.path.normcase(os.path.normpath(str(vieux)))
        if s == v or s.startswith(v + os.sep):
            reste = brut[len(v) :].lstrip("\\/")
            return neuf / reste if reste else neuf
    return p


class _Journal:
    """The moves done, to put everything back in reverse order."""

    def __init__(self, attente: Path) -> None:
        self.ops: list[tuple[str, Path, Path]] = []
        self.attente = attente

    def deplacer(self, src: Path, dst: Path) -> None:
        if not src.exists():
            return
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dst)
            self.ops.append(("mv", src, dst))
        elif src.is_dir() and dst.is_dir():
            for enfant in sorted(src.iterdir()):
                self.deplacer(enfant, dst / enfant.name)
            src.rmdir()
            self.ops.append(("rmdir", src, src))
        elif src.is_file() and dst.is_file():
            if filecmp.cmp(src, dst, shallow=False):
                garde = self.attente / str(len(self.ops))
                garde.parent.mkdir(parents=True, exist_ok=True)
                os.rename(src, garde)
                self.ops.append(("mv", src, garde))
            else:
                # Your file wins; the shipped one is set aside, like an update does.
                self.deplacer(dst, dst.with_name(dst.name + ".nouveau"))
                self.deplacer(src, dst)
        else:
            raise Echec(f"{src} et {dst} : un dossier et un fichier du même nom")

    def defaire(self) -> list[str]:
        erreurs = []
        for op, a, b in reversed(self.ops):
            try:
                if op == "mv":
                    a.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(b, a)
                else:
                    a.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                erreurs.append(f"{b} -> {a} : {e}")
        return erreurs


def _renommer_dedans(dossier: Path, j: _Journal) -> None:
    """The renamed names directly inside a folder (files and sub-folders)."""
    if not dossier.is_dir():
        return
    for enfant in sorted(dossier.iterdir()):
        nom = enfant.name
        neuf = _racine.NOMS.get(nom)
        if neuf is None and nom.startswith("profil.json"):
            neuf = "profile.json" + nom[len("profil.json") :]  # profil.json.bak
        if neuf is None and nom.startswith("exemple_"):
            neuf = "example_" + nom[len("exemple_") :].replace("Faits", "Facts")
        if neuf is not None and neuf != nom:
            j.deplacer(enfant, dossier / neuf)


def _sauvegarde(r: Path, base: Path | None) -> Path:
    """ZIP of what cannot be rebuilt. Returns its path."""
    zp = r / f"_backup_migration_{datetime.datetime.now():%Y-%m-%d_%H%M%S}.zip"
    racines = [r, *([base] if base else [])]
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for b in racines:
            for d in ("Scripts", "profil", "Mon_CV", "CV", "Lettres"):
                if not (b / d).is_dir() or (b is base and d not in ("CV", "Lettres")):
                    continue
                for f in (b / d).rglob("*"):
                    if f.is_file() and "Par_offre" not in f.parts and not f.name.endswith(".lock"):
                        nom = f.relative_to(b).as_posix()
                        z.write(f, nom if b is r else f"_documents/{nom}")
    return zp


def _lire(p: Path, defaut: Any) -> Any:
    # Direct reading: this program runs before the storage modules know the new
    # layout, under the queue lock it holds.
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return defaut


def _liens_valides(file: list[dict[str, Any]]) -> int:
    return sum(bool(_liens.existe(o.get(k))) for o in file for k in ("cv", "lettre"))


def _sans_capture(suivi: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in suivi.items():
        v = dict(v) if isinstance(v, dict) else v
        if isinstance(v, dict) and isinstance(v.get("preuve"), dict):
            v["preuve"] = {c: x for c, x in v["preuve"].items() if c != "capture"}
        out[k] = v
    return out


def migrer(r: Path, bavard: bool = True) -> int:
    """Moves the 2.x layout of `r` to 3.0. Returns 0 (done or nothing to do), 1 (failed,
    everything put back), 3 (queue busy, nothing touched)."""

    def dire(m: str) -> None:
        if bavard:
            print(m)

    if not a_migrer(r):
        dire("Rien à migrer : ce dossier est déjà au format 3.0.")
        return 0
    queue = r / "Scripts" / "apply_queue.json"
    if queue.parent.is_dir() and not _verrou.prendre_verrou(queue, attente=0, bavard=False):
        dire(
            "La file est occupée par un autre programme : rien n'a été touché, réessaie plus tard."
        )
        return OCCUPE
    base = _base_documents(r)
    paires = prefixes(r, base)
    j = _Journal(r / ATTENTE)
    file_avant: list[dict[str, Any]] = []
    suivi_avant: dict[str, Any] = {}
    # The two data files byte for byte, to put them back exactly as they were.
    octets = {p: p.read_bytes() for p in (queue, r / "Scripts" / "suivi.json") if p.is_file()}
    try:
        file_avant = _lire(queue, [])
        suivi_avant = _lire(r / "Scripts" / "suivi.json", {})
        valides_avant = _liens_valides(file_avant)
        zp = _sauvegarde(r, base)
        dire(f"Sauvegarde : {zp.name}")

        for a, b in _racine.DOSSIERS.items():
            j.deplacer(r / a, r / b)
        for d in ("data", "profile", "My_CV", "CV", "Letters"):
            _renommer_dedans(r / d, j)
        if base:
            j.deplacer(base / "Lettres", base / "Letters")
            for d in ("CV", "Letters"):
                _renommer_dedans(base / d, j)
        donnees = r / "data"
        file_ = _lire(donnees / "apply_queue.json", [])
        for o in file_:
            for k in ("cv", "lettre"):
                p = _liens.chemin_de(o.get(k))
                if p is not None and (neuf := traduire(p, paires)) != p:
                    o[k] = _liens.url_de(neuf)
        suivi = _lire(donnees / "applications.json", {})
        for v in suivi.values():
            preuve = v.get("preuve") if isinstance(v, dict) else None
            if isinstance(preuve, dict) and preuve.get("capture"):
                preuve["capture"] = str(traduire(Path(preuve["capture"]), paires))
        if file_:
            _atomique.ecrire_json(donnees / "apply_queue.json", file_)
        if suivi:
            _atomique.ecrire_json(donnees / "applications.json", suivi)

        # The checks: same offers, same tracking, no document link lost.
        apres = _lire(donnees / "apply_queue.json", [])
        if [(o.get("entreprise"), o.get("poste")) for o in apres] != [
            (o.get("entreprise"), o.get("poste")) for o in file_avant
        ]:
            raise Echec("la file n'a plus les mêmes offres")
        if _sans_capture(_lire(donnees / "applications.json", {})) != _sans_capture(suivi_avant):
            raise Echec("le suivi a changé")
        if _liens_valides(apres) < valides_avant:
            raise Echec(
                f"liens de documents perdus ({_liens_valides(apres)} au lieu de {valides_avant})"
            )
        if not _racine.anglais(r):
            raise Echec("le dossier n'est pas reconnu au format 3.0 après la migration")
    except (Echec, OSError, ValueError) as e:
        erreurs = j.defaire()
        for p, contenu in octets.items():
            if p.parent.is_dir():
                p.write_bytes(contenu)  # the moves are undone above; the content too
        _verrou.rendre_verrou(queue)
        print(f"! Migration annulée ({e}) : tout est remis comme avant.", file=sys.stderr)
        for err in erreurs:
            print(f"  ! non remis : {err}", file=sys.stderr)
        return 1
    _verrou.rendre_verrou(queue)
    # Our lock moved with the folder: it is released at its new place.
    (r / "data" / "apply_queue.json.lock").unlink(missing_ok=True)
    shutil.rmtree(r / ATTENTE, ignore_errors=True)
    dire(
        f"Migration faite : {len(file_avant)} offres, {len(suivi_avant)} candidatures, "
        f"{valides_avant} liens de documents. Dossiers : data/, profile/, My_CV/, Letters/."
    )
    return 0


def automatique(r: Path) -> bool:
    """Is the migration done without asking, in this folder? Published installation only."""
    from jobhunter import frozen as _gele

    return _gele.est_gele() or (r / "VERSION").exists()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Passe les dossiers de données aux noms anglais de la 3.0 (avec sauvegarde)."
    )
    ap.add_argument("--verifier", action="store_true", help="dire seulement s'il y a à migrer")
    a = ap.parse_args()
    r = _racine.racine()
    if a.verifier:
        print("À migrer (format 2.x)." if a_migrer(r) else "Déjà au format 3.0.")
        return 0
    return migrer(r)


if __name__ == "__main__":
    sys.exit(main())
