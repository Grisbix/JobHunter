"""The welcome, in the web window: what a folder without a profile shows (3.78).

Mixed into `Api` (jobhunter.web.api). The page asks `bienvenue()` first; without a
profile it draws the welcome instead of the application:

1. a previous JobHunter folder found on the machine: take its data back (`reprendre`);
2. otherwise the CV, chosen in a file dialog (`choisir_cv`) or dropped on the page;
3. the form prefilled from the CV (`lire_cv`), the Word preview of a PDF CV, the
   background paragraph taken from one's own letter;
4. the profile written by first_launch (`creer_mon_profil`), then the window restarts on
   it: the paths of the data are fixed when the modules load.

A new profile made from the application (Profil → « Nouveau profil… ») restarts the
window in that profile's empty folder, its CV already chosen (JH_CV): the same welcome.
Giving up there puts the empty folder in the archives and goes back to the main profile.

The logic lives in jobhunter.welcome, which has no window; this module only answers the
page. Before 3.78 the same steps were customtkinter windows (ADR 0017).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

FORMATS_CV = ("CV (*.pdf;*.docx)",)


class BienvenueApi:
    """The welcome's calls from the page."""

    _fenetre: Any = None

    def _relancer(self, dans: Path | None = None, cv: str = "") -> None:  # pragma: no cover — Api's
        raise NotImplementedError

    def _dialogue(self, dossier: bool = False, formats: tuple[str, ...] = FORMATS_CV) -> str:
        """A file (or folder) chosen in the system's dialog; "" when cancelled."""
        if self._fenetre is None:
            return ""
        import webview

        if dossier:
            choix = self._fenetre.create_file_dialog(webview.FileDialog.FOLDER)
        else:
            choix = self._fenetre.create_file_dialog(webview.FileDialog.OPEN, file_types=formats)
        return str(choix[0]) if choix else ""

    @staticmethod
    def _secondaire() -> str:
        """The slug of the profile this window is in, "" for the main folder."""
        from jobhunter import profiles, root

        try:
            ici, principale = root.racine().resolve(), profiles.principale().resolve()
        except RuntimeError:
            return ""
        return ici.name if ici != principale and ici.parent.name == profiles.DOSSIER else ""

    def bienvenue(self) -> dict[str, Any]:
        """{"profil", "message", "secondaire", "cv", "reprise": [{"dossier", "date"}]}.

        "message" is the folder migration's sentence (launch), shown once; "cv" the CV
        already chosen for a new profile.
        """
        import time

        from jobhunter import previous_data, root, welcome

        etat: dict[str, Any] = {
            "profil": welcome.a_un_profil(),
            "message": os.environ.pop("JH_MIGRATION", ""),
            "secondaire": bool(self._secondaire()),
            "cv": os.environ.pop("JH_CV", ""),
            "reprise": [],
        }
        if etat["profil"] or etat["secondaire"] or etat["cv"]:
            return etat
        try:
            candidats = previous_data.candidats(root.racine())
        except (OSError, RuntimeError):
            candidats = []
        for d in candidats[:3]:
            f = previous_data.profil_de(d)
            quand = time.strftime("%d/%m/%Y", time.localtime(f.stat().st_mtime)) if f else ""
            etat["reprise"].append({"dossier": str(d), "date": quand})
        return etat

    def choisir_cv(self) -> dict[str, Any]:
        """The CV chosen in a dialog: {"cv"} or {"annule": True}."""
        from jobhunter import welcome

        f = self._dialogue()
        if not f:
            return {"annule": True}
        if welcome.choisir_cv([Path(f)]) is None:
            return {"erreur": "Ce n'est pas un CV PDF ou Word : choisis-en un autre."}
        return {"cv": f}

    def choisir_ancien_dossier(self) -> dict[str, Any]:
        """A previous JobHunter folder chosen by hand: {"dossier"}, {"annule"} or {"erreur"}."""
        from jobhunter import previous_data

        d = self._dialogue(dossier=True)
        if not d:
            return {"annule": True}
        if previous_data.profil_de(Path(d)) is None:
            return {"erreur": "Pas de profil dans ce dossier : choisis celui de JobHunter."}
        return {"dossier": d}

    def reprendre(self, dossier: str) -> dict[str, Any]:
        """Takes a previous folder's data, then opens the application on them."""
        from jobhunter import welcome

        erreur = welcome.reprendre(Path(dossier))
        if erreur:
            return {"ok": False, "erreur": erreur}
        self._relancer()
        return {"ok": True}

    def lire_cv(self, cv: str) -> dict[str, Any]:
        """What the form shows: the CV's answers, the sectors, the countries, warnings."""
        from jobhunter import cv_text, welcome
        from jobhunter.programs import first_launch
        from jobhunter.scoring import zones

        if welcome.choisir_cv([Path(cv)]) is None:
            return {"ok": False, "erreur": "Ce n'est pas un CV PDF ou Word : choisis-en un autre."}
        try:
            texte = first_launch.lire_cv(cv)
        except (Exception, SystemExit) as e:  # a damaged, protected or unknown file  # noqa: BLE001
            return {
                "ok": False,
                "erreur": f"Ce fichier ne s'ouvre pas : {Path(cv).name} ({e}). Ferme-le s'il est "
                "ouvert ailleurs, ou exporte-le à nouveau en PDF (ou en .docx), puis choisis-le encore.",
            }
        prop = first_launch.propositions(texte)
        peu = ""
        if len(texte.strip()) < welcome.PEU_DE_TEXTE:
            peu = (
                "Presque rien n'a pu être lu dans ce CV. "
                + (
                    cv_text.pourquoi_peu_de_texte(cv)
                    or "Choisis un PDF exporté depuis Word, Canva ou Google Docs, ou le .docx."
                )
                + " Sinon, remplis au moins les métiers visés."
            )
        pdf = Path(cv).suffix.lower() == ".pdf"
        return {
            "ok": True,
            "cv": cv,
            "nom": Path(cv).name,
            "peu": peu,
            "pdf": pdf,
            "a_completer": first_launch.A_COMPLETER,
            "propositions": {
                "prenom": str(prop.get("prenom") or ""),
                "nom": str(prop.get("nom") or ""),
                "email": str(prop.get("email") or ""),
                "telephone": str(prop.get("telephone") or ""),
                "ville": str(prop.get("ville") or ""),
                "metiers": str(prop.get("metiers") or ""),
                "annees": int(prop.get("annees") or 0),
                "genre": "f" if prop.get("genre") == "f" else "m",
                "prioritaires": list(prop.get("prioritaires") or []),
                "entreprises": bool(prop.get("entreprises")),
                "parcours": str(prop.get("parcours") or ""),
                "word": pdf and len(texte.strip()) >= welcome.PEU_DE_TEXTE,
            },
            "secteurs": [[s, str(zones.CATALOGUE[s].get("libelle") or s)] for s in zones.CATALOGUE],
            "pays": zones._ISO_PAYS.get(str(prop.get("pays") or "fr"), "ton pays"),
        }

    def apercu_word(self, cv: str) -> dict[str, Any]:
        """Opens the Word version JobHunter would make of a PDF CV."""
        import tempfile

        from jobhunter import cv_word, welcome

        try:
            sortie = Path(tempfile.mkdtemp()) / "Apercu_CV.docx"
            welcome.ouvrir(cv_word.pdf_en_docx(cv, sortie))
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": f"Version Word impossible : {e}."}
        return {"ok": True}

    def parcours_de_ma_lettre(self) -> dict[str, Any]:
        """The background paragraph of one's own letter, chosen in a dialog.

        The letter is kept as the base letter, seen later in Profil (the user, 2026-10-28).
        """
        import shutil

        from jobhunter import own_letter
        from jobhunter.web.workshop import _dossier_lettre_base

        f = self._dialogue(formats=("Lettre (*.pdf;*.docx)",))
        if not f:
            return {"annule": True}
        try:
            trouve = own_letter.parcours_de_lettre(f)
        except (OSError, ValueError) as e:
            return {"erreur": f"Lettre illisible : {e}."}
        if not trouve:
            return {
                "erreur": "Aucun paragraphe de parcours trouvé dans cette lettre : écris-le ici."
            }
        try:
            base = _dossier_lettre_base()
            base.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, base / Path(f).name)
        except (OSError, RuntimeError):
            pass
        return {"parcours": trouve, "source": Path(f).name}

    def creer_mon_profil(self, cv: str, rep: dict[str, Any]) -> dict[str, Any]:
        """Writes the profile from the form's answers, then opens the application on it."""
        from jobhunter import profiles, root, welcome
        from jobhunter.programs import first_launch

        rep = dict(rep or {})
        metiers = str(rep.get("metiers") or "").strip()
        if not metiers or metiers == first_launch.A_COMPLETER:
            return {"ok": False, "erreur": "Indique au moins un métier visé."}
        try:
            rep["annees"] = int(rep.get("annees") or 0)
        except (TypeError, ValueError):
            return {"ok": False, "erreur": "Années d'expérience : un nombre."}
        ok, sortie = welcome.creer_profil(cv, rep)
        if not ok:
            fin = "\n".join(sortie.strip().splitlines()[-12:]) or "(aucun message)"
            return {
                "ok": False,
                "erreur": "Le profil n'a pas été créé. Ce que JobHunter a répondu :\n\n"
                f"{fin}\n\nTu peux choisir un autre CV (un PDF exporté depuis Word ou Canva, "
                "ou le .docx).",
            }
        slug = self._secondaire()
        if slug:
            profiles.nommer(root.racine())
            profiles.activer(slug)
        self._relancer()
        return {"ok": True}

    def plus_tard(self) -> dict[str, Any]:
        """No profile now.

        A new profile's empty folder goes to the archives (never deleted) and the main
        profile opens again; the main folder's window closes.
        """
        from jobhunter import profiles

        slug = self._secondaire()
        if slug:
            try:
                profiles.archiver(slug)
            except (ValueError, RuntimeError):
                pass  # left as it is: never deleted
            self._relancer()
            return {"ok": True}
        if self._fenetre is not None:
            self._fenetre.destroy()
        return {"ok": True}
