#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_sources.py — Arbitrage des doublons entre sources (job_sources).

Une meme annonce paraît souvent sur LinkedIn ET sur un vrai site d'emploi.
LinkedIn est le pire des deux : mur de connexion, description illisible sans
compte, et postuler y renvoie de toute facon vers la source. La premiere source
vue gagnait, au hasard de l'ordre des scans.

Run : python test_sources.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import job_sources as J
# Les fusions de test ne doivent pas lire les rejets reels du tri (rejets_tri.py).
import tempfile as _tf
J.REJETS_TRI = __import__('pathlib').Path(_tf.mkdtemp()) / 'rejets.json'
from job_sources import rang_source

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


print("\n── A. classement des sources ──")
for url, att, quoi in [
    ("https://fr.linkedin.com/jobs/view/consultant-esg-at-oderis-4", 0, "LinkedIn"),
    ("https://www.linkedin.com/jobs/view/123", 0, "LinkedIn (www)"),
    ("https://fr.indeed.com/viewjob?jk=abc", 1, "Indeed"),
    ("https://fr.talent.com/view?id=x", 1, "Talent"),
    ("https://www.welcometothejungle.com/fr/companies/oderis/jobs/x", 2, "WTJ"),
    ("https://www.apec.fr/candidat/emploi/1234", 2, "APEC"),
    ("https://mon-vie-via.businessfrance.fr/offres/123", 2, "Business France"),
    ("https://boards.greenhouse.io/sweep/jobs/123", 3, "Greenhouse"),
    ("https://jobs.lever.co/greenly/abc", 3, "Lever"),
    ("https://careers.axa.com/careers-home/jobs/2446", 3, "site entreprise"),
]:
    check(f"{quoi} → {att}", rang_source(url), att)
check("URL vide → -1", rang_source(""), -1)
check("URL None → -1", rang_source(None), -1)

print("\n── B. ordre : entreprise > site emploi > agrégateur > LinkedIn ──")
li = "https://fr.linkedin.com/jobs/view/x-4"
wtj = "https://www.welcometothejungle.com/fr/companies/o/jobs/x"
ind = "https://fr.indeed.com/viewjob?jk=x"
ats = "https://boards.greenhouse.io/o/jobs/1"
check("WTJ bat LinkedIn", rang_source(wtj) > rang_source(li), True)
check("Indeed bat LinkedIn", rang_source(ind) > rang_source(li), True)
check("WTJ bat Indeed", rang_source(wtj) > rang_source(ind), True)
check("ATS bat WTJ", rang_source(ats) > rang_source(wtj), True)

print("\n── C. promotion réelle dans merge_into_queue ──")
# queue jetable : on ne touche pas apply_queue.json
tmp = Path(tempfile.mkdtemp()) / "q.json"
depart = [{
    "entreprise": "Oderis Consulting", "poste": "Consultant(e) Junior ESG",
    "domaine": "ESG_Finance_Durable", "statut": "Scan 2026-09-03", "url": li,
    "canal": "manuel", "site_kind": "board", "fit": 8, "description": "",
}]
tmp.write_text(json.dumps(depart, ensure_ascii=False), encoding="utf-8")
_vrai = J.QUEUE
J.QUEUE = tmp
try:
    entrant = [J._mk("Consultant(e) Junior ESG", wtj, "Oderis Consulting",
                     source="welcometothejungle.com")]
    r = J.merge_into_queue(entrant, dry=False)
    apres = json.loads(tmp.read_text(encoding="utf-8"))
    check("aucun doublon ajouté", len(apres), 1)
    check("1 lien promu", r["promus"], 1)
    check("l'URL est celle de WTJ", apres[0]["url"], wtj)
    check("canal repassé en manuel (board)", apres[0]["canal"], "manuel")

    # sens inverse : LinkedIn ne doit JAMAIS ecraser une meilleure source
    r2 = J.merge_into_queue([J._mk("Consultant(e) Junior ESG", li, "Oderis Consulting")],
                            dry=False)
    apres2 = json.loads(tmp.read_text(encoding="utf-8"))
    check("LinkedIn ne rétrograde pas le lien", apres2[0]["url"], wtj)
    check("aucune promotion à contresens", r2["promus"], 0)

    # un ATS doit encore battre WTJ
    r3 = J.merge_into_queue([J._mk("Consultant(e) Junior ESG", ats, "Oderis Consulting")],
                            dry=False)
    apres3 = json.loads(tmp.read_text(encoding="utf-8"))
    check("l'ATS promeut par-dessus WTJ", apres3[0]["url"], ats)
    check("canal repassé en auto (entreprise)", apres3[0]["canal"], "auto")
finally:
    J.QUEUE = _vrai

print("\n── C bis. enrichissement DANS LE MÊME lot ──")
# Le cas normal : `--all` enchaîne ATS, LinkedIn, WTJ, eFC et Indeed. La même
# annonce arrive donc plusieurs fois dans UN SEUL appel, l'offre étant ajoutée
# par la première source puis améliorée par les suivantes.
# `idx[key] = o` rangeait le dict du SCAN, alors que la file recevait un dict
# different : promotion d'URL et description s'ecrivaient sur l'orphelin. Les
# compteurs annoncaient le travail, la file n'en gardait rien.
tmp2 = Path(tempfile.mkdtemp()) / "q.json"
tmp2.write_text("[]", encoding="utf-8")
_vrai = J.QUEUE
J.QUEUE = tmp2
try:
    lot = [
        J._mk("Analyste ESG", li, "Amundi", "Paris, France", source="linkedin-search"),
        J._mk("Analyste ESG", ats, "Amundi", "Paris, France", source="greenhouse:amundi",
              description="Analyse extra-financière, SFDR, taxonomie. Bac+5 finance durable."),
    ]
    r4 = J.merge_into_queue(lot, dry=False)
    apres4 = json.loads(tmp2.read_text(encoding="utf-8"))
    check("une seule ligne créée", len(apres4), 1)
    check("le lien ATS a bien remplacé LinkedIn", apres4[0]["url"], ats)
    check("la description est DANS la file", bool(apres4[0].get("description", "").strip()), True)
    check("promotion comptée une fois", r4["promus"], 1)

    # L'ordre inverse ne doit rien degrader : la bonne source arrive d'abord.
    tmp2.write_text("[]", encoding="utf-8")
    r5 = J.merge_into_queue(list(reversed(lot)), dry=False)
    apres5 = json.loads(tmp2.read_text(encoding="utf-8"))
    check("ordre inverse : le lien ATS tient", apres5[0]["url"], ats)
    check("ordre inverse : aucune rétrogradation", r5["promus"], 0)
finally:
    J.QUEUE = _vrai

print("\n── C ter. les deux listes de mots-clés ne divergent pas ──")
# title_ok = lexique LARGE (scrape_jobs.ESG_FINANCE_KEYWORDS) ET mot MÉTIER
# (_DOMAIN_RX). Un mot présent dans l'un et absent de l'autre fait jeter
# l'offre en silence. « CSRD » était dans _DOMAIN_RX et dans les mots-clés de
# RECHERCHE, mais pas dans le lexique : on demandait ces offres à LinkedIn
# avant de les jeter à l'arrivée.
from scrape_jobs import matches_esg_finance, offre_retenue
for mot in ["esg", "csr", "csrd", "sfdr", "taxonomie", "hse", "qhse", "e&s",
            "extra-financier", "rse", "biodiversit", "impact", "transition",
            "environnement", "environmental", "durabilit", "decarbonation",
            "climat", "carbon", "green", "quant", "risk", "risque", "credit",
            "invest", "audit", "actuari", "treasury", "tresorerie", "m&a",
            "portfolio", "asset", "analyste", "analytic", "consultant",
            "conseil", "economiste", "comptab", "controlling"]:
    check(f"« {mot} » passe le lexique large", matches_esg_finance(mot), True)

print("\n── C quater. le filtre d'entrée de scrape_jobs ──")
# « h/f » est dans le lexique large, et presque toute annonce française le
# porte : matches_esg_finance seul acceptait boucher, plombier et serveur.
for titre in ["Plombier chauffagiste H/F", "Serveur en restauration H/F",
              "Chef de rayon boucherie H/F", "Assistant RH (H/F)",
              "Commercial sédentaire H/F", "Backend Developer H/F",
              "Talent Acquisition Manager", "Designer UX Senior"]:
    check(f"refusé : {titre}", offre_retenue(titre), False)
for titre in ["Analyste ESG junior H/F", "Sustainable Finance Analyst",
              "CSRD Reporting Manager", "Graduate Programme Finance",
              "Contrôleur de gestion H/F", "Chargé de mission environnement",
              "VIE Transition Énergétique Corporate", "AI Software Engineer"]:
    check(f"retenu  : {titre}", offre_retenue(titre), True)

print("\n── C quinquies. le garde-fou \\b couvre TOUS les motifs ──")
# Il ne regardait que le préfixe `_RX_` et laissait passer _DOMAIN_RX,
# _HARD_NEG_RX, _AI_RX… soit exactement les motifs de title_ok.
import re as _re
_motifs = [n for n, v in vars(J).items() if isinstance(v, _re.Pattern)]
check("au moins 25 motifs compilés", len(_motifs) >= 25, True)
for _nom in ("_DOMAIN_RX", "_HARD_NEG_RX", "_AI_RX", "_NEG_TITLE_RX", "_RX_ALT"):
    _avant = getattr(J, _nom)
    for _corrompu, _quoi in ((_re.compile("(\x08ia\x08)"), "backspace"),
                             (_re.compile("(" + chr(92) * 2 + "bia)"), "antislash")):
        setattr(J, _nom, _corrompu)
        try:
            J._verifier_motifs()
            _vu = False
        except AssertionError:
            _vu = True
        finally:
            setattr(J, _nom, _avant)
        check(f"{_nom} : {_quoi} détecté", _vu, True)
J._verifier_motifs()   # l'état réel du module doit rester sain

print("\n── D. par défaut, le monde entier entre ──")
from job_sources import en_france
# l'utilisateur a tranché : les offres hors de France sont voulues. `MONDE` vaut donc
# True par défaut, et `en_france` laisse tout passer — le filtre ne sert plus
# qu'à `--france`.
check("MONDE actif par défaut", J.MONDE, True)
for lieu in ["Singapore, Singapore", "Dublin, Leinster, Ireland", "London",
             "Luxembourg", "Bruxelles", "Zurich"]:
    check(f"{lieu} entre", en_france(lieu), True)

print("\n── E. avec --france, le filtre trie toujours juste ──")
# Le mécanisme doit rester correct : il sert dès que `--france` est demandé.
# Un flux ATS porte le nom de la société, pas son pays — greenhouse/forvismazars
# est l'entité allemande, greenhouse/metron la société de défense américaine
# (Reston VA, « Military Analyst »). Seul le LIEU tranche.
_monde = J.MONDE
J.MONDE = False
try:
    for lieu in ["Paris", "Bordeaux", "", "Remote", "All France (remote)", "fr",
                 "PARIS 08, Île-de-France, France", "Strasbourg", "33", "Sud-Ouest"]:
        check(f"{lieu or '(vide)'} → France", en_france(lieu), True)
    for lieu in ["Berlin", "Dublin, Leinster, Ireland", "Hanoi", "Tokyo, JP", "London",
                 "Frankfurt am Main, Hessen, Deutschland", "de", "Casablanca"]:
        check(f"{lieu} → ailleurs", en_france(lieu), False)
    # Ces quatre-là passaient à tort : aucun code d'État américain n'était listé,
    # et un lieu non reconnu était accepté par défaut.
    for lieu in ["Reston, VA", "Aurora, CO", "Crane, IN", "Mexico City"]:
        check(f"{lieu} → ailleurs", en_france(lieu), False)
finally:
    J.MONDE = _monde
check("le mode mondial est bien rétabli après le test", J.MONDE, True)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
# sys.exit au niveau module TERMINE l'interpreteur de qui importe ce
# fichier. Sous garde, il ne s'applique qu'a une execution directe.
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
