"""A profile's trades: one CV and one letter each, and the profile file edited in the window.

Mixed into `Api` (jobhunter.web.api). A trade is a domain of the profile
(`domaines[]`): the words of a posting's title that call it, its CV, and the background
paragraph of its letters. The user, 2026-11-02: « pouvoir ajouter un CV dans un profil
déjà existant, avoir plusieurs lettres de motivation pour un seul profil, par conséquent
ça rajoute un domaine différent dans le filtre domaines ». A trade added here is a new
domain: once the offers are scored again, it shows in the Offres screen's filter.

The letter of a trade is kept in Letters/Base/Domaines (the user's own letter stays the
newest file of Letters/Base): its background paragraph becomes the trade's
`parcours_fr` or `parcours_en`, the one its generated letters use.

The advanced editor replaces « open profile.json in Notepad »: the same file, shown as
a form. It only changes values: a key cannot be added nor removed, and each value keeps
its type, so a typo cannot break the engine.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from jobhunter.web.messages import echec

FORMATS = ("Document (*.docx;*.pdf)",)


def _dossier_lettres_metiers() -> Path:
    from jobhunter import root

    return root.dossier("Lettres") / "Base" / "Domaines"


def _libre(dossier: Path, nom: str) -> Path:
    """`nom` in `dossier`, numbered when taken (never overwrites a file)."""
    f = dossier / nom
    n = 2
    while f.exists():
        f = dossier / f"{Path(nom).stem}_{n}{Path(nom).suffix}"
        n += 1
    return f


def _cle_libre(libelle: str, prises: set[str]) -> str:
    import re
    import unicodedata

    base = unicodedata.normalize("NFKD", libelle).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")[:40] or "Metier"
    cle, n = base, 2
    while cle.lower() in {p.lower() for p in prises}:
        cle, n = f"{base}_{n}", n + 1
    return cle


def _mots(texte: str | list[Any]) -> list[str]:
    morceaux = texte if isinstance(texte, list) else str(texte or "").replace(";", ",").split(",")
    return list(dict.fromkeys(m.strip().lower() for m in map(str, morceaux) if m.strip()))


def meme_forme(ancien: Any, neuf: Any, chemin: str = "profil") -> str:
    """An empty text when `neuf` has the shape of `ancien`; else where and why not.

    Same keys in each object; each value keeps its type (an integer may become a
    decimal and back); a list may grow or shrink, its new items shaped as its first.
    """
    if isinstance(ancien, bool) or isinstance(neuf, bool):
        return (
            "" if isinstance(ancien, bool) and isinstance(neuf, bool) else f"{chemin} : oui ou non"
        )
    if isinstance(ancien, (int, float)):
        return "" if isinstance(neuf, (int, float)) else f"{chemin} : un nombre"
    if isinstance(ancien, str):
        return "" if isinstance(neuf, str) else f"{chemin} : un texte"
    if ancien is None:
        return ""
    if isinstance(ancien, dict):
        if not isinstance(neuf, dict):
            return f"{chemin} : une rubrique"
        if set(ancien) != set(neuf):
            return f"{chemin} : rubriques changées"
        for k in ancien:
            e = meme_forme(ancien[k], neuf[k], f"{chemin} › {k}")
            if e:
                return e
        return ""
    if isinstance(ancien, list):
        if not isinstance(neuf, list):
            return f"{chemin} : une liste"
        if not ancien:
            ok = all(isinstance(x, (str, int, float, bool)) for x in neuf)
            return "" if ok else f"{chemin} : une liste de textes"
        for i, x in enumerate(neuf):
            modele = ancien[i] if i < len(ancien) else ancien[0]
            e = meme_forme(modele, x, f"{chemin} › {i + 1}")
            if e:
                return e
        return ""
    return ""


class MetiersApi:
    """Mixed into `Api`: uses its `_fenetre`, `_profil_brut`, `_ecrire_profil`."""

    _fenetre: Any

    def _profil_brut(self) -> dict[str, Any]:  # pragma: no cover — Api's
        raise NotImplementedError

    def _ecrire_profil(self, nouveau: dict[str, Any]) -> str:  # pragma: no cover — Api's
        raise NotImplementedError

    def _choisir(self, quoi: str) -> Path | None:
        """A .docx or .pdf the user picks; None when cancelled or not a document."""
        if self._fenetre is None:
            return None
        import webview

        choix = self._fenetre.create_file_dialog(webview.FileDialog.OPEN, file_types=FORMATS)
        if not choix:
            return None
        f = Path(str(choix[0]))
        return f if f.suffix.lower() in (".docx", ".pdf") and f.is_file() else None

    def metiers(self) -> dict[str, Any]:
        """Each trade: its name, its title words, its CV and its letter (paths when present)."""
        from jobhunter import paths

        p = self._profil_brut()
        lettres = _dossier_lettres_metiers()
        sortie = []
        for d in p.get("domaines") or []:
            if not isinstance(d, dict):
                continue
            cv = str(d.get("cv") or "")
            lettre = str(d.get("lettre") or "")
            chemin_lettre = str(lettres / lettre) if lettre and (lettres / lettre).is_file() else ""
            if not lettre and d.get("cle") == "General":
                # The letter given before trades existed (Letters/Base) is the rest's
                # letter: one place for letters, « Mes métiers » (3.75).
                from jobhunter.web.workshop import lettre_de_base

                base = lettre_de_base()
                lettre, chemin_lettre = (base.name, str(base)) if base else ("", "")
            sortie.append(
                {
                    "cle": str(d.get("cle") or ""),
                    "libelle": str(d.get("libelle") or d.get("cle") or ""),
                    "mots": [str(m) for m in d.get("mots_titre") or []],
                    "cv": cv,
                    "cv_chemin": str(paths.CV_MODELES / cv)
                    if cv and (paths.CV_MODELES / cv).is_file()
                    else "",
                    "lettre": lettre,
                    "lettre_chemin": chemin_lettre,
                }
            )
        base = self.documents_de_base()  # type: ignore[attr-defined]
        return {
            "metiers": sortie,
            "phrase_fr": base["phrase_fr"],
            "phrase_en": base["phrase_en"],
            "exemple": base["exemple"],
        }

    def _poser(self, cle: str, champs: dict[str, Any]) -> dict[str, Any]:
        p = self._profil_brut()
        for d in p.get("domaines") or []:
            if isinstance(d, dict) and d.get("cle") == cle:
                d.update(champs)
                break
        else:
            return {"ok": False, "erreur": "Métier inconnu"}
        try:
            return {"ok": True, "bak": self._ecrire_profil(p)}
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": echec(e)}

    def _copier_cv(self, f: Path) -> str:
        from jobhunter import paths

        paths.CV_MODELES.mkdir(parents=True, exist_ok=True)
        cible = _libre(paths.CV_MODELES, f.name)
        shutil.copy2(f, cible)
        return cible.name

    def _copier_lettre(self, f: Path) -> tuple[str, dict[str, str]]:
        """The letter kept for its trade, and the background paragraph it gives."""
        from jobhunter import own_letter
        from jobhunter.scoring.language import langue_offre

        dossier = _dossier_lettres_metiers()
        dossier.mkdir(parents=True, exist_ok=True)
        cible = _libre(dossier, f.name)
        shutil.copy2(f, cible)
        try:
            parcours = own_letter.parcours_de_lettre(cible)
        except (OSError, ValueError):
            parcours = ""
        champs: dict[str, str] = {}
        if parcours:
            langue = langue_offre("", parcours, "")
            champs["parcours_en" if langue == "en" else "parcours_fr"] = parcours
        return cible.name, champs

    def cv_metier(self, cle: str) -> dict[str, Any]:
        """Gives a trade its own CV (the others keep theirs)."""
        f = self._choisir("cv")
        if f is None:
            return {"ok": False, "annule": True}
        try:
            nom = self._copier_cv(f)
        except OSError as e:
            return {"ok": False, "erreur": echec(e)}
        return {**self._poser(str(cle), {"cv": nom}), "nom": nom}

    def lettre_metier(self, cle: str) -> dict[str, Any]:
        """Gives a trade its own letter; its background paragraph goes to the trade."""
        f = self._choisir("lettre")
        if f is None:
            return {"ok": False, "annule": True}
        try:
            nom, champs = self._copier_lettre(f)
        except OSError as e:
            return {"ok": False, "erreur": echec(e)}
        r = self._poser(str(cle), {"lettre": nom, **champs})
        return {**r, "nom": nom, "parcours": next(iter(champs.values()), "")}

    def ajouter_metier(self, libelle: str, mots: str | list[Any]) -> dict[str, Any]:
        """A new trade: its name, its title words, a CV picked now, its letter if wanted.

        Its sentences are the first trade's until its own letter gives a paragraph: a
        letter is never written from nothing.
        """
        libelle = str(libelle or "").strip()[:40]
        liste = _mots(mots)
        if not libelle or not liste:
            return {"ok": False, "erreur": "Il faut un nom et au moins un mot du titre"}
        f = self._choisir("cv")
        if f is None:
            return {"ok": False, "annule": True}
        p = self._profil_brut()
        domaines = [d for d in p.get("domaines") or [] if isinstance(d, dict)]
        modele = next(
            (d for d in domaines if d.get("cle") != "General"), domaines[0] if domaines else {}
        )
        try:
            cv = self._copier_cv(f)
        except OSError as e:
            return {"ok": False, "erreur": echec(e)}
        neuf = {
            **{k: v for k, v in modele.items() if isinstance(v, str)},
            "cle": _cle_libre(libelle, {str(d.get("cle")) for d in domaines}),
            "libelle": libelle,
            "mots_titre": liste,
            "cv": cv,
            "cv_en": "",
            "accroche_fr": libelle.lower(),
            "accroche_en": libelle.lower(),
            "preuve_fr": "",
            "preuve_en": "",
            "preuve_detente_fr": "",
        }
        neuf.pop("lettre", None)
        # Before the catch-all « General », which takes what no other trade wants.
        rang = next((i for i, d in enumerate(domaines) if d.get("cle") == "General"), len(domaines))
        p["domaines"] = [*domaines[:rang], neuf, *domaines[rang:]]
        try:
            bak = self._ecrire_profil(p)
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": echec(e)}
        return {"ok": True, "cle": neuf["cle"], "cv": cv, "bak": bak}

    def retirer_metier(self, cle: str) -> dict[str, Any]:
        """Removes a trade from the profile (its CV and letter files stay)."""
        p = self._profil_brut()
        domaines = [d for d in p.get("domaines") or [] if isinstance(d, dict)]
        reste = [d for d in domaines if d.get("cle") != cle]
        if len(reste) == len(domaines):
            return {"ok": False, "erreur": "Métier inconnu"}
        if not [d for d in reste if d.get("cle") != "General"]:
            return {"ok": False, "erreur": "Garde au moins un métier"}
        p["domaines"] = reste
        try:
            return {"ok": True, "bak": self._ecrire_profil(p)}
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": echec(e)}

    def renommer_metier(self, cle: str, libelle: str, mots: str | list[Any]) -> dict[str, Any]:
        """A trade's displayed name and title words."""
        libelle = str(libelle or "").strip()[:40]
        liste = _mots(mots)
        if not libelle:
            return {"ok": False, "erreur": "Nom vide"}
        champs: dict[str, Any] = {"libelle": libelle}
        if cle != "General":
            if not liste:
                return {"ok": False, "erreur": "Au moins un mot du titre"}
            champs["mots_titre"] = liste
        return self._poser(str(cle), champs)

    # --- The whole profile, as a form (« Fichier du profil (avancé) ») -----------------
    def profil_avance(self) -> dict[str, Any]:
        """The profile file as it is, for the form."""
        try:
            return {"ok": True, "profil": self._profil_brut()}
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": echec(e)}

    def enregistrer_profil_avance(self, neuf: Any) -> dict[str, Any]:
        """Writes the form back, only if every key and type is as before (`meme_forme`)."""
        try:
            ancien = self._profil_brut()
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": echec(e)}
        erreur = meme_forme(ancien, neuf)
        if erreur:
            return {"ok": False, "erreur": f"Rien n'est écrit — {erreur}"}
        try:
            return {"ok": True, "bak": self._ecrire_profil(neuf)}
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": echec(e)}
