"""The desktop's side panels for the web interface.

Statistics, access and keys, followed companies, job boards.

The same data and the same files as `jobhunter.app.panels`, without a window: the
desktop module draws Tk widgets, this one returns JSON for the page. `Api` (api.py)
inherits these methods; they use its `_file()`, `_suivi()` and task runner.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# What the connection test found (sources.connexion.Resultat.etat), said plainly.
MESSAGES_TEST = {
    "ok": "{nom} : connexion vérifiée, la clé fonctionne.",
    "absente": "{nom} : aucune clé enregistrée (Saisir la clé).",
    "refusee": "{nom} : clé refusée par le service — vérifie-la ou crée-en une nouvelle.",
    "quota": "{nom} : quota atteint — la clé est bonne, réessaie demain.",
    "panne": "{nom} : le service répond mais en erreur — réessaie plus tard.",
    "reseau": "{nom} : pas de réponse (hors ligne ?).",
}

# General job sites: they go in "Sites d'offres", not among the companies.
BOARD_HOSTS = (
    "linkedin",
    "indeed",
    "welcometothejungle",
    "glassdoor",
    "efinancialcareers",
    "wizbii",
    "jobteaser",
    "hellowork",
    "apec.fr",
    "meteojob",
    "monster",
    "jobs.smartrecruiters",
    "engagement-jeunes",
    "wttj",
)

ATS_URL = {
    "greenhouse": "https://boards.greenhouse.io/{s}",
    "lever": "https://jobs.lever.co/{s}",
    "ashby": "https://jobs.ashbyhq.com/{s}",
    "recruitee": "https://{s}.recruitee.com",
    "smartrecruiters": "https://careers.smartrecruiters.com/{s}",
}


def _est_board(url: str) -> bool:
    return any(b in url.lower() for b in BOARD_HOSTS)


def _ecrire_json(f: Path, donnees: Any) -> None:
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def _date_fr(iso: Any) -> str:
    t = str(iso or "")[:10]
    return f"{t[8:10]}/{t[5:7]}/{t[:4]}" if len(t) == 10 and t[4] == "-" else ""


def _session(session: Any, verification: Any) -> tuple[str, str]:
    """A historical check is not a proof of current login (app.theme._session_presentation)."""
    import datetime

    if not verification:
        return "Jamais vérifié", ""
    try:
        age = (datetime.date.today() - datetime.date.fromisoformat(str(verification)[:10])).days
    except ValueError:
        age = None
    if age is None or age < 0 or age > 7:
        return "À revérifier", "ancien"
    noms = {
        "connecte": "Connecté",
        "deconnecte": "Déconnecté",
        "bloque": "Bloqué",
        "erreur": "Erreur",
    }
    return noms.get(str(session), "Indéterminé"), (
        "ok"
        if session == "connecte"
        else "ko"
        if session in ("deconnecte", "bloque", "erreur")
        else ""
    )


def statistiques(q: list[Any], sv: Any) -> dict[str, Any]:
    """The desktop's Stats panel: cards, then sections of (label, n, share)."""
    from jobhunter import funnel, profile
    from jobhunter.links import existe
    from jobhunter.storage import queue as queue_io

    st = [str((v or {}).get("s") or "").lower() for v in sv.values()]
    ok = [o for o in q if str(o.get("link_status") or "").upper() not in ("MORT", "EXPIREE")]

    def fichier(u: Any) -> bool:
        try:
            return bool(u) and bool(existe(u))
        except Exception:  # noqa: BLE001 — an unreadable path counts as absent
            return False

    top = [o for o in ok if (o.get("fit") or 0) >= 8]
    pretes, sans_doc, sans_desc, douteux = [], [], [], []
    for o in top:
        if not (fichier(o.get("cv")) and fichier(o.get("lettre"))):
            sans_doc.append(o)
        elif len(str(o.get("description") or "")) < 200:
            sans_desc.append(o)
        elif not o.get("ls_check"):
            douteux.append(o)
        else:
            pretes.append(o)
    cartes = [
        ("Offres", len(q)),
        ("Liens OK", len(ok)),
        ("Avec description", sum(1 for o in q if str(o.get("description") or "").strip())),
        ("Fit ≥ 8", len(top)),
        ("Dossiers préparés", len(pretes)),
        ("Postulé", st.count("postulé")),
        ("Relancé", st.count("relancé")),
        ("Entretien", st.count("entretien")),
        ("Refus", st.count("refus")),
        ("Pas intéressé", st.count("pas intéressé")),
    ]
    sections: list[dict[str, Any]] = []

    def section(titre: str, paires: list[tuple[str, Any]], base: int | None = None) -> None:
        if not paires:
            return
        total = len(q) if base is None else base
        sections.append(
            {
                "titre": titre,
                "lignes": [
                    {
                        "nom": str(nom),
                        "n": n,
                        "part": (n / total) if total and isinstance(n, int) else None,
                    }
                    for nom, n in paires
                ],
            }
        )

    def compte(cle: str, src: list[Any] | None = None) -> list[tuple[str, int]]:
        d: dict[str, int] = {}
        for o in src if src is not None else q:
            v = str(o.get(cle) or "—").strip() or "—"
            d[v] = d.get(v, 0) + 1
        return sorted(d.items(), key=lambda x: -x[1])

    section(
        "Sur les offres à fit ≥ 8",
        [
            ("dossiers préparés (envoi à vérifier)", len(pretes)),
            ("bloquées : CV ou lettre absent du disque", len(sans_doc)),
            ("bloquées : description trop courte", len(sans_desc)),
            ("bloquées : lien jamais vérifié", len(douteux)),
        ],
        base=len(top),
    )
    e = funnel.entonnoir(sv, {queue_io.oid(o): o for o in q})
    entonnoir = None
    if e["envoyees"]:
        entonnoir = {
            "envoyees": e["envoyees"],
            "reponses": e["reponses"],
            "taux": e["taux"],
            "entretiens": e["entretiens"],
            "silence": e["silence"],
            "delai_median": e["delai_median"],
            "n_delais": len(e["delais"]),
            "par": {
                champ: [
                    {"val": val, "env": env, "rep": rep, "ent": ent}
                    for val, env, rep, ent in [x for x in e["par"][champ] if x[1]][:6]
                ]
                for champ in ("contrat", "domaine")
            },
        }
    libelles = {d["cle"]: str(d.get("libelle") or d["cle"]) for d in profile.domaines()}
    par_domaine: dict[str, int] = {}
    for v, n in compte("domaine"):
        lib = libelles.get(v, v)
        par_domaine[lib] = par_domaine.get(lib, 0) + n
    section("Domaine", sorted(par_domaine.items(), key=lambda x: -x[1])[:8])
    section("Canal", compte("canal"))
    section("État des liens", compte("link_status"))
    fits = [(f"fit {i}", sum(1 for o in ok if (o.get("fit") or 0) == i)) for i in range(10, 0, -1)]
    section("Fit (offres vivantes)", [p for p in fits if p[1]], base=len(ok))
    tranches = {"100 %": 0, "80-99 %": 0, "60-79 %": 0, "40-59 %": 0, "< 40 %": 0, "non scoré": 0}
    for o in ok:
        a = o.get("ats_pct")
        cle = (
            "non scoré"
            if a is None
            else "100 %"
            if a >= 100
            else "80-99 %"
            if a >= 80
            else "60-79 %"
            if a >= 60
            else "40-59 %"
            if a >= 40
            else "< 40 %"
        )
        tranches[cle] += 1
    section("ATS % (offres vivantes)", [(k, v) for k, v in tranches.items() if v], base=len(ok))
    section("Sources (top 10)", [(s[:46], n) for s, n in compte("source")[:10]])
    return {
        "cartes": [{"nom": n, "n": v} for n, v in cartes],
        "sections": sections,
        "entonnoir": entonnoir,
    }


class PanneauxApi:
    """Mixed into `Api`: uses its `_file`, `_suivi`, `_tache` and `_demarrer`."""

    _file: Any
    _suivi: Any
    _tache: Any
    _demarrer: Any

    # --- Statistics ---------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        """The desktop's Stats panel, from the disk."""
        return statistiques(list(self._file()), dict(self._suivi()))

    # --- Access: collection sources and their keys, logins for applying ---------------
    def acces(self) -> dict[str, Any]:
        """Each source's access and last state; the keys' presence only, never their value."""
        from jobhunter import api_keys, inventory, root
        from jobhunter.programs import access
        from jobhunter.sources import quota
        from jobhunter.sources import source_yield as rendement

        donnees = root.scripts()
        journal = rendement.lire_journal(root.dans(donnees, "_rendement.jsonl"))
        fichiers = {c.fichier: c.nom for c in api_keys.CLES.values()}
        sources = [
            {
                "source": e.source,
                "libelle": e.libelle,
                "acces": e.acces,
                "etat": e.etat,
                "le": _date_fr(e.le),
                "gravite": e.gravite,
                "bloque": e.bloque,
                "cle": e.source in api_keys.CLES,
            }
            for e in inventory.etat_sources(
                journal, lambda f: api_keys.presente(root.dossier_cles(), fichiers[f])
            )
        ]
        quotas = []
        for nom, lib in (
            ("adzuna", "Adzuna"),
            ("jooble", "Jooble"),
            ("francetravail", "France Travail"),
        ):
            quotas.append({"nom": lib, "n": quota.usage(nom), "plafond": quota.plafond(nom)})
        try:
            comptes = json.loads(root.dans(donnees, "comptes.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            comptes = {}
        connexions = []
        for hote in access.SITES_CONNEXION:
            e = comptes.get(hote) or {}
            lib, grav = _session(e.get("session") or "?", e.get("session_verif"))
            connexions.append(
                {
                    "site": hote,
                    "identifiant": e.get("identifiant") or "",
                    "session": lib,
                    "gravite": grav,
                    "le": _date_fr(e.get("session_verif")),
                }
            )
        return {"sources": sources, "quotas": quotas, "connexions": connexions}

    def cle_champs(self, nom: str) -> dict[str, Any]:
        """The fields of a key's entry form, and whether one is saved; never a value."""
        from jobhunter import api_keys, root

        cle = api_keys.CLES.get(nom)
        if cle is None:
            return {"ok": False, "erreur": "accès libre, aucune clé à saisir."}
        return {
            "ok": True,
            "libelle": cle.libelle,
            "champs": [{"nom": c, "secret": c in cle.secrets} for c in cle.champs],
            "obtenir": cle.obtenir,
            "deja": api_keys.presente(root.dossier_cles(), nom),
        }

    def saisir_cle(self, nom: str, valeurs: dict[str, str]) -> dict[str, Any]:
        """Writes a key typed by the user into the file its source reads.

        The value goes from the form to the file only: it is not logged, not returned,
        and the page empties its fields. A field left empty keeps the stored value.
        """
        from jobhunter import api_keys, root

        if nom not in api_keys.CLES:
            return {"ok": False, "erreur": "source inconnue"}
        propres = {str(k): str(v or "").strip() for k, v in (valeurs or {}).items()}
        try:
            api_keys.enregistrer(root.dossier_cles(), nom, propres)
        except (KeyError, ValueError) as e:
            return {"ok": False, "erreur": str(e)}
        return {"ok": True}

    def tester_cle(self, nom: str) -> dict[str, Any]:
        """One minimal request with the saved key (sources.connexion); no offer imported."""
        from jobhunter import api_keys
        from jobhunter.sources import connexion

        if nom not in api_keys.CLES:
            return {"ok": False, "erreur": "accès libre, aucune clé à saisir."}
        try:
            r = connexion.tester(nom)
            etat, detail = r.etat, r.detail
        except Exception as e:  # noqa: BLE001 — never the message: it may hold a URL with the key
            etat, detail = "reseau", type(e).__name__
        texte = MESSAGES_TEST.get(etat, etat).format(nom=api_keys.CLES[nom].libelle)
        return {
            "ok": True,
            "reussi": etat == "ok",
            "message": texte + (f" ({detail})" if detail else ""),
        }

    def collecter_source(self, nom: str) -> dict[str, Any]:
        """Collects one source; a refused one is not tried again before 30 days (ADR 0004)."""
        from jobhunter import api_keys, inventory, root
        from jobhunter.sources import source_yield as rendement

        if nom not in inventory.DRAPEAUX_COLLECTE:
            return {"ok": False, "erreur": "source inconnue"}
        journal = rendement.lire_journal(root.dans(root.scripts(), "_rendement.jsonl"))
        fichiers = {c.fichier: c.nom for c in api_keys.CLES.values()}
        e = next(
            x
            for x in inventory.etat_sources(
                journal, lambda f: api_keys.presente(root.dossier_cles(), fichiers[f])
            )
            if x.source == nom
        )
        if e.bloque:
            return {"ok": False, "erreur": f"{e.libelle} : {e.etat}"}
        if nom in api_keys.CLES and not api_keys.presente(root.dossier_cles(), nom):
            return {"ok": False, "erreur": f"{e.libelle} : saisis d'abord sa clé."}
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        return self._demarrer(
            "source",
            f"Collecte {e.libelle}",
            ["jobhunter.sources", inventory.DRAPEAUX_COLLECTE[nom]],
        )

    def rendement_sources(self) -> dict[str, Any]:
        """The source_yield report, in the task panel."""
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        return self._demarrer(
            "rendement", "Rendement des sources", ["jobhunter.programs.source_yield"]
        )

    def connexion(self, site: str, verifier: bool = False) -> dict[str, Any]:
        """Opens a site's login page, or checks every session, in a console (programs.access).

        The user logs in himself; passwords stay in the browser's manager.
        """
        from jobhunter import root
        from jobhunter.programs import access

        if not verifier and site not in access.SITES_CONNEXION:
            return {"ok": False, "erreur": "site inconnu"}
        args = ["--check"] if verifier else ["--open", site]
        subprocess.Popen(  # nosec B603 : our own program, arguments from a fixed list
            [sys.executable, "-m", "jobhunter.programs.access", *args],
            cwd=str(root.scripts()),
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10),
        )
        return {"ok": True}

    # --- Companies: the feeds collected and the offers they bring ---------------------
    def _cfg_sources(self) -> tuple[Path, dict[str, Any]]:
        from jobhunter import root

        f = root.scripts() / "sources_config.json"
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            c = {}
        return f, c if isinstance(c, dict) else {}

    def _sites(self) -> tuple[Path, list[str]]:
        from jobhunter import root

        f = root.scripts() / "unique_domains.txt"
        try:
            lignes = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            lignes = []
        return f, [x.split("|", 1)[-1].strip() for x in lignes if x.strip()]

    @staticmethod
    def _defauts() -> dict[str, Any]:
        from jobhunter.sources import common as src

        return {
            "ats_slugs": {k: list(v) for k, v in src.ATS_SLUGS.items()},
            "workday_flux": [list(x) for x in src.WORKDAY_FLUX],
            "autres_flux": [list(x) for x in src.AUTRES_FLUX],
        }

    def _flux(self) -> list[Any]:
        from jobhunter import inventory
        from jobhunter.sources import common as src

        src._load_cfg()
        _, urls = self._sites()
        return inventory.flux_suivis(
            src.ATS_SLUGS, src.WORKDAY_FLUX, src.AUTRES_FLUX, [u for u in urls if not _est_board(u)]
        )

    def entreprises(self) -> dict[str, Any]:
        """One row per followed company: read by, last collection, offers, best fit."""
        from jobhunter import inventory, root
        from jobhunter.sources import feeds

        etat = feeds.lire(root.scripts() / feeds.FICHIER)
        suspendus = feeds.suspendus()
        flux = self._flux()
        comptes = inventory.compter(self._file(), flux)

        def collecte(f: Any) -> str:
            if f.outil == "site":
                return "—"
            ident = feeds.cle(f.outil, f.cle)
            if ident in suspendus:
                return "suspendue"
            e = etat.get(ident) or {}
            if m := feeds.muet(e):
                return f"muette : {m}"
            if e.get("incident"):
                return f"{e['incident']} ({_date_fr(str(e.get('incident_le', ''))[:10])})"
            if e.get("succes"):
                return f"ok {_date_fr(str(e['succes'])[:10])} · {e.get('offres', 0)}"
            return "—"

        lignes = [
            {
                "id": f"{f.outil}|{f.cle}",
                "nom": f.nom,
                "outil": inventory.NOMS_OUTILS.get(f.outil, f.outil),
                "collecte": collecte(f),
                "offres": comptes[f].offres,
                "fit": comptes[f].meilleur_fit if comptes[f].offres else None,
                "derniere": _date_fr(comptes[f].derniere),
                "lien": f.lien,
                "suspendue": f.outil != "site" and feeds.cle(f.outil, f.cle) in suspendus,
                "site": f.outil == "site",
            }
            for f in sorted(flux, key=lambda f: (-comptes[f].offres, f.nom.lower()))
        ]
        return {
            "lignes": lignes,
            "muettes": len(feeds.muets(etat, suspendus)),
            "muet_jours": feeds.MUET_JOURS,
        }

    def suivre_entreprise(self, texte: str) -> dict[str, Any]:
        """Follows a company by its career page URL.

        An ATS read by API becomes a feed, another site is read by the browser; a
        general board belongs to the job boards instead.
        """
        from jobhunter import inventory

        v = str(texte or "").strip()
        if not v.startswith("http"):
            return {"ok": False, "erreur": "une adresse http, ou cherche le nom dans l'annuaire"}
        if _est_board(v):
            return {
                "ok": False,
                "erreur": "c'est un site d'offres général : ajoute-le dans « Sites d'offres »",
            }
        trouve = inventory.flux_depuis_url(v)
        if trouve:
            f, c = self._cfg_sources()
            msg = inventory.ajouter_flux(c, self._defauts(), trouve)
            _ecrire_json(f, c)
            return {"ok": True, "message": msg}
        f, urls = self._sites()
        if v in urls:
            return {"ok": False, "erreur": "déjà suivi"}
        f.write_text(("\n".join([*urls, v])).strip() + "\n", encoding="utf-8")
        return {"ok": True, "message": f"site carrière ajouté, lu par le navigateur : {v}"}

    def annuaire(self, texte: str) -> list[dict[str, Any]]:
        """Companies of the Lever, Ashby and Greenhouse directories matching a name."""
        from jobhunter import inventory
        from jobhunter.sources import common as src
        from jobhunter.sources import directory

        src._load_cfg()
        suivis = {(o, str(s).lower()) for o, slugs in src.ATS_SLUGS.items() for s in slugs}
        return [
            {
                "nom": e.nom,
                "outil": e.outil,
                "outil_nom": inventory.NOMS_OUTILS.get(e.outil, e.outil),
                "jeton": e.jeton,
                "suivi": (e.outil, str(e.jeton).lower()) in suivis,
            }
            for e in directory.chercher(str(texte or ""), limite=50)
        ]

    def suivre_annuaire(self, outil: str, jeton: str) -> dict[str, Any]:
        """Follows a company found in the directory (its ATS feed)."""
        from jobhunter import inventory
        from jobhunter.sources import directory

        if outil not in directory.OUTILS or not re.fullmatch(r"[\w.-]+", str(jeton or "")):
            return {"ok": False, "erreur": "entrée d'annuaire invalide"}
        f, c = self._cfg_sources()
        msg = inventory.ajouter_flux(c, self._defauts(), (outil, jeton))
        _ecrire_json(f, c)
        return {"ok": True, "message": msg}

    def _trouver_flux(self, ident: str) -> Any:
        return next((f for f in self._flux() if f"{f.outil}|{f.cle}" == ident), None)

    def retirer_entreprise(self, ident: str) -> dict[str, Any]:
        """Stops following a company: its feed address is removed (the page asks first)."""
        from jobhunter import inventory

        fl = self._trouver_flux(ident)
        if fl is None:
            return {"ok": False, "erreur": "entreprise introuvable"}
        if fl.outil == "site":
            f, urls = self._sites()
            f.write_text("\n".join(u for u in urls if u != fl.cle).strip() + "\n", encoding="utf-8")
        else:
            f, c = self._cfg_sources()
            if not inventory.retirer_flux(c, self._defauts(), fl):
                return {
                    "ok": False,
                    "erreur": f"{fl.nom} : flux introuvable dans sources_config.json",
                }
            _ecrire_json(f, c)
        return {"ok": True, "message": f"{fl.nom} ne sera plus collectée"}

    def suspendre_entreprise(self, ident: str) -> dict[str, Any]:
        """Stops or resumes a company's collections; its offers and history stay."""
        from jobhunter.sources import feeds

        fl = self._trouver_flux(ident)
        if fl is None:
            return {"ok": False, "erreur": "entreprise introuvable"}
        if fl.outil == "site":
            return {
                "ok": False,
                "erreur": "Un site lu par le navigateur ne se suspend pas : retire-le.",
            }
        f, c = self._cfg_sources()
        cle = feeds.cle(fl.outil, fl.cle)
        oui = cle not in feeds.suspendus(c)
        feeds.suspendre(c, cle, oui)
        _ecrire_json(f, c)
        return {
            "ok": True,
            "suspendue": oui,
            "message": f"{fl.nom} {'suspendue' if oui else 'reprise'}",
        }

    # --- Job boards and ATS slugs (the desktop's "Sites d'offres") ---------------------
    def sites_offres(self) -> dict[str, Any]:
        """ATS slugs and general boards, with the offers each brought."""
        _, c = self._cfg_sources()
        offres = list(self._file())
        sources = [str(o.get("source") or "").lower() for o in offres]
        lignes = []
        for genre, slugs in (c.get("ats_slugs") or {}).items():
            for s in slugs:
                cle = f"{genre}:{s}".lower()
                lignes.append(
                    {
                        "type": genre,
                        "source": s,
                        "offres": sum(1 for x in sources if cle in x),
                        "lien": ATS_URL.get(genre, "{s}").format(s=s),
                    }
                )
        _, urls = self._sites()
        for u in urls:
            if _est_board(u):
                hote = urlparse(u).netloc.replace("www.", "")
                n = sum(1 for o in offres if hote and hote in (o.get("url") or ""))
                lignes.append({"type": "board", "source": hote, "offres": n, "lien": u})
        return {"lignes": lignes, "types": ["board", *ATS_URL]}

    def ajouter_site_offres(self, genre: str, valeur: str) -> dict[str, Any]:
        """Adds an ATS slug (API) or a job board (read by "Scrape les sites")."""
        v = str(valeur or "").strip()
        if not v:
            return {"ok": False, "erreur": "valeur vide"}
        if genre == "board":
            if not v.startswith("http"):
                return {"ok": False, "erreur": "un site d'offres : adresse http"}
            f, urls = self._sites()
            if v in urls:
                return {"ok": False, "erreur": "déjà présent"}
            f.write_text(("\n".join([*urls, v])).strip() + "\n", encoding="utf-8")
            return {"ok": True}
        if genre not in ATS_URL:
            return {"ok": False, "erreur": f"type inconnu : {genre}"}
        f, c = self._cfg_sources()
        slugs = c.setdefault("ats_slugs", {}).setdefault(genre, [])
        if v not in slugs:
            slugs.append(v)
        _ecrire_json(f, c)
        return {"ok": True}

    def retirer_site_offres(self, genre: str, valeur: str) -> dict[str, Any]:
        """Removes an ATS slug or a job board (the page asks first)."""
        if genre == "board":
            f, urls = self._sites()
            f.write_text("\n".join(u for u in urls if u != valeur).strip() + "\n", encoding="utf-8")
            return {"ok": True}
        f, c = self._cfg_sources()
        slugs = (c.get("ats_slugs") or {}).get(genre) or []
        if valeur in slugs:
            slugs.remove(valeur)
            _ecrire_json(f, c)
        return {"ok": True}

    def ouvrir_lien(self, url: str) -> bool:
        """Opens a feed's or a board's page."""
        if not re.match(r"^https?://", str(url or "")):
            return False
        return webbrowser.open(url)
