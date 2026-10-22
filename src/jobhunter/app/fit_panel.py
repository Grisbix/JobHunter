"""The "Fit" tab of the Profil panel: how the fit is computed, with its weights to tune.

Each weight of the fit (one per axis, the score worth 10, the title's junior bonus and
senior penalty, the penalty per years of experience asked for) has its slider. Moving
one recomputes at once, without writing anything:
  - the queue: mean fit, offers at 8 and more, distribution 1-10 — against the saved
    weights, drawn as outlines;
  - the offer selected in the table: its fit and the steps of its computation.
Nothing is written before "Enregistrer", which keeps the previous profile as `.bak` and
offers to recompute the fit stored for every offer (rescore_ats).

The components of the queue's offers (what no weight changes, scoring.fit.Composantes)
are read once by programs.fit_components in a separate process: ten thousand texts take
about thirty seconds, which would freeze the window. A change of weights then costs a
few milliseconds (scoring.weights.bilan).
"""

import json
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from jobhunter import profile as _profil
from jobhunter import search_settings as _reglages
from jobhunter.app import language as _langue
from jobhunter.app import theme as _theme
from jobhunter.app.common import PY
from jobhunter.app.language import t as _t
from jobhunter.app.theme import (
    ACC,
    ACC_H,
    ACC_TX,
    BTN,
    BTN_H,
    CARD,
    CB,
    CF,
    CL,
    LINE,
    MUT,
    OK,
    TX,
    WORK,
)
from jobhunter.scoring import weights as _poids

if TYPE_CHECKING:
    from jobhunter.app._app_type import AppTypee
    from jobhunter.scoring.fit import Composantes

# slider ranges: (from, to, step)
_AXE = (0.0, 5.0, 0.25)
_CIBLE = (0.5, 8.0, 0.25)
_BONUS = (0.0, 4.0, 0.5)
_MALUS_EXP = (0.0, 9.0, 0.5)


def _nom_axe(axe: str) -> str:
    return axe.upper() if len(axe) <= 3 else axe.capitalize()


def _chiffre(v: float) -> str:
    return f"{v:g}".replace(".", ",")


def lire_composantes() -> tuple[list[str], list["Composantes"]]:
    """The queue's components, read by programs.fit_components in its own process."""
    from jobhunter.programs.fit_components import depuis_ligne

    r = subprocess.run(  # nosec B603 : our own program, arguments built here
        [PY, "-m", "jobhunter.programs.fit_components"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1:] or "fit_components")
    d = json.loads(r.stdout)
    axes = list(d["axes"])
    return axes, [depuis_ligne(x, axes) for x in d["lignes"]]


class FitMixin:
    def _construire_fit(self: "AppTypee", parent: Any) -> Any:
        """The "Fit" tab of the Profil panel. Built once; `_reload()` at each display."""
        w = CF(parent, bg=WORK, plat=True)
        intro = CL(
            w,
            text=_t(
                "Le fit va de 1 à 10. Chaque axe compte la part de ses compétences que "
                "l'annonce cite, multipliée par son poids ; la somme, rapportée au score qui "
                "vaut 10, donne la note de vocabulaire. Un plafond la borne ensuite (part du "
                "cœur de cible, intitulé, langue), puis viennent le bonus ou le malus de "
                "l'intitulé et le malus d'expérience demandée. Bouge un poids : la file et "
                "l'offre choisie sont recalculées tout de suite ; rien n'est écrit avant "
                "« Enregistrer »."
            ),
            bg=WORK,
            fg=MUT,
            anchor="w",
            justify="left",
            # Fixed and modest: CustomTkinter scales it (x1.5 on a high-DPI screen),
            # and recomputing it on <Configure> froze Tk in a geometry loop.
            wraplength=820,
        )
        intro.pack(fill="x", padx=28, pady=(10, 6))

        corps = CF(w, bg=WORK, plat=True)
        corps.pack(fill="both", expand=True, padx=28, pady=4)
        corps.columnconfigure(0, weight=5, uniform="f")
        corps.columnconfigure(1, weight=6, uniform="f")
        corps.rowconfigure(0, weight=1)

        # ── left: the weights ──
        gauche = ctk.CTkScrollableFrame(corps, fg_color=CARD, corner_radius=_theme.RAD_CARD)
        gauche.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        gauche.columnconfigure(1, weight=1)
        curseurs: dict[str, tuple[Any, Any, Any]] = {}  # key -> (slider, value, saved)
        etat: dict[str, Any] = {"enregistre": None, "composantes": None, "offre": None}
        prevu: list[str] = []

        def section(titre: str, aide: str) -> None:
            ligne = gauche.grid_size()[1]
            CL(
                gauche,
                text=_t(titre),
                bg=CARD,
                fg=TX,
                font=(_theme.FONT_UI, 13, "bold"),
                anchor="w",
            ).grid(row=ligne, column=0, columnspan=4, sticky="ew", padx=14, pady=(14, 0))
            CL(
                gauche,
                text=_t(aide),
                bg=CARD,
                fg=MUT,
                anchor="w",
                justify="left",
                wraplength=360,
            ).grid(row=ligne + 1, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 4))

        def curseur(cle: str, libelle: str, bornes: tuple[float, float, float]) -> None:
            ligne = gauche.grid_size()[1]
            de, a, pas = bornes
            CL(gauche, text=libelle, bg=CARD, fg=TX, anchor="w").grid(
                row=ligne, column=0, sticky="w", padx=(14, 8), pady=3
            )
            s = ctk.CTkSlider(
                gauche,
                from_=de,
                to=a,
                number_of_steps=round((a - de) / pas),
                command=lambda _v: changer(),
                button_color=ACC,
                button_hover_color=ACC_H,
                progress_color=ACC,
            )
            s.grid(row=ligne, column=1, sticky="ew", padx=4)
            valeur = CL(gauche, text="", bg=CARD, fg=TX, font=(_theme.FONT_UI, 12, "bold"))
            valeur.configure(width=44)
            valeur.grid(row=ligne, column=2, sticky="e", padx=(4, 4))
            avant = CL(gauche, text="", bg=CARD, fg=MUT, anchor="w")
            avant.configure(width=90)
            avant.grid(row=ligne, column=3, sticky="w", padx=(0, 14))
            curseurs[cle] = (s, valeur, avant)

        # ── right: the queue, then the selected offer ──
        droite = CF(corps, bg=WORK, plat=True)
        droite.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        file_ = CF(droite, bg=CARD)
        file_.pack(fill="x")
        CL(
            file_, text=_t("Ta file"), bg=CARD, fg=TX, font=(_theme.FONT_UI, 13, "bold"), anchor="w"
        ).pack(fill="x", padx=14, pady=(12, 0))
        chiffres = CF(file_, bg=CARD, plat=True)
        chiffres.pack(fill="x", padx=14, pady=(4, 0))
        moyenne = CL(chiffres, text="—", bg=CARD, fg=ACC, font=(_theme.FONT_UI, 28))
        moyenne.pack(side="left")
        detail = CL(chiffres, text="", bg=CARD, fg=MUT, anchor="w", justify="left")
        detail.pack(side="left", padx=14)
        histo = tk.Canvas(file_, height=120, bg=CARD, highlightthickness=0)
        histo.pack(fill="x", padx=14, pady=(6, 12))

        offre = CF(droite, bg=CARD)
        offre.pack(fill="both", expand=True, pady=(12, 0))
        titre_offre = CL(
            offre,
            text="",
            bg=CARD,
            fg=TX,
            font=(_theme.FONT_UI, 13, "bold"),
            anchor="w",
            justify="left",
            wraplength=460,
        )
        titre_offre.pack(fill="x", padx=14, pady=(12, 0))
        # A text box, not a label: the steps of a rich offer are longer than the card.
        raisons = ctk.CTkTextbox(
            offre, wrap="word", fg_color=CARD, text_color=TX, font=(_theme.FONT_UI, 12)
        )

        def ecrire_raisons(texte: str) -> None:
            raisons.configure(state="normal")
            raisons.delete("1.0", "end")
            raisons.insert("1.0", texte)
            raisons.configure(state="disabled")

        raisons.pack(fill="both", expand=True, padx=14, pady=(4, 12))

        message = CL(w, text="", bg=WORK, fg=MUT, anchor="w", justify="left", wraplength=820)
        barre = CF(w, bg=WORK, plat=True)
        # Before the body, at the bottom: packed after it, the buttons went out of the
        # window once the Profil panel's tabs took their height.
        message.pack(side="bottom", fill="x", padx=28, pady=(0, 12), before=corps)
        barre.pack(side="bottom", fill="x", padx=28, pady=(10, 2), before=corps)

        def brut() -> dict[str, Any]:
            return dict(json.loads(Path(_profil.FICHIER).read_text(encoding="utf-8")))

        def courante() -> _poids.Ponderation:
            e: _poids.Ponderation = etat["enregistre"]
            return _poids.Ponderation(
                axes={a: float(curseurs[f"axe:{a}"][0].get()) for a in e.axes},
                cible=float(curseurs["cible"][0].get()),
                bonus_junior=float(curseurs["bonus_junior"][0].get()),
                malus_senior=float(curseurs["malus_senior"][0].get()),
                malus_experience={
                    s: float(curseurs[f"exp:{s}"][0].get()) for s in e.malus_experience
                },
            )

        def valeurs(p: _poids.Ponderation) -> dict[str, float]:
            v = {f"axe:{a}": x for a, x in p.axes.items()}
            v.update(cible=p.cible, bonus_junior=p.bonus_junior, malus_senior=p.malus_senior)
            v.update({f"exp:{s}": m for s, m in p.malus_experience.items()})
            return v

        def construire(p: _poids.Ponderation) -> None:
            """The sliders of the profile's weights (axes and steps come from it)."""
            for enfant in gauche.winfo_children():
                enfant.destroy()
            curseurs.clear()
            section(
                "Poids des axes",
                "Combien compte chaque axe du profil quand l'annonce cite ses compétences.",
            )
            for a in p.axes:
                curseur(f"axe:{a}", _nom_axe(a), _AXE)
            section(
                "Score qui vaut 10",
                "La somme pondérée des axes qui donne 10. Plus bas : les notes montent.",
            )
            curseur("cible", _t("Score pour 10"), _CIBLE)
            section("Intitulé", "Ajouté ou retiré selon les mots du titre de l'offre.")
            curseur("bonus_junior", _t("Bonus junior"), _BONUS)
            curseur("malus_senior", _t("Malus senior"), _BONUS)
            if p.malus_experience:
                section(
                    "Expérience demandée",
                    "Retiré quand l'annonce demande au moins ce nombre d'années.",
                )
                for s in sorted(p.malus_experience):
                    curseur(f"exp:{s}", _t("{n} ans et plus").format(n=s), _MALUS_EXP)

        def poser(p: _poids.Ponderation) -> None:
            for cle, v in valeurs(p).items():
                if cle in curseurs:
                    curseurs[cle][0].set(v)
            changer(tout_de_suite=True)

        def changer(tout_de_suite: bool = False) -> None:
            if etat["enregistre"] is None:
                return
            for cle, (s, valeur, _a) in curseurs.items():
                valeur.configure(text=_chiffre(float(s.get())))
            if prevu:
                w.after_cancel(prevu.pop())
            if tout_de_suite:
                recalculer()
            else:
                prevu.append(w.after(60, recalculer))

        def recalculer() -> None:
            prevu.clear()
            p, e = courante(), etat["enregistre"]
            ve, vc = valeurs(e), valeurs(p)
            for cle, (_s, valeur, avant) in curseurs.items():
                change = abs(vc[cle] - ve[cle]) > 1e-9
                avant.configure(
                    text=_t("avant : {v}").format(v=_chiffre(ve[cle])) if change else ""
                )
                valeur.configure(text_color=ACC if change else TX)
            dessiner_file(p, e)
            dessiner_offre(p)

        def dessiner_file(p: _poids.Ponderation, e: _poids.Ponderation) -> None:
            cs = etat["composantes"]
            if cs is None:
                return
            if not cs:
                moyenne.configure(text="—")
                detail.configure(text=_t("Ta file est vide."))
                histo.delete("all")
                return
            b, b0 = _poids.bilan(cs, p), _poids.bilan(cs, e)
            moyenne.configure(text=f"{b.moyenne:.2f}".replace(".", ","))
            lignes = [_t("fit moyen sur {n} offres").format(n=b.n)]
            if p != e:
                lignes.append(
                    _t("enregistré : {m} · fit ≥ 8 : {h} (enregistré : {h0})").format(
                        m=f"{b0.moyenne:.2f}".replace(".", ","), h=b.haut, h0=b0.haut
                    )
                )
            else:
                lignes.append(_t("fit ≥ 8 : {h} offres").format(h=b.haut))
            detail.configure(text="\n".join(lignes))
            histogramme(b, b0)

        def histogramme(b: _poids.Bilan, b0: _poids.Bilan) -> None:
            histo.delete("all")
            larg = max(histo.winfo_width(), 300)
            haut = int(histo.cget("height"))
            pied, tete = 18, 22
            plus = max([*b.repartition.values(), *b0.repartition.values(), 1])
            pas = larg / 10
            for f in range(1, 11):
                x0 = (f - 1) * pas + pas * 0.18
                x1 = f * pas - pas * 0.18
                h = (haut - pied - tete) * b.repartition[f] / plus
                h0 = (haut - pied - tete) * b0.repartition[f] / plus
                histo.create_rectangle(
                    x0, haut - pied - h, x1, haut - pied, fill=OK if f >= 8 else ACC, width=0
                )
                histo.create_rectangle(
                    x0, haut - pied - h0, x1, haut - pied, outline=LINE if h0 <= h else MUT, width=1
                )
                histo.create_text(
                    (x0 + x1) / 2, haut - pied / 2, text=str(f), fill=MUT, font=(_theme.FONT_UI, 9)
                )
                histo.create_text(
                    (x0 + x1) / 2,
                    haut - pied - h - 7,
                    text=str(b.repartition[f]),
                    fill=TX,
                    font=(_theme.FONT_UI, 8),
                )

        def dessiner_offre(p: _poids.Ponderation) -> None:
            o = etat["offre"]
            if o is None:
                titre_offre.configure(text=_t("Aucune offre choisie"))
                ecrire_raisons(
                    _t(
                        "Sélectionne une offre dans le tableau, puis reviens ici : le détail "
                        "de son fit s'affiche et suit tes réglages."
                    )
                )
                return
            from jobhunter.programs.fit_components import texte
            from jobhunter.scoring.fit import expliquer

            try:
                lignes = expliquer(texte(o), o.get("poste", ""), p)
            except Exception as ex:  # an incomplete profile must not break the panel
                ecrire_raisons(f"! {type(ex).__name__}: {ex}")
                return
            fit = lignes[-1].removeprefix("fit ")
            stocke = str(o.get("fit") or "—")
            entete = f"{o.get('entreprise', '')} — {o.get('poste', '')}"
            titre_offre.configure(text=entete)
            corps_ = "\n".join("· " + _langue.explication(x) for x in lignes[:-1])
            ecrire_raisons(
                _t("Fit : {fit} (dans la file : {stocke})").format(fit=fit, stocke=stocke)
                + "\n\n"
                + corps_
            )

        def charger_file() -> None:
            etat["composantes"] = None
            moyenne.configure(text="…")
            detail.configure(text=_t("Lecture des offres de ta file… (une trentaine de secondes)"))
            histo.delete("all")

            def tache() -> None:
                try:
                    _axes, cs = lire_composantes()
                    err = ""
                except Exception as ex:
                    cs, err = [], f"! {_t('Lecture impossible')} ({type(ex).__name__})"

                def fin() -> None:
                    etat["composantes"] = cs
                    if err:
                        detail.configure(text=err)
                        moyenne.configure(text="—")
                    else:
                        changer(tout_de_suite=True)

                self.root.after(0, fin)

            threading.Thread(target=tache, daemon=True).start()

        def recharger(relire_file: bool = False) -> None:
            from jobhunter.scoring.fit import ponderation

            try:
                _profil.recharger()
                e = ponderation()
            except Exception as ex:
                message.configure(text=f"! {type(ex).__name__}: {ex}")
                return
            if (
                etat["enregistre"] is None
                or set(e.axes) != set(etat["enregistre"].axes)
                or set(e.malus_experience) != set(etat["enregistre"].malus_experience)
            ):
                construire(e)
            etat["enregistre"] = e
            etat["offre"] = self.rowmap.get(self.tree.focus()) if hasattr(self, "tree") else None
            poser(e)
            message.configure(text="")
            if relire_file or etat["composantes"] is None:
                charger_file()

        def annuler() -> None:
            poser(etat["enregistre"])
            message.configure(text="")

        def enregistrer() -> None:
            p = courante()
            if p == etat["enregistre"]:
                message.configure(text=_t("Rien à enregistrer : les poids sont ceux du profil."))
                return
            if erreurs := _poids.valider(p):
                messagebox.showwarning(
                    "JobHunter",
                    _t("Rien n'est enregistré :") + "\n· " + "\n· ".join(erreurs),
                    parent=self.root,
                )
                return
            bak = _reglages.ecrire(Path(_profil.FICHIER), _poids.appliquer(brut(), p))
            recharger()
            texte = _t("Pondération enregistrée (profil d'avant : {bak}).").format(bak=bak.name)
            message.configure(text=texte)
            self._log(texte + "\n")
            if messagebox.askyesno(
                "JobHunter",
                _t(
                    "Recalculer maintenant le fit enregistré de chaque offre de ta file ? "
                    "Le tableau et le tri l'utilisent."
                ),
                parent=self.root,
            ):
                self.run_step([PY, "-m", "jobhunter.programs.rescore_ats"], _t("Recalculer le fit"))

        for texte_, cmd, principal in (
            ("Enregistrer", enregistrer, True),
            ("Annuler les modifications", annuler, False),
            ("Relire la file", lambda: recharger(relire_file=True), False),
        ):
            CB(
                barre,
                text=texte_,
                command=cmd,
                bg=ACC if principal else BTN,
                fg=ACC_TX if principal else TX,
                activebackground=ACC_H if principal else BTN_H,
                relief="flat",
                cursor="hand2",
            ).pack(side="left", padx=(0, 12))

        def redimensionner(_e: Any) -> None:
            if etat["composantes"] and etat["enregistre"] is not None:
                p, e = courante(), etat["enregistre"]
                histogramme(
                    _poids.bilan(etat["composantes"], p), _poids.bilan(etat["composantes"], e)
                )

        histo.bind("<Configure>", redimensionner)
        w._reload = recharger
        # for the tests and the screenshots
        w._etat, w._curseurs, w._changer, w._enregistrer = etat, curseurs, changer, enregistrer
        return w
