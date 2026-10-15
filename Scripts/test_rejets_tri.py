#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_rejets_tri.py — Une offre retiree par le tri ne revient pas a la collecte.

Couvre : memorisation, expiration a 30 jours, date d'origine conservee, et la
fusion de job_sources qui ignore une offre rejetee NOUVELLE sans toucher a une
offre deja en file. Sans reseau, sur fichiers jetables.

Run : python test_rejets_tri.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import json
import datetime
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.argv = ["x"]
import rejets_tri as R
import job_sources as J

ok = ko = 0


def check(nom, obtenu, attendu):
    global ok, ko
    if obtenu == attendu:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


tmpd = Path(tempfile.mkdtemp())
f = tmpd / "rej.json"
j0 = datetime.date(2026, 10, 5)

print("\n── A. memoire ──")
R.ajouter({"Acme|Senior ESG Manager": "seniorite"}, f, j0)
check("rejet memorise", "Acme|Senior ESG Manager" in R.charger(f, j0), True)
check("motif garde", R.charger(f, j0)["Acme|Senior ESG Manager"]["m"], "seniorite")
check("encore valable a J+29", "Acme|Senior ESG Manager" in R.charger(f, j0 + datetime.timedelta(29)), True)
check("expire a J+30", "Acme|Senior ESG Manager" in R.charger(f, j0 + datetime.timedelta(30)), False)
R.ajouter({"Acme|Senior ESG Manager": "experience"}, f, j0 + datetime.timedelta(10))
check("re-rejet : date d'origine conservee",
      R.charger(f, j0 + datetime.timedelta(10))["Acme|Senior ESG Manager"]["d"], j0.isoformat())
R.ajouter({"B|X": "experience"}, f, j0 + datetime.timedelta(31))
check("les expires sont purges a l'ecriture",
      sorted(json.loads(f.read_text(encoding="utf-8"))), ["B|X"])
check("fichier absent : aucun rejet", R.charger(tmpd / "absent.json"), {})

print("\n── B. la collecte ignore une offre rejetee ──")
q = tmpd / "q.json"
q.write_text(json.dumps([{
    "entreprise": "Mirova", "poste": "Analyste ESG", "statut": "Scan 2026-10-01",
    "url": "https://www.linkedin.com/jobs/view/1", "fit": 9, "description": "",
}], ensure_ascii=False), encoding="utf-8")
rej = tmpd / "rej_merge.json"
R.ajouter({"Deloitte|Senior Manager ESG": "seniorite", "Mirova|Analyste ESG": "experience"}, rej)
_q, _r = J.QUEUE, J.REJETS_TRI
J.QUEUE, J.REJETS_TRI = q, rej
try:
    entrant = [J._mk("Senior Manager ESG", "https://www.linkedin.com/jobs/view/2", "Deloitte"),
               J._mk("Analyste ESG", "https://www.linkedin.com/jobs/view/1", "Mirova"),
               J._mk("Chargé de mission ESG", "https://www.linkedin.com/jobs/view/3", "Bpifrance")]
    r = J.merge_into_queue(entrant, dry=False)
    apres = {f"{o['entreprise']}|{o['poste']}" for o in json.loads(q.read_text(encoding="utf-8"))}
    check("offre rejetee non reprise", "Deloitte|Senior Manager ESG" in apres, False)
    check("compteur rejetees_tri", r.get("rejetees_tri"), 1)
    check("offre deja en file intacte malgre le rejet", "Mirova|Analyste ESG" in apres, True)
    check("offre nouvelle non rejetee ajoutee", "Bpifrance|Chargé de mission ESG" in apres, True)
finally:
    J.QUEUE, J.REJETS_TRI = _q, _r

print(f"\n=== BILAN : {ok} ✅  /  {ko} ❌  ({ok}/{ok + ko}) ===")
sys.exit(1 if ko else 0)
