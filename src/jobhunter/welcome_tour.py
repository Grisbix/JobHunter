"""After the first profile: where JobHunter looks, the API keys, and a first collection.

Three steps in the welcome window (jobhunter.welcome, same look), before the
application opens:

1. the job sites read, with or without a key, and those not read;
2. the free API keys (France Travail, Adzuna, Jooble): where to get them, and their
   entry, written by jobhunter.api_keys into the files the sources read. Optional: a
   field left empty changes nothing; no value is read back or shown;
3. a short first collection (LinkedIn, V.I.E, Jobs that make sense, and the APIs whose
   key is there), its progress, then the best offers found and how the application is
   used day to day. JobHunter never sends an application: the last click is the user's.

Every step can be skipped; the application opens in any case.
"""

import os
import queue
import subprocess
import sys
import threading
import webbrowser
from typing import Any

from jobhunter import api_keys as _cles
from jobhunter import frozen as _gele
from jobhunter import root as _rac
from jobhunter import welcome as _w

# The sites, as the collection reads them (sources/cli.py, `--all`).
SITES = (
    (
        "Lus à chaque collecte, sans clé",
        (
            "LinkedIn : les offres publiques, par tes mots-clés",
            "Les pages carrières des entreprises suivies (Greenhouse, Lever, Workday…)",
            "V.I.E et V.I.A (Business France)",
            "Welcome to the Jungle, Jobs that make sense, EURES (portail de l'UE)",
            "eFinancialCareers et FIR, si tu vises la finance ou l'ESG",
        ),
    ),
    (
        "Lus avec une clé gratuite (étape suivante)",
        ("France Travail, Adzuna, Jooble : leurs API officielles",),
    ),
    (
        "Pas lus",
        (
            "APEC, Glassdoor, Indeed : ils refusent les robots, et JobHunter ne contourne "
            "pas un refus",
        ),
    ),
)
# What each key brings, in one line.
APPORT = {
    "francetravail": "les offres de France Travail (ex-Pôle emploi), toute la France",
    "adzuna": "un agrégateur : des milliers d'offres de sites d'emploi",
    "jooble": "un autre agrégateur, utile hors de France",
}
SCAN_DE_BASE = ["--linkedin", "--vie", "--makesense", "--pages", "1"]
SCAN_CLES = {"francetravail": "--ft", "adzuna": "--adzuna", "jooble": "--jooble"}


def _etape(fenetre: Any, numero: int, titre: str, intro: str) -> tuple[Any, Any, Any]:
    """A step's panel: its number, title and introduction. (card, body, button row)."""
    import customtkinter as ctk

    carte = _w._carte(fenetre)
    corps = ctk.CTkFrame(carte, fg_color="transparent")
    corps.pack(fill="both", expand=True, padx=26, pady=(22, 0))
    _w._texte(corps, f"Étape {numero} sur 3", couleur=_w.TEXTE_DOUX, taille=12).pack(anchor="w")
    _w._texte(corps, titre, taille=26, gras=True).pack(anchor="w", pady=(2, 0))
    _w._texte(corps, intro, couleur=_w.TEXTE_DOUX, largeur=600).pack(anchor="w", pady=(6, 12))
    bas = ctk.CTkFrame(carte, fg_color="transparent")
    bas.pack(side="bottom", fill="x", padx=26, pady=(8, 22))
    return carte, corps, bas


def _attendre(fenetre: Any, carte: Any, defaut: str) -> str:
    """Shows the step and waits for its answer ("suivant", "passer"…)."""
    choix = {"r": defaut}

    def fin(r: str) -> None:
        choix["r"] = r
        fenetre.quit()

    fenetre._choisir = fin
    _w._fermeture(fenetre, lambda: fin("passer"))
    _w._montrer(fenetre)
    fenetre.mainloop()
    carte.destroy()
    fenetre.withdraw()
    return choix["r"]


def etape_sites(fenetre: Any) -> str:
    """Step 1: the sites read, with or without a key, and those not read."""
    import customtkinter as ctk

    carte, corps, bas = _etape(
        fenetre,
        1,
        "Où JobHunter cherche",
        "Chaque collecte lit ces sites avec les mots-clés tirés de ton CV, garde les offres "
        "qui te correspondent et les note sur 10. Tu changes les mots-clés dans « Ma "
        "recherche », et chaque site dans « Sources ».",
    )
    for titre, lignes in SITES:
        bloc = ctk.CTkFrame(corps, fg_color=_w.PISTE, corner_radius=_w.RAD_BOUTON)
        bloc.pack(fill="x", pady=5)
        _w._texte(bloc, titre, gras=True).pack(anchor="w", padx=14, pady=(10, 2))
        for l in lignes:
            _w._texte(bloc, f"·  {l}", couleur=_w.ENCRE, largeur=580).pack(anchor="w", padx=14)
        ctk.CTkFrame(bloc, fg_color="transparent", height=8).pack()
    _w._bouton(bas, "Suivant", lambda: fenetre._choisir("suivant"), principal=True).pack(
        side="left"
    )
    _w._bouton(bas, "Passer la visite", lambda: fenetre._choisir("passer")).pack(side="right")
    return _attendre(fenetre, carte, "passer")


def etape_cles(fenetre: Any) -> str:
    """Step 2: the free API keys, their official page and their entry."""
    import customtkinter as ctk

    carte, corps, bas = _etape(
        fenetre,
        2,
        "Les clés API, gratuites",
        "Facultatif, mais souvent les sources les plus riches. Compte développeur gratuit "
        "sur la page officielle, puis colle la clé ici : elle reste sur ce PC. Plus tard : "
        "« Accès » → Collecte des offres.",
    )
    dossier = _rac.dossier_cles()
    champs: dict[str, dict[str, Any]] = {}
    etats: dict[str, Any] = {}
    for nom, cle in _cles.CLES.items():
        bloc = ctk.CTkFrame(corps, fg_color=_w.PISTE, corner_radius=_w.RAD_BOUTON)
        bloc.pack(fill="x", pady=5)
        tete = ctk.CTkFrame(bloc, fg_color="transparent")
        tete.pack(fill="x", padx=14, pady=(10, 0))
        _w._texte(tete, cle.libelle, gras=True).pack(side="left")
        _w._texte(tete, f" · {APPORT.get(nom, '')}", couleur=_w.TEXTE_DOUX, taille=12).pack(
            side="left"
        )
        etats[nom] = _w._texte(tete, "", couleur=_w.TEXTE_DOUX, taille=12)
        etats[nom].pack(side="right", padx=(10, 0))
        ctk.CTkButton(
            tete,
            text="Obtenir une clé ↗",
            command=lambda u=cle.obtenir: webbrowser.open(u),
            fg_color="transparent",
            hover_color=_w.SURVOL,
            text_color=_w.BRUN,
            font=_w._police(12, True),
            width=10,
            height=26,
        ).pack(side="right")
        ligne = ctk.CTkFrame(bloc, fg_color="transparent")
        ligne.pack(fill="x", padx=14, pady=(4, 10))
        champs[nom] = {}
        for champ in cle.champs:
            e = ctk.CTkEntry(
                ligne,
                placeholder_text=champ,
                width=250,
                height=34,
                corner_radius=_w.RAD_CHAMP,
                border_width=1,
                border_color=_w.BORD_CHAMP,
                fg_color=_w.SURFACE,
                text_color=_w.ENCRE,
                font=_w._police(12),
                show="•" if champ in cle.secrets else "",
            )
            e.pack(side="left", padx=(0, 8))
            champs[nom][champ] = e

    def montrer_etats() -> None:
        for nom in _cles.CLES:
            ok = _cles.presente(dossier, nom)
            etats[nom].configure(
                text="✓ clé posée" if ok else "pas de clé",
                text_color=_w.BRUN if ok else _w.TEXTE_DOUX,
            )

    retour = _w._texte(corps, "", couleur=_w.BAD, largeur=600)
    retour.pack(anchor="w", pady=(6, 0))

    def enregistrer() -> None:
        erreurs = []
        for nom, es in champs.items():
            valeurs = {k: e.get() for k, e in es.items()}
            if not any(v.strip() for v in valeurs.values()):
                continue  # nothing typed: the file stays as it is
            try:
                _cles.enregistrer(dossier, nom, valeurs)
            except (OSError, ValueError) as ex:
                erreurs.append(f"{_cles.CLES[nom].libelle} : {ex}")
        for es in champs.values():
            for e in es.values():
                e.delete(0, "end")
        montrer_etats()
        if erreurs:
            retour.configure(text="\n".join(erreurs))
            return
        fenetre._choisir("suivant")

    montrer_etats()
    _w._bouton(bas, "Enregistrer et continuer", enregistrer, principal=True).pack(side="left")
    _w._bouton(bas, "Plus tard", lambda: fenetre._choisir("suivant")).pack(side="left", padx=8)
    _w._bouton(bas, "Passer la visite", lambda: fenetre._choisir("passer")).pack(side="right")
    return _attendre(fenetre, carte, "passer")


def commande_scan(dossier_cles: Any) -> list[str]:
    """The first collection: quick sources, plus each API whose key is there."""
    args = list(SCAN_DE_BASE)
    for nom, option in SCAN_CLES.items():
        if _cles.presente(dossier_cles, nom):
            args.append(option)
    return [str(_gele.interpreteur()), "-m", "jobhunter", "collect", *args]


def meilleures(n: int = 5) -> tuple[int, list[Any]]:
    """(offers in the queue, the n best by fit) once the collection has merged."""
    from jobhunter.storage import queue as _file

    offres = _file.charger(descriptions=False)

    def note(o: Any) -> float:
        try:
            return float(o.get("fit") or 0)
        except (TypeError, ValueError):
            return 0.0

    return len(offres), sorted(offres, key=note, reverse=True)[:n]


def etape_scan(fenetre: Any) -> str:
    """Step 3: a short collection, its progress, the best offers and what comes next."""
    import customtkinter as ctk

    carte, corps, bas = _etape(
        fenetre,
        3,
        "Ton premier scan",
        "Une collecte courte pour voir comment ça marche : LinkedIn, les V.I.E et Jobs that "
        "make sense, plus les API dont tu as posé la clé. Quelques minutes. La collecte "
        "complète, tous les sites, se lance ensuite avec « Actualiser les offres », ou "
        "chaque matin toute seule si tu l'actives.",
    )
    journal = ctk.CTkTextbox(
        corps,
        height=170,
        fg_color=_w.SURFACE,
        text_color=_w.TEXTE_DOUX,
        border_width=1,
        border_color=_w.BORD_CHAMP,
        corner_radius=_w.RAD_CHAMP,
        font=_w._police(11),
        wrap="word",
    )
    barre = ctk.CTkProgressBar(corps, mode="indeterminate", progress_color=_w.BRUN, height=6)
    resultat = ctk.CTkFrame(corps, fg_color="transparent")
    etat: dict[str, Any] = {"proc": None, "lignes": queue.Queue()}

    def lire(proc: Any) -> None:
        for l in proc.stdout:
            etat["lignes"].put(l.rstrip())
        etat["lignes"].put(None)

    def suivre() -> None:
        fini = False
        while True:
            try:
                l = etat["lignes"].get_nowait()
            except queue.Empty:
                break
            if l is None:
                fini = True
                break
            if l.strip():
                journal.configure(state="normal")
                journal.insert("end", l + "\n")
                journal.see("end")
                journal.configure(state="disabled")
        if fini:
            etat["proc"].wait()
            terminer(etat["proc"].returncode)
        else:
            fenetre.after(200, suivre)

    def lancer() -> None:
        for w in bas.winfo_children():
            w.destroy()
        journal.pack(fill="x", pady=(0, 8))
        barre.pack(fill="x")
        barre.start()
        _w._bouton(bas, "Arrêter", arreter).pack(side="right")
        try:
            etat["proc"] = subprocess.Popen(  # nosec B603 : our own program, fixed arguments
                commande_scan(_rac.dossier_cles()),
                cwd=str(_rac.racine()),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as e:
            journal.insert("end", f"Impossible de lancer la collecte : {e}\n")
            terminer(1)
            return
        threading.Thread(target=lire, args=(etat["proc"],), daemon=True).start()
        fenetre.after(200, suivre)

    def arreter() -> None:
        if etat["proc"] and etat["proc"].poll() is None:
            etat["proc"].terminate()

    def terminer(code: int) -> None:
        barre.stop()
        barre.pack_forget()
        for w in bas.winfo_children():
            w.destroy()
        try:
            total, top = meilleures(3)
        except Exception:  # noqa: BLE001 — no queue yet: shown as 0
            total, top = 0, []
        # The result replaces the introduction and the log: the window keeps its height.
        for w in corps.winfo_children()[2:]:
            if w is not resultat:
                w.pack_forget()
        resultat.pack(fill="x", pady=(4, 0))
        if total:
            _w._texte(resultat, f"{total} offres dans ta file. Les mieux notées :", gras=True).pack(
                anchor="w"
            )
            for o in top:
                _w._texte(
                    resultat,
                    f"·  {o.get('fit') or '–'}/10  {o.get('poste') or ''} — {o.get('entreprise') or ''}",
                    largeur=600,
                ).pack(anchor="w")
        else:
            _w._texte(
                resultat,
                "Aucune offre pour l'instant"
                + (" (collecte arrêtée)." if code else ".")
                + " Élargis tes mots-clés dans « Ma recherche », puis « Actualiser les offres ».",
                largeur=600,
            ).pack(anchor="w")
        _w._texte(resultat, "Ensuite, dans JobHunter", gras=True).pack(anchor="w", pady=(12, 2))
        for l in (
            "1. « Offres » : la liste triée par note ; ouvre une offre pour la lire.",
            "2. « Voir CV » et « Voir lettre » : un CV et une lettre adaptés à l'offre, à relire.",
            "3. Tu postules toi-même sur le site de l'offre : JobHunter n'envoie jamais rien.",
            "4. « Suivi et note ▸ » garde l'état de chaque candidature ; « Statistiques » fait le bilan.",
        ):
            _w._texte(resultat, l, largeur=600).pack(anchor="w")
        _w._bouton(bas, "Ouvrir JobHunter", lambda: fenetre._choisir("fini"), principal=True).pack(
            side="left"
        )
        _w._centrer(fenetre)

    journal.configure(state="disabled")
    _w._bouton(bas, "Lancer le premier scan", lancer, principal=True).pack(side="left")
    _w._bouton(bas, "Plus tard", lambda: fenetre._choisir("passer")).pack(side="right")
    r = _attendre(fenetre, carte, "passer")
    arreter()
    return r


def visite(fenetre: Any) -> None:
    """The three steps; any "skip" opens the application straight away."""
    for etape in (etape_sites, etape_cles, etape_scan):
        if etape(fenetre) == "passer":
            return


if __name__ == "__main__":  # a look at the steps, on the current data folder
    _r = _w.fenetre_accueil()
    visite(_r)
    _r.destroy()
    sys.exit(0)
