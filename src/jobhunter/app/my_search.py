"""The "Ma recherche" panel: keywords, title filter and places edited in the app, CV suggestions.

Places ("Où tu veux travailler"): a search field ("Rechercher") finds a place of
`scoring.zones.CATALOGUE` or any city or country of the world; only the chosen places
are shown, as priority or secondary, each removed by its ✕. They never touch the fit; they fill the Zone column
(1 · prioritaire, 2 · secondaire…), and the offers already in the queue are labelled
again after "Enregistrer" (`python -m jobhunter.scoring.zones --ecrire`).

What the panel edits lives in the active profile (jobhunter.search_settings); nothing is
written before "Enregistrer", which keeps the previous profile as `.bak`. "Aperçu sur ma
file" runs the engine's real title filter on the offers already in the queue, once with
the current profile and once with the settings being edited, in separate processes
(programs.search_preview), and says which offers would be set aside. Suggestions from
the CV (jobhunter.cv_suggestions) each come with the CV's sentence that justifies them,
and are added only once ticked.
"""

import json
import subprocess
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from jobhunter import cv_suggestions as _sugg
from jobhunter import profile as _profil
from jobhunter import search_settings as _reglages
from jobhunter.app import theme as _theme
from jobhunter.app.common import PY
from jobhunter.app.language import t as _t
from jobhunter.app.theme import ACC, ACC_H, ACC_TX, BTN, BTN_H, CB, CF, CL, MUT, TX, WORK

if TYPE_CHECKING:
    from jobhunter.app._app_type import AppTypee

_CHAMPS = (
    (
        "mots_cles",
        "Mots-clés de recherche",
        "Une recherche par ligne (LinkedIn, Welcome to the Jungle…).",
    ),
    (
        "garder",
        "Intitulés à garder",
        "Un mot par ligne. Un intitulé doit contenir l'un d'eux pour être collecté. "
        "Un mot trouve aussi la suite : « financ » trouve finance, financier.",
    ),
    (
        "ecarter",
        "Intitulés à écarter",
        "Un mot par ligne. Un intitulé qui contient l'un d'eux est écarté.",
    ),
)

_LEGENDE = (
    "Un mot = le début d'un mot (« rse » ne trouve pas « diverse »). « *mot » : aussi au "
    "milieu d'un mot (« *analyst » trouve Nachhaltigkeitsanalyst). « re: » : motif avancé."
)

# The two lists of chosen places, as shown; a place chosen in neither is simply lower.
_PRIO, _SEC = "Prioritaire", "Secondaire"


def _sans_fenetre() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _gardees(profil: Path | None = None) -> tuple[int, set[str]]:
    """(offers in the queue, identities kept by the title filter) — in its own process."""
    cmd = [PY, "-m", "jobhunter.programs.search_preview"]
    if profil is not None:
        cmd += ["--profil", str(profil)]
    r = subprocess.run(  # nosec B603 : our own program, arguments built here
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        creationflags=_sans_fenetre(),
    )
    d = json.loads(r.stdout.strip().splitlines()[-1])
    return int(d["total"]), set(d["gardees"])


class MaRechercheMixin:
    """The "Ma recherche" panel."""

    def _ma_recherche_panel(self: "AppTypee") -> None:
        self._hide_all()
        if "recherche" in self._panels:
            w = self._panels["recherche"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["recherche"] = w
        CL(
            w,
            text=_t(
                "Ces réglages appartiennent au profil actif. Ils servent à la prochaine collecte ; "
                "l'aperçu montre leur effet sur les offres déjà dans ta file."
            ),
            bg=WORK,
            fg=MUT,
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(fill="x", padx=28, pady=(10, 4))

        grille = CF(w, bg=WORK, plat=True)
        grille.pack(fill="both", expand=True, padx=28, pady=4)
        boites: dict[str, Any] = {}
        for i, (cle, titre, aide) in enumerate(_CHAMPS):
            col = CF(grille, bg=WORK, plat=True)
            col.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            grille.columnconfigure(i, weight=1, uniform="c")
            CL(col, text=titre, bg=WORK, fg=TX, font=(_theme.FONT_UI, 13, "bold"), anchor="w").pack(
                fill="x"
            )
            CL(
                col, text=_t(aide), bg=WORK, fg=MUT, anchor="w", justify="left", wraplength=280
            ).pack(fill="x", pady=(0, 4))
            b = ctk.CTkTextbox(
                col,
                height=200,
                font=(_theme.FONT_UI, 12),
                # one word per line: never cut a word in two
                wrap="none" if cle == "mots_cles" else "word",
            )
            b.pack(fill="both", expand=True)
            boites[cle] = b
        grille.rowconfigure(0, weight=1)
        CL(w, text=_t(_LEGENDE), bg=WORK, fg=MUT, anchor="w", justify="left", wraplength=1000).pack(
            fill="x", padx=28, pady=(4, 0)
        )

        # ── Where to work: search a place, keep only the chosen ones ──
        CL(
            w,
            text="Où tu veux travailler",
            bg=WORK,
            fg=TX,
            font=(_theme.FONT_UI, 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=28, pady=(10, 0))
        CL(
            w,
            text=_t(
                "La ville ne change pas le fit : elle remplit la colonne Zone (1 · prioritaire, "
                "2 · secondaire, puis le reste), pour trier et filtrer. Une ville non choisie "
                "reste visible, simplement plus bas. À l'étranger, écris le nom comme dans les "
                "offres (London, Geneva)."
            ),
            bg=WORK,
            fg=MUT,
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(fill="x", padx=28, pady=(0, 4))
        cherche = CF(w, bg=WORK, plat=True)
        cherche.pack(fill="x", padx=28, pady=(0, 4))
        champ_lieu = ctk.CTkEntry(
            cherche,
            width=360,
            placeholder_text=_t("Une ville, une région ou un pays…"),
        )
        champ_lieu.pack(side="left")
        # Packed only while it shows results: an empty CTkFrame keeps its 200 px.
        resultats = CF(w, bg=WORK, plat=True)
        choisis: dict[str, list[Any]] = {"prioritaires": [], "secondaires": []}
        rangees: dict[str, Any] = {}
        for cle, titre in (("prioritaires", _PRIO), ("secondaires", _SEC)):
            r_ = CF(w, bg=WORK, plat=True)
            r_.pack(fill="x", padx=28, pady=2)
            ctk.CTkLabel(r_, text=_t(titre) + " :", text_color=TX, anchor="w", width=110).pack(
                side="left"
            )
            rangees[cle] = CF(r_, bg=WORK, plat=True)
            rangees[cle].pack(side="left", fill="x", expand=True)

        def afficher_choisis() -> None:
            for cle, cadre in rangees.items():
                for enfant in cadre.winfo_children():
                    enfant.destroy()
                if not choisis[cle]:
                    CL(cadre, text=_t("aucune"), bg=WORK, fg=MUT).pack(side="left")
                for entree in choisis[cle]:
                    CB(
                        cadre,
                        text=f"{_reglages.libelle_lieu(entree)}  ✕",
                        command=lambda c=cle, e=entree: retirer_lieu(c, e),
                        bg=ACC if cle == "prioritaires" else BTN,
                        fg=ACC_TX if cle == "prioritaires" else TX,
                        relief="flat",
                        cursor="hand2",
                    ).pack(side="left", padx=(0, 6))

        def retirer_lieu(cle: str, entree: Any) -> None:
            ident = _reglages.cle_lieu(entree)
            choisis[cle] = [x for x in choisis[cle] if _reglages.cle_lieu(x) != ident]
            afficher_choisis()

        def ajouter_lieu(cle: str, entree: Any) -> None:
            ident = _reglages.cle_lieu(entree)
            for c in choisis:  # a place is in one list only
                choisis[c] = [x for x in choisis[c] if _reglages.cle_lieu(x) != ident]
            choisis[cle].append(entree)
            for enfant in resultats.winfo_children():
                enfant.destroy()
            resultats.pack_forget()
            champ_lieu.delete(0, "end")
            afficher_choisis()

        def rechercher_lieu() -> None:
            for enfant in resultats.winfo_children():
                enfant.destroy()
            trouves = _reglages.chercher_lieux(champ_lieu.get())
            resultats.pack(fill="x", padx=28, after=cherche)
            if not trouves:
                CL(resultats, text=_t("Tape au moins deux lettres."), bg=WORK, fg=MUT).pack(
                    anchor="w"
                )
            for entree, libelle in trouves:
                ligne = CF(resultats, bg=WORK, plat=True)
                ligne.pack(fill="x", pady=1)
                # CL ignores `width`: a fixed width keeps the buttons in one column.
                ctk.CTkLabel(ligne, text=libelle, text_color=TX, anchor="w", width=320).pack(
                    side="left"
                )
                for cle, titre in (("prioritaires", _PRIO), ("secondaires", _SEC)):
                    CB(
                        ligne,
                        text="+ " + _t(titre),
                        command=lambda c=cle, e=entree: ajouter_lieu(c, e),
                        bg=BTN,
                        fg=TX,
                        activebackground=BTN_H,
                        relief="flat",
                        cursor="hand2",
                    ).pack(side="left", padx=(0, 6))

        CB(
            cherche,
            text="Rechercher",
            command=rechercher_lieu,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=10)
        champ_lieu.bind("<Return>", lambda _e: rechercher_lieu())

        def lieux_choisis() -> tuple[list[Any], list[Any]]:
            return list(choisis["prioritaires"]), list(choisis["secondaires"])

        etat = CL(w, text="", bg=WORK, fg=MUT, anchor="w", justify="left", wraplength=1000)
        barre = CF(w, bg=WORK, plat=True)
        barre.pack(fill="x", padx=28, pady=(8, 4))
        etat.pack(fill="x", padx=28, pady=(0, 12))

        def reglages() -> _reglages.Reglages:
            prio, sec = lieux_choisis()
            return _reglages.Reglages(
                **{
                    c: _reglages.depuis_texte(boites[c].get("1.0", "end")) for c, _t1, _a in _CHAMPS
                },
                prioritaires=prio,
                secondaires=sec,
            )

        def brut() -> dict[str, Any]:
            return dict(json.loads(Path(_profil.FICHIER).read_text(encoding="utf-8")))

        def recharger() -> None:
            try:
                r = _reglages.lire(brut())
            except (OSError, ValueError) as e:
                etat.configure(text=f"! {type(e).__name__}: {e}")
                return
            for c, _t1, _a in _CHAMPS:
                boites[c].delete("1.0", "end")
                lignes = getattr(r, c)
                # A "re:(a|b|c)" list is shown one word per line (search_settings.eclater).
                if c != "mots_cles":
                    lignes = _reglages.eclater(lignes)
                boites[c].insert("1.0", "\n".join(lignes))
            choisis["prioritaires"] = list(r.prioritaires or [])
            choisis["secondaires"] = list(r.secondaires or [])
            afficher_choisis()
            etat.configure(text="")

        def enregistrer() -> None:
            r = reglages()
            if erreurs := _reglages.valider(r):
                messagebox.showwarning(
                    "JobHunter",
                    _t("Rien n'est enregistré :") + "\n· " + "\n· ".join(erreurs),
                    parent=self.root,
                )
                return
            fichier = Path(_profil.FICHIER)
            avant = _reglages.lire(brut())
            bak = _reglages.ecrire(fichier, _reglages.appliquer(brut(), r))
            _profil.recharger()
            if (avant.prioritaires, avant.secondaires) != (r.prioritaires, r.secondaires):
                # The Zone column of the offers already there follows the new places.
                self.run_step(
                    [PY, "-m", "jobhunter.scoring.zones", "--ecrire"],
                    _t("Zones des offres mises à jour"),
                )
            texte = _t(
                "Recherche enregistrée (profil d'avant : {bak}). Effet à la prochaine collecte."
            )
            etat.configure(text=texte.format(bak=bak.name))
            self._log(texte.format(bak=bak.name) + "\n")

        def apercu() -> None:
            r = reglages()
            if erreurs := _reglages.valider(r):
                etat.configure(text="! " + " ; ".join(erreurs))
                return
            etat.configure(text=_t("Aperçu en cours (filtre du moteur sur ta file)…"))
            candidat = Path(tempfile.gettempdir()) / "jobhunter_apercu_profil.json"
            candidat.write_text(
                json.dumps(_reglages.appliquer(brut(), r), ensure_ascii=False), encoding="utf-8"
            )

            def tache() -> None:
                try:
                    total, avant = _gardees()
                    _total, apres = _gardees(candidat)
                except Exception as e:
                    msg = f"! {_t('Aperçu impossible')} ({type(e).__name__})"
                else:
                    perdues = sorted(avant - apres)
                    msg = _t(
                        "Sur les {total} offres de ta file : {apres} passent ce filtre "
                        "(actuellement {avant})."
                    ).format(total=total, apres=len(apres), avant=len(avant))
                    if perdues:
                        msg += "\n" + _t("Seraient écartées, par exemple :") + " "
                        msg += " · ".join(p.replace("|", " — ") for p in perdues[:6])
                    msg += "\n" + _t("Élargir la recherche se voit à la prochaine collecte.")
                finally:
                    candidat.unlink(missing_ok=True)
                self.root.after(0, lambda: etat.configure(text=msg))

            threading.Thread(target=tache, daemon=True).start()

        def suggerer() -> None:
            p = filedialog.askopenfilename(
                parent=self.root,
                title=_t("Le CV à lire"),
                filetypes=[("CV", "*.docx *.pdf"), ("Word", "*.docx"), ("PDF", "*.pdf")],
            )
            if not p:
                return
            try:
                texte = _sugg.lire_cv(Path(p))
                liste = _sugg.suggestions(texte, brut())
            except Exception as e:
                messagebox.showerror("JobHunter", f"{type(e).__name__}: {e}", parent=self.root)
                return
            if not liste:
                etat.configure(text=_t("Rien de nouveau dans ce CV : ton profil a déjà tout."))
                return
            acceptees = self._choisir_suggestions(liste)
            if not acceptees:
                return
            competences = [s for s in acceptees if s.genre == "competence"]
            recherches = [s for s in acceptees if s.genre == "recherche"]
            if competences:
                fichier = Path(_profil.FICHIER)
                _reglages.ecrire(fichier, _sugg.appliquer(brut(), competences))
                _profil.recharger()
            if recherches:  # into the box: saved with the rest by "Enregistrer"
                b = boites["mots_cles"]
                deja = {x.lower() for x in _reglages.depuis_texte(b.get("1.0", "end"))}
                for s in recherches:
                    if s.libelle.lower() not in deja:
                        b.insert("end", ("\n" if b.get("1.0", "end").strip() else "") + s.libelle)
            etat.configure(
                text=_t(
                    "{c} compétence(s) ajoutée(s) au profil ; {r} recherche(s) ajoutée(s) "
                    "à la liste (Enregistrer pour les garder)."
                ).format(c=len(competences), r=len(recherches))
            )

        for texte, cmd, principal in (
            ("Enregistrer", enregistrer, True),
            ("Aperçu sur ma file", apercu, False),
            ("Suggestions depuis mon CV…", suggerer, False),
            ("Annuler les modifications", recharger, False),
        ):
            CB(
                barre,
                text=texte,
                command=cmd,
                bg=ACC if principal else BTN,
                fg=ACC_TX if principal else TX,
                activebackground=ACC_H if principal else BTN_H,
                relief="flat",
                cursor="hand2",
            ).pack(side="left", padx=(0, 12))

        w._reload = recharger
        w._chercher_lieu = lambda texte: (  # for the tests
            champ_lieu.delete(0, "end"),
            champ_lieu.insert(0, texte),
            rechercher_lieu(),
        )
        w._choisis = choisis
        recharger()
        w.pack(fill="both", expand=True)

    def _choisir_suggestions(
        self: "AppTypee", liste: list[_sugg.Suggestion]
    ) -> list[_sugg.Suggestion]:
        """A modal list of checkboxes, nothing ticked; returns the ticked suggestions."""
        f = ctk.CTkToplevel(self.root)
        f.title(_t("Suggestions depuis ton CV"))
        f.geometry("820x560")
        f.transient(self.root)
        ctk.CTkLabel(
            f,
            text=_t(
                "Coche ce que tu veux ajouter. Une compétence vient de ton CV (la phrase est "
                "citée) ; une recherche n'ajoute rien à tes CV ni à tes lettres."
            ),
            justify="left",
            wraplength=780,
        ).pack(padx=16, pady=(14, 6), anchor="w")
        zone = ctk.CTkScrollableFrame(f)
        zone.pack(fill="both", expand=True, padx=16, pady=6)
        cases: list[tuple[tk.BooleanVar, _sugg.Suggestion]] = []
        for s in liste:
            v = tk.BooleanVar(value=False)
            genre = _t("Compétence") if s.genre == "competence" else _t("Recherche")
            ctk.CTkCheckBox(
                zone, text=f"{genre} : {s.libelle}\n      « {s.phrase} »", variable=v
            ).pack(anchor="w", pady=3)
            cases.append((v, s))
        choix: dict[str, bool] = {"ok": False}

        def fin(ok: bool) -> None:
            choix["ok"] = ok
            f.destroy()

        bas = ctk.CTkFrame(f, fg_color="transparent")
        bas.pack(pady=(4, 14))
        ctk.CTkButton(bas, text=_t("Ajouter la sélection"), command=lambda: fin(True)).pack(
            side="left", padx=6
        )
        ctk.CTkButton(
            bas,
            text=_t("Annuler"),
            fg_color="transparent",
            border_width=1,
            text_color=TX,
            command=lambda: fin(False),
        ).pack(side="left", padx=6)
        f.protocol("WM_DELETE_WINDOW", lambda: fin(False))
        f.after(50, f.grab_set)
        self.root.wait_window(f)
        return [s for v, s in cases if v.get()] if choix["ok"] else []
