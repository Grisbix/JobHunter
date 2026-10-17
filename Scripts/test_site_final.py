#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_site_final.py — site_final : intitules, identite Workday, resondage.

Sans reseau : les appels Workday et ATS sont remplaces par des doublures.

Run : python test_site_final.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import site_final as S

ok = ko = 0


def verifie(nom, obtenu, attendu):
    global ok, ko
    if obtenu == attendu:
        ok += 1
    else:
        ko += 1
        print(f"❌ {nom} → {obtenu!r}, attendu {attendu!r}")


# Intitules : memes mots, l'ordre et les mentions de genre/contrat varient.
verifie("genre", S.meme_titre("Analyste ESG (H/F)", "Analyste ESG"), True)
verifie("ordre", S.meme_titre("ESG Analyst", "Analyst ESG"), True)
verifie("junior", S.meme_titre("Junior Energy Consultant", "Energy Consultant"), False)
verifie("vide", S.meme_titre("(H/F)", "(H/F)"), False)

# Mots du nom dont le tenant est fait.
verifie("tenant 1 mot", S.mots_du_tenant("Accenture in India", "accenture"), ["accenture"])
verifie("tenant 2 mots", S.mots_du_tenant("Lombard Odier", "lombardodier"), ["lombard", "odier"])
verifie("tenant tiret", S.mots_du_tenant("Lombard Odier", "lombard-odier"), ["lombard", "odier"])
verifie("tenant etranger", S.mots_du_tenant("ERM", "accenture"), [])

# Identite : la vitrine doit nommer l'entreprise en mots entiers.
verifie("ERM nomme", S.meme_employeur("ERM", "erm", "at erm, sustainability is"), True)
verifie("ERM dans term", S.meme_employeur("ERM", "erm", "long term growth"), False)
verifie("deux mots", S.meme_employeur("Lombard Odier", "lombardodier", "about lombard odier"), True)
verifie(
    "deux mots colles",
    S.meme_employeur("Lombard Odier", "lombardodier", "lombardodier group"),
    False,
)
verifie(
    "entite juridique",
    S.meme_employeur("Accenture", "accenture", "8140 asol - gurugram non stpi company"),
    False,
)

# Quand resonder : un flux trouve ne se resonde pas, une absence apres 30 jours.
J = datetime.date(2026, 10, 7)
verifie("jamais vu", S.a_resonder(None, J), (True, True))
verifie(
    "ATS trouve, Workday jamais",
    S.a_resonder({"date": "2026-10-05", "flux": [["lever", "x"]]}, J),
    (False, True),
)
verifie(
    "rien, recent",
    S.a_resonder({"date": "2026-10-05", "flux": [], "wd_date": "2026-10-05"}, J),
    (False, False),
)
verifie(
    "rien, perime",
    S.a_resonder({"date": "2026-09-01", "flux": [], "wd_date": "2026-09-01"}, J),
    (True, True),
)
verifie(
    "Workday trouve",
    S.a_resonder(
        {"date": "2026-09-01", "flux": [["workday", "a.wd3/b"]], "wd_date": "2026-09-01"}, J
    ),
    (True, False),
)
verifie("date illisible", S.a_resonder({"date": "?", "flux": []}, J), (True, True))

# sonder : garde ce qui est trouve, ne resonde que ce qui est du.
appels = []
S.flux_de = lambda e, c: appels.append(("ats", e)) or [["greenhouse", "g"]]
S.flux_workday = lambda e: appels.append(("wd", e)) or [["workday", "t.wd3/Site"]]
x = S.sonder("A", None, [], J)
verifie(
    "sonder neuf",
    (x["flux"], x["date"], x["wd_date"], len(appels)),
    ([["greenhouse", "g"], ["workday", "t.wd3/Site"]], "2026-10-07", "2026-10-07", 2),
)
appels.clear()
x = S.sonder("B", {"date": "2026-10-01", "flux": [["lever", "l"]]}, [], J)
verifie(
    "sonder Workday seul",
    (x["flux"], x["date"], appels),
    ([["lever", "l"], ["workday", "t.wd3/Site"]], "2026-10-01", [("wd", "B")]),
)
appels.clear()
x = S.sonder("C", None, [("workday", "c.wd1/C_Careers")], J)
verifie("Workday cure", (x["flux"][-1], appels), (["workday", "c.wd1/C_Careers"], [("ats", "C")]))

appels.clear()
x = S.sonder(
    "PwC France",
    {"date": "2026-10-07", "flux": [], "wd_date": "2026-10-07"},
    [
        ("workday", "pwc.wd3/Global_Experienced_Careers"),
        ("workday", "pwc.wd3/Global_Campus_Careers"),
    ],
    J,
)
verifie(
    "flux cure ajoute sans resonder",
    (x["flux"], appels),
    (
        [
            ["workday", "pwc.wd3/Global_Experienced_Careers"],
            ["workday", "pwc.wd3/Global_Campus_Careers"],
        ],
        [],
    ),
)


# lire_workday : URL publique = hote/site + externalPath.
class _R:
    status_code = 200

    def json(self):
        return {
            "jobPostings": [
                {
                    "title": "ESG Analyst",
                    "externalPath": "/job/Paris/ESG_R1",
                    "locationsText": "Paris",
                },
                {"title": "", "externalPath": "/x"},
            ]
        }


S._wd_jobs = lambda *a, **k: _R()
verifie(
    "lire_workday",
    S.lire_workday("erm.wd3/erm_Careers", "esg"),
    [("ESG Analyst", "https://erm.wd3.myworkdayjobs.com/erm_Careers/job/Paris/ESG_R1", "Paris")],
)
verifie(
    "lire_flux workday", S.lire_flux("workday", "erm.wd3/erm_Careers", "esg")[0][0], "ESG Analyst"
)
S._wd_jobs = lambda *a, **k: None
verifie("reseau en panne", S.lire_workday("erm.wd3/erm_Careers", "esg"), None)

# coquille : compte ATS de demonstration (google.recruitee.com, 2026-10-07).
verifie(
    "coquille : que des offres modeles",
    S.coquille([("Senior Marketer (Sample)", "u", "London")]),
    True,
)
verifie(
    "coquille : le modele a cote d'une offre saisie (accenture.recruitee)",
    S.coquille([("Senior Marketer (Sample)", "u", ""), ("sales executive", "v", "")]),
    True,
)
verifie("coquille : vraies offres seules", S.coquille([("ESG Analyst", "v", "")]), False)
verifie("coquille : flux vide n'en est pas une", S.coquille([]), False)

print(f"✅ {ok}/{ok + ko}")
sys.exit(1 if ko else 0)
