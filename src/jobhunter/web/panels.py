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
import webbrowser
from collections.abc import Mapping
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


# Collection tools named as the user knows them (« sfrss » is SAP SuccessFactors).
_SITES = {
    "linkedin": "LinkedIn",
    "workday": "Workday",
    "sfrss": "SuccessFactors",
    "glassdoor": "Glassdoor",
    "apec": "APEC",
    "adzuna": "Adzuna",
    "jooble": "Jooble",
    "freehire": "freehire",
    "arbeitsagentur": "Arbeitsagentur",
    "vie": "Business France (V.I.E)",
    "oracle": "Oracle",
    "francetravail": "France Travail",
    "efc": "eFinancialCareers",
    "eures": "EURES",
    "wtj": "Welcome to the Jungle",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "smartrecruiters": "SmartRecruiters",
}


def statistiques(
    q: list[Any], sv: Any, descriptions: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """The Statistics screen: cards, the sent applications, then sections of (label, n, share).

    `descriptions` (oid → text) is the queue's texts, kept in their own file: the
    queue read for this screen has none, and every prepared offer counted as
    "description too short" (2026-10-27). Without it, the description is not checked.
    Sections that told nothing (channel, link state, ATS score) were removed then.
    """
    from jobhunter import funnel, profile
    from jobhunter.links import existe
    from jobhunter.storage import queue as queue_io

    ok = [o for o in q if str(o.get("link_status") or "").upper() not in ("MORT", "EXPIREE")]

    def fichier(u: Any) -> bool:
        try:
            return bool(u) and bool(existe(u))
        except Exception:  # noqa: BLE001 — an unreadable path counts as absent
            return False

    def description(o: Any) -> str:
        if descriptions is None:
            return str(o.get("description") or "x" * 200)
        return str(descriptions.get(queue_io.oid(o)) or o.get("description") or "")

    top = [o for o in ok if (o.get("fit") or 0) >= 8]
    pretes, sans_doc, sans_desc, douteux = [], [], [], []
    for o in top:
        if not (fichier(o.get("cv")) and fichier(o.get("lettre"))):
            sans_doc.append(o)
        elif len(description(o)) < 200:
            sans_desc.append(o)
        elif not o.get("ls_check"):
            douteux.append(o)
        else:
            pretes.append(o)
    e = funnel.entonnoir(sv, {queue_io.oid(o): o for o in q})
    cartes = [
        ("Offres en ligne", len(ok)),
        ("Fit ≥ 8", len(top)),
        ("Dossiers prêts", len(pretes)),
        ("Candidatures envoyées", e["envoyees"]),
        ("Réponses", e["reponses"]),
        ("Entretiens", e["entretiens"]),
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
            ("dossiers prêts (CV, lettre, lien vérifié)", len(pretes)),
            ("sans CV ou lettre", len(sans_doc)),
            ("description trop courte", len(sans_desc)),
            ("lien jamais vérifié", len(douteux)),
        ],
        base=len(top),
    )
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
    fits = [(f"fit {i}", sum(1 for o in ok if (o.get("fit") or 0) == i)) for i in range(10, 0, -1)]
    section("Fit des offres en ligne", [p for p in fits if p[1]], base=len(ok))
    libelles = {d["cle"]: str(d.get("libelle") or d["cle"]) for d in profile.domaines()}
    par_domaine: dict[str, int] = {}
    for v, n in compte("domaine", ok):
        lib = libelles.get(v, v)
        par_domaine[lib] = par_domaine.get(lib, 0) + n
    section("Domaine", sorted(par_domaine.items(), key=lambda x: -x[1])[:8], base=len(ok))
    # « linkedin-search:analyste isr » → the site, then the collection keyword.
    sites: dict[str, int] = {}
    mots: dict[str, int] = {}
    for s, n in compte("source", ok):
        site, _, mot = s.partition(":")
        site = _SITES.get(site.removesuffix("-search"), site.removesuffix("-search"))
        sites[site] = sites.get(site, 0) + n
        if mot:
            mots[mot] = mots.get(mot, 0) + n
    section(
        "Sites d'où viennent les offres",
        sorted(sites.items(), key=lambda x: -x[1])[:8],
        base=len(ok),
    )
    section(
        "Mots-clés qui rapportent le plus",
        [(m[:46], n) for m, n in sorted(mots.items(), key=lambda x: -x[1])[:8]],
        base=len(ok),
    )
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
    _descriptions: Any

    # --- Statistics ---------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        """The desktop's Stats panel, from the disk."""
        return statistiques(list(self._file()), dict(self._suivi()), self._descriptions())

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
        from jobhunter import frozen, root
        from jobhunter.programs import access

        if not verifier and site not in access.SITES_CONNEXION:
            return {"ok": False, "erreur": "site inconnu"}
        args = ["--check"] if verifier else ["--open", site]
        subprocess.Popen(  # nosec B603 : our own program, arguments from a fixed list
            [frozen.interpreteur(), "-m", "jobhunter.programs.access", *args],
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

    def entreprises_vues(self) -> dict[str, Any]:
        """Every company a collection has seen (storage.companies), with its offers now.

        `suivie`: already followed, by name or by its feed. `flux`: the feed its offer
        links give, to follow it in one click.
        """
        from jobhunter import inventory
        from jobhunter.sources import common
        from jobhunter.storage import companies

        q = self._file()
        reg = companies.charger(common.QUEUE)
        if not reg and q:  # register not written yet: the queue's companies, unsaved
            reg = {}
            for o in q:
                k = companies.cle(o.get("entreprise"))
                if k:
                    e = reg.setdefault(k, {"nom": str(o["entreprise"]).strip(), "sites": []})
                    s = companies.site(o.get("source"))
                    if s and s not in e["sites"]:
                        e["sites"].append(s)
        par: dict[str, list[int]] = {}
        for o in q:
            par.setdefault(companies.cle(o.get("entreprise")), []).append(int(o.get("fit") or 0))
        suivis = self._flux()
        noms = {companies.cle(f.nom) for f in suivis}
        flux_suivis = {(f.outil, str(f.cle).lower()) for f in suivis}
        lignes: list[dict[str, Any]] = []
        for k, e in reg.items():
            fl = e.get("flux") or None
            ident = None
            if fl:
                c = fl["cle"]  # Workday: [tenant, host, site], followed by its tenant
                ident = (fl["outil"], str(c[0] if isinstance(c, list) else c).lower())
            fits = par.get(k, [])
            lignes.append(
                {
                    "nom": e.get("nom") or k,
                    "offres": len(fits),
                    "fit": max(fits) if fits else None,
                    "sites": [_SITES.get(s, s) for s in e.get("sites", [])],
                    "premiere": _date_fr(str(e.get("premiere_vue") or "")),
                    "derniere": _date_fr(str(e.get("derniere_vue") or "")),
                    "tri": str(e.get("derniere_vue") or ""),
                    "outil": inventory.NOMS_OUTILS.get(fl["outil"], fl["outil"]) if fl else None,
                    "url_flux": fl["url"] if fl else None,
                    "suivie": k in noms or (ident in flux_suivis),
                }
            )
        lignes.sort(key=lambda x: (-x["offres"], -(x["fit"] or 0), x["nom"].lower()))
        return {"lignes": lignes}

    def suivre_vues(self, fit_min: int = 7, maxi: int = 25) -> dict[str, Any]:
        """Follows the well-rated companies seen, whose feed answers with open offers.

        One request per company to its tool's public API (sources.discovery): a feed
        that gives nothing is not followed. At most `maxi` checks per click.
        """
        from jobhunter import inventory
        from jobhunter.sources import discovery

        a_voir = [
            x
            for x in self.entreprises_vues()["lignes"]
            if x["url_flux"] and not x["suivie"] and (x["fit"] or 0) >= int(fit_min)
        ]
        f, c = self._cfg_sources()
        suivies, vides = [], []
        for x in a_voir[:maxi]:
            trouve = inventory.flux_depuis_url(x["url_flux"])
            if not trouve:
                continue
            n = discovery.offres_ouvertes(trouve)
            if n == 0:
                vides.append(x["nom"])
                continue
            inventory.ajouter_flux(c, self._defauts(), trouve)
            suivies.append(x["nom"])
        if suivies:
            _ecrire_json(f, c)
        reste = max(0, len(a_voir) - maxi)
        return {
            "ok": True,
            "suivies": suivies,
            "vides": vides,
            "message": f"{len(suivies)} entreprise(s) suivie(s), {len(vides)} sans offre ouverte"
            + (f", {reste} à vérifier au prochain clic" if reste else ""),
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
        """Companies of the directories (Lever, Ashby, Greenhouse; Workday if built) matching a name."""
        from jobhunter import inventory
        from jobhunter.sources import common as src
        from jobhunter.sources import directory

        src._load_cfg()
        suivis = {(o, str(s).lower()) for o, slugs in src.ATS_SLUGS.items() for s in slugs}
        suivis |= {("workday", f"{x[0]}.{x[1]}/{x[2]}".lower()) for x in src.WORKDAY_FLUX}
        suivis |= {(str(x[0]), str(x[1]).lower()) for x in src.AUTRES_FLUX}
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

        trouve: tuple[str, Any]
        if outil == "workday" and directory.workday_de_jeton(jeton):
            from jobhunter.sources import discovery

            trouve = ("workday", directory.workday_de_jeton(jeton))
            if discovery.offres_ouvertes(trouve) == 0:
                return {"ok": False, "erreur": "ce site Workday n'a aucune offre ouverte"}
        elif outil in directory.SUIVABLES and re.fullmatch(r"[\w.-]+", str(jeton or "")):
            trouve = (outil, jeton)
        else:
            return {"ok": False, "erreur": "entrée d'annuaire invalide"}
        f, c = self._cfg_sources()
        msg = inventory.ajouter_flux(c, self._defauts(), trouve)
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
                from jobhunter.sources import company_lists

                if ids := company_lists.origine(c, fl.outil, fl.cle):
                    titres = ", ".join(
                        f"« {x.titre} »" for i in ids if (x := company_lists.par_ident(i))
                    )
                    return {
                        "ok": False,
                        "erreur": f"{fl.nom} vient de la liste {titres} : décoche-la dans la "
                        "liste, ou suspends-la.",
                    }
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

    # --- Company lists by sector (sources.company_lists) -------------------------------
    def listes_entreprises(self) -> list[dict[str, Any]]:
        """Each sector's list: ticked or not, and its companies, unticked when suspended."""
        from jobhunter.sources import company_lists, feeds

        _, c = self._cfg_sources()
        suspendus = feeds.suspendus(c)
        listes = company_lists.resume(c)
        for liste in listes:
            for e in liste["entreprises"]:
                e["suivie"] = feeds.cle(e["outil"], e["cle"]) not in suspendus
        return listes

    def activer_liste(self, ident: str, oui: bool) -> dict[str, Any]:
        """Ticks or unticks a whole list: its companies join or leave the collection."""
        from jobhunter.sources import company_lists

        liste = company_lists.par_ident(str(ident or ""))
        if liste is None:
            return {"ok": False, "erreur": "liste inconnue"}
        f, c = self._cfg_sources()
        company_lists.activer(c, liste.ident, bool(oui))
        _ecrire_json(f, c)
        etat = "collectée dès la prochaine collecte" if oui else "n'est plus collectée"
        return {"ok": True, "message": f"« {liste.titre} » {etat}"}

    def suivre_dans_liste(self, outil: str, cle: str, oui: bool) -> dict[str, Any]:
        """Ticks or unticks one company of a list (suspends its feed; offers stay)."""
        from jobhunter.sources import feeds

        if not re.fullmatch(r"[\w.|-]+", str(outil or "")) or not re.fullmatch(
            r"[\w.|-]+", str(cle or "")
        ):
            return {"ok": False, "erreur": "entreprise invalide"}
        f, c = self._cfg_sources()
        feeds.suspendre(c, feeds.cle(outil, cle), not oui)
        _ecrire_json(f, c)
        return {"ok": True}

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
