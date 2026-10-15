#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_glassdoor_refus.py — Glassdoor face a un refus d'entree, sans reseau.

Le 2026-10-07 (et le 03), l'etape 1e du pipeline a ete tuee a 40 min : chaque
mot-cle recevait un 403, attendait 45 s, reessayait, et la passe continuait.
Regle d'AGENTS.md : une limite de debit s'attend, un refus d'entree s'arrete.

Couvre : arret au premier 403, sans repos ni seconde requete ; refus compte
dans INCIDENTS ; offres deja lues conservees ; un 429 garde sa pause et sa
seconde chance ; une page normale est lue.

Run : python test_glassdoor_refus.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import io
import sys
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.argv = ["x"]
import job_sources as js

ok = ko = 0


def ck(nom, cond):
    global ok, ko
    if cond:
        ok += 1
        print(f"✅ {nom}")
    else:
        ko += 1
        print(f"❌ {nom}")


dormi = []
js.time.sleep = lambda s: dormi.append(s)

PAGE = ('<a class="x" data-test="job-title" href="https://www.glassdoor.fr/job/{n}">'
        'Analyste ESG junior</a><div data-test="emp-location">Paris</div>')


def erreur(code):
    return urllib.error.HTTPError("https://www.glassdoor.fr/", code, "refus", {}, None)


def rejouer(reponses):
    """Remplace urlopen par une file : un code HTTP leve l'erreur, un texte
    devient la page servie. Rend la liste des URL demandees."""
    it = iter(reponses)
    vus = []

    def urlopen(req, timeout=None):
        vus.append(req.full_url)
        x = next(it, 403)
        if isinstance(x, int):
            raise erreur(x)
        return io.BytesIO(x.encode("utf-8"))
    urllib.request.urlopen = urlopen
    return vus


def scan(mots):
    js.INCIDENTS.clear()
    dormi.clear()
    buf = io.StringIO()
    with redirect_stdout(buf):
        res = js.scan_glassdoor(mots=mots, pause=12)
    return res, buf.getvalue()


MOTS = [f"mot {i}" for i in range(10)]

# ── 1. 403 des le premier mot : arret immediat ───────────────────────────────
vus = rejouer([403] * 50)
res, sortie = scan(MOTS)
ck("403 : une seule requete, pas de seconde chance ni de mot suivant", len(vus) == 1)
ck("403 : aucun repos (ni 45 s, ni pause entre mots)", dormi == [])
ck("403 : passe annoncee comme refus d'entree", "refus d'entree" in sortie)
ck("403 : compte dans INCIDENTS", js.INCIDENTS["glassdoor"].get("HTTP 403") == 1)
ck("403 : rien collecte, sans exception", res == [])

# ── 2. 403 apres des succes : les offres lues sont gardees ───────────────────
vus = rejouer([PAGE.format(n=1), PAGE.format(n=2), 403])
res, sortie = scan(MOTS)
ck("403 au 3e mot : trois requetes, pas une de plus", len(vus) == 3)
ck("403 au 3e mot : les deux offres deja lues sont conservees", len(res) == 2)
ck("403 au 3e mot : seulement les pauses entre mots, pas de repos de 45 s",
   js.GD_REPOS not in dormi)

# ── 3. un 429 reste une limite de debit : pause puis seconde chance ──────────
vus = rejouer([429, PAGE.format(n=3)])
res, sortie = scan(MOTS[:1])
ck("429 : repos avant la seconde chance", js.GD_REPOS in dormi)
ck("429 : seconde requete, offre lue", len(vus) == 2 and len(res) == 1)

# ── 4. 429 persistant : arret apres GD_ABANDON refus d'affilee ───────────────
vus = rejouer([429] * 100)
res, sortie = scan(MOTS)
ck("429 persistant : arret au bout de GD_ABANDON mots",
   len(vus) == 2 * js.GD_ABANDON)
ck("429 persistant : compte dans INCIDENTS",
   js.INCIDENTS["glassdoor"].get("HTTP 429") == js.GD_ABANDON)

print(f"\n=== BILAN : {ok} ✅  /  {ko} ❌  ({ok}/{ok + ko}) ===")
sys.exit(1 if ko else 0)
