"""The desktop's workshop windows in the web interface.

Fit weights, cleaning recipes, documents to compare, CV and letters in bulk, the base
CV. Mixed into `Api` (jobhunter.web.api). The logic of these windows lived in their Tk
code (app.fit_panel, app.recipes, app.compare, app.cv_drop); what the web needs of it
is written here as plain calls, or moved to a module both use (base_cv,
cleanup_recipes.EXEMPLE). Nothing here imports jobhunter.app (tests/test_architecture).
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Sliders of the fit weights: (minimum, maximum, step), the desktop's.
BORNES = {
    "axe": (0.0, 5.0, 0.25),
    "cible": (0.5, 8.0, 0.25),
    "bonus": (0.0, 4.0, 0.5),
    "exp": (0.0, 9.0, 0.5),
}


def _nom_axe(axe: str) -> str:
    # A profile built from a CV names its axes after the catalogue's families.
    from jobhunter.programs.skills_catalog import FAMILLES

    if axe in FAMILLES:
        return str(FAMILLES[axe][0])
    return axe.upper() if len(axe) <= 3 else axe.capitalize()


def _ponderation(v: dict[str, Any], base: Any) -> Any:
    """The weights sent by the page, on the axes and steps of the saved ones."""
    from jobhunter.scoring import weights

    def nb(cle: str, defaut: float) -> float:
        try:
            return float(v.get(cle, defaut))
        except (TypeError, ValueError):
            return defaut

    return weights.Ponderation(
        axes={a: nb(f"axe:{a}", x) for a, x in base.axes.items()},
        cible=nb("cible", base.cible),
        bonus_junior=nb("bonus_junior", base.bonus_junior),
        malus_senior=nb("malus_senior", base.malus_senior),
        malus_experience={s: nb(f"exp:{s}", m) for s, m in base.malus_experience.items()},
    )


def _bilan(b: Any) -> dict[str, Any]:
    d = asdict(b)
    d["repartition"] = [d["repartition"].get(f, 0) for f in range(1, 11)]
    return d


class AtelierApi:
    """Mixed into `Api`: uses its `_file`, `_suivi`, `_tache`, `_demarrer`, `_fenetre`, `_profil_brut`."""

    _file: Any
    _profil_brut: Any
    _suivi: Any
    _tache: Any
    _demarrer: Any
    _fenetre: Any

    # --- Fit weights (the desktop's Profil → Fit tab) ---------------------------------
    _composantes: list[Any] | None = None
    _composantes_erreur: str = ""
    _composantes_en_cours: bool = False

    def poids(self) -> dict[str, Any]:
        """The saved weights, as sliders: key, label, value, bounds."""
        from jobhunter.scoring import weights

        p = weights.lire(self._profil_brut())
        curseurs = [
            {"cle": f"axe:{a}", "nom": _nom_axe(a), "v": x, "b": BORNES["axe"], "groupe": "axes"}
            for a, x in p.axes.items()
        ]
        curseurs += [
            {
                "cle": "cible",
                "nom": "Score pour 10",
                "v": p.cible,
                "b": BORNES["cible"],
                "groupe": "cible",
            },
            {
                "cle": "bonus_junior",
                "nom": "Bonus junior",
                "v": p.bonus_junior,
                "b": BORNES["bonus"],
                "groupe": "titre",
            },
            {
                "cle": "malus_senior",
                "nom": "Malus senior",
                "v": p.malus_senior,
                "b": BORNES["bonus"],
                "groupe": "titre",
            },
        ]
        curseurs += [
            {
                "cle": f"exp:{s}",
                "nom": f"{s} ans et plus",
                "v": m,
                "b": BORNES["exp"],
                "groupe": "exp",
            }
            for s, m in sorted(p.malus_experience.items())
        ]
        self._lire_composantes()
        return {"curseurs": curseurs}

    def _lire_composantes(self, relire: bool = False) -> None:
        """The queue's components, read once by programs.fit_components in its own process.

        Ten thousand texts take about thirty seconds; a change of weights then costs
        milliseconds (scoring.weights.bilan).
        """
        if self._composantes_en_cours or (self._composantes is not None and not relire):
            return
        self._composantes_en_cours = True

        def tache() -> None:
            from jobhunter import root
            from jobhunter.programs.fit_components import depuis_ligne

            try:
                r = subprocess.run(  # nosec B603 : our own program, arguments built here
                    [sys.executable, "-m", "jobhunter.programs.fit_components"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=600,
                    cwd=str(root.scripts()),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if r.returncode != 0:
                    raise RuntimeError("fit_components")
                d = json.loads(r.stdout)
                axes = list(d["axes"])
                self._composantes = [depuis_ligne(x, axes) for x in d["lignes"]]
                self._composantes_erreur = ""
            except Exception as e:  # noqa: BLE001 — shown on the page, never fatal
                self._composantes_erreur = type(e).__name__
            finally:
                self._composantes_en_cours = False

        threading.Thread(target=tache, daemon=True).start()

    def bilan_poids(self, valeurs: dict[str, Any]) -> dict[str, Any]:
        """The queue under the page's weights and under the saved ones; nothing written."""
        from jobhunter.scoring import weights

        if self._composantes is None:
            return {
                "pret": False,
                "erreur": self._composantes_erreur,
                "en_cours": self._composantes_en_cours,
            }
        e = weights.lire(self._profil_brut())
        p = _ponderation(valeurs or {}, e)
        return {
            "pret": True,
            "essai": _bilan(weights.bilan(self._composantes, p)),
            "enregistre": _bilan(weights.bilan(self._composantes, e)),
            "change": p != e,
        }

    def relire_composantes(self) -> dict[str, Any]:
        """Reads the queue's components again (after a collection)."""
        self._lire_composantes(relire=True)
        return {"ok": True}

    def enregistrer_poids(self, valeurs: dict[str, Any]) -> dict[str, Any]:
        """Writes the weights into the profile; the previous one is kept as `.bak`."""
        from jobhunter import profile, search_settings
        from jobhunter.scoring import weights

        brut = self._profil_brut()
        e = weights.lire(brut)
        p = _ponderation(valeurs or {}, e)
        if p == e:
            return {"ok": False, "erreur": "Rien à enregistrer : les poids sont ceux du profil."}
        if erreurs := weights.valider(p):
            return {"ok": False, "erreurs": erreurs}
        bak = search_settings.ecrire(Path(profile.FICHIER), weights.appliquer(brut, p))
        profile.recharger()
        return {"ok": True, "bak": bak.name}

    # --- Cleaning recipes --------------------------------------------------------------
    @staticmethod
    def _fichier_recettes() -> Path:
        from jobhunter import cleanup_recipes as R
        from jobhunter import root

        return root.dans(root.scripts(), R.FICHIER)

    def recettes(self) -> dict[str, Any]:
        """The saved recipes as text (the example when there are none)."""
        from jobhunter import cleanup_recipes as R

        return {"texte": R.en_texte(R.lire(self._fichier_recettes())) or R.EXEMPLE}

    def _changements(self, texte: str) -> tuple[list[Any], list[Any], list[str]]:
        from jobhunter import cleanup_recipes as R

        r = R.depuis_texte(str(texte or ""))
        if erreurs := R.valider(r):
            return r, [], erreurs
        return r, R.apercu(list(self._file()), r, set(self._suivi())), []

    def apercu_recettes(self, texte: str) -> dict[str, Any]:
        """Every change the recipes would make on the queue; nothing is written."""
        _, chg, erreurs = self._changements(texte)
        if erreurs:
            return {"ok": False, "erreurs": erreurs}
        n = sum(1 for c in chg if not c.ecarte)
        return {
            "ok": True,
            "n": n,
            "ecartes": len(chg) - n,
            "lignes": [asdict(c) for c in chg[:2000]],
        }

    def appliquer_recettes(self, texte: str) -> dict[str, Any]:
        """Saves the recipes, then applies them under the queue's lock (programs.recipes).

        An offer applied to is never renamed (cleanup_recipes.apercu sets it aside).
        """
        from jobhunter import cleanup_recipes as R

        r, chg, erreurs = self._changements(texte)
        if erreurs:
            return {"ok": False, "erreurs": erreurs}
        R.ecrire(self._fichier_recettes(), r)
        if not any(not c.ecarte for c in chg):
            return {"ok": True, "message": "Recettes enregistrées : rien à changer dans la file."}
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        d = self._demarrer(
            "recettes", "Recettes de nettoyage", ["jobhunter.programs.recipes", "--appliquer"]
        )
        return {**d, "tache": True}

    # --- Documents to compare (a retouched one and the newer version beside it) ---------
    @staticmethod
    def _attente() -> list[Any]:
        from jobhunter import paths
        from jobhunter.documents import generated

        return generated.en_attente([paths.CV_PAR_OFFRE, paths.LT_PAR_OFFRE])

    def a_comparer(self) -> list[dict[str, Any]]:
        """The documents retouched by hand that have a newer generated version waiting."""
        import os

        from jobhunter import paths
        from jobhunter.documents import generated

        lignes = []
        try:
            attente = self._attente()
        except OSError:
            return []
        for i, e in enumerate(attente):
            try:
                n: int | str = generated.ecart(e.actuel, e.nouveau)
            except Exception:  # noqa: BLE001 — open in Word, damaged: shown, not compared
                n = "?"
            lignes.append({"i": i, "doc": os.path.relpath(e.actuel, paths.BASE), "ecart": n})
        return lignes

    def diff_document(self, i: int) -> dict[str, Any]:
        """The paragraphs: "-" only in the user's version, "+" only in the new one."""
        from jobhunter.documents import generated

        attente = self._attente()
        if not 0 <= int(i) < len(attente):
            return {"ok": False, "erreur": "document introuvable"}
        e = attente[int(i)]
        try:
            lignes = generated.comparer(e.actuel, e.nouveau)
        except Exception as x:  # noqa: BLE001
            return {"ok": False, "erreur": f"Lecture impossible : {type(x).__name__}"}
        return {"ok": True, "lignes": [[g, p] for g, p in lignes if g != "=" or p.strip()]}

    def choisir_version(self, i: int, prendre: bool) -> dict[str, Any]:
        """Keeps one version; the other goes to _a_comparer/_anciennes/, never deleted."""
        from jobhunter.documents import generated

        attente = self._attente()
        if not 0 <= int(i) < len(attente):
            return {"ok": False, "erreur": "document introuvable"}
        e = attente[int(i)]
        try:
            ou = generated.prendre_nouvelle(e) if prendre else generated.garder_mienne(e)
        except OSError as x:
            return {
                "ok": False,
                "erreur": f"Impossible pour l'instant ({type(x).__name__}) : le document est-il ouvert dans Word ?",
            }
        return {"ok": True, "message": f"Version mise de côté : {ou.name}"}

    # --- CV and letters in bulk -----------------------------------------------------------
    def documents_restants(self) -> int:
        """Offers at fit 8 and more still waiting for their CV or letter."""
        from jobhunter.links import existe

        return sum(
            1
            for o in self._file()
            if (o.get("fit") or 0) >= 8 and not (existe(o.get("cv")) and existe(o.get("lettre")))
        )

    def documents_lot(self, n: int) -> dict[str, Any]:
        """CV and letter for the `n` best-scored offers that do not have them."""
        try:
            n = int(n)
        except (TypeError, ValueError):
            n = 0
        if not 1 <= n <= 1000:
            return {"ok": False, "erreur": "entre 1 et 1000 offres"}
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        return self._demarrer(
            "documents_lot",
            f"CV et lettres · {n} offre(s)",
            ["jobhunter.programs.generate_docs", "--top", str(n)],
        )

    # --- The base CV ------------------------------------------------------------------
    _cv_choisi: Path | None = None

    def choisir_cv_base(self) -> dict[str, Any]:
        """Asks for the new base CV; nothing is replaced before `remplacer_cv_base`."""
        from jobhunter import base_cv, profile

        if self._fenetre is None:
            return {"ok": False, "erreur": "il faut l'application pour choisir un CV"}
        import webview

        choix = self._fenetre.create_file_dialog(
            webview.FileDialog.OPEN, file_types=("CV (*.docx;*.pdf)",)
        )
        if not choix:
            return {"ok": False, "annule": True}
        cv = Path(str(choix[0]))
        if cv.suffix.lower() not in (".docx", ".pdf"):
            return {"ok": False, "erreur": "un CV au format .docx ou .pdf"}
        try:
            noms = base_cv.cvs_de_base(profile.charger())
        except (profile.ProfilAbsent, ValueError):
            noms = []
        self._cv_choisi = cv
        ancien = noms[0] if noms else f"CV_base{cv.suffix.lower()}"
        return {"ok": True, "cv": cv.name, "ancien": ancien, "autres": max(0, len(noms) - 1)}

    def remplacer_cv_base(self) -> dict[str, Any]:
        """Puts the chosen CV in place of the base one; the old one is kept as `.bak`."""
        from jobhunter import base_cv, paths, profile

        cv, self._cv_choisi = self._cv_choisi, None
        if cv is None:
            return {"ok": False, "erreur": "aucun CV choisi"}
        try:
            noms = base_cv.cvs_de_base(profile.charger())
        except (profile.ProfilAbsent, ValueError):
            noms = []
        ancien = noms[0] if noms else f"CV_base{cv.suffix.lower()}"
        try:
            neuf = base_cv.remplacer_cv_de_base(cv, ancien, paths.CV_MODELES, Path(profile.FICHIER))
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": f"{type(e).__name__}: {e}"}
        profile.recharger()
        return {"ok": True, "neuf": neuf}
