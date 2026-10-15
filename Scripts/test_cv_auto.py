#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cv_auto.py — CV automatique depuis CV/Faits.json, sans reseau ni LLM.

Couvre : un fait non valide n'est JAMAIS utilise ; les declencheurs ; les faux
positifs connus (« faire preuve d'énergie ») ; l'application aux vrais modeles
FR et EN ; les allegements ; la priorite du sur-mesure sur l'automatique.

Run : python test_cv_auto.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, __import__("os").path.dirname(__file__))

import cv_auto
import tailor_application as ta
from docx import Document

ok = ko = 0


def ck(nom, cond):
    global ok, ko
    if cond:
        ok += 1
        print(f"✅ {nom}")
    else:
        ko += 1
        print(f"❌ {nom}")


# ── 1. la banque fictive : un fait valide, un fait NON valide ────────────────
B = {
    "faits": [
        {"id": "vrai", "valide": True, "declencheurs": ["solaire"], "priorite": 5,
         "fr": [{"op": "ajoute_apres", "ancre": "ANCRE", "texte": "ligne vraie"}], "en": []},
        {"id": "pas_relu", "valide": False, "declencheurs": ["solaire"], "priorite": 9,
         "fr": [{"op": "ajoute_apres", "ancre": "ANCRE", "texte": "ligne inventee"}]},
    ],
    "allegements": {"fr": ["L1", "L2"], "en": ["E1"]},
}
r = cv_auto.retouches("Projet SOLAIRE en Espagne", "fr", b=B)
ck("fait valide retenu, casse ignoree", r["faits"] == ["vrai"])
ck("fait NON valide jamais utilise", all("inventee" not in x[1] for x in r["ajoute_apres"]))
ck("aucun declencheur -> aucune retouche", cv_auto.retouches("comptable", "fr", b=B)["faits"] == [])
ck("allege=0 -> rien retire", cv_auto.retouches("x", "fr", 0, b=B)["supprime"] == [])
ck("allege=1 -> premiere ligne seulement", cv_auto.retouches("x", "fr", 1, b=B)["supprime"] == ["L1"])
ck("allege au-dela -> toutes, sans erreur", cv_auto.retouches("x", "fr", 9, b=B)["supprime"] == ["L1", "L2"])
ck("fait sans version anglaise -> rien en anglais", cv_auto.retouches("solaire", "en", b=B)["faits"] == [])

# ── 2. une banque realiste : declencheurs et faux positifs ──────────────────
# Banque SYNTHETIQUE, sur le modele d'une vraie : un fait de secteur, un fait de
# langue, un fait desactive (propre a une seule candidature).
BANQUE = {
    "faits": [
        {"id": "renouvelables", "valide": True, "priorite": 5,
         "declencheurs": [r"photovolta", r"\bsolaire", r"\b[ée]olien"],
         "fr": [{"op": "ajoute_apres", "ancre": "Construction de modèles",
                 "texte": "Études de projets photovoltaïques, dont un parc en Andalousie"}],
         "en": [{"op": "ajoute_apres", "ancre": "Built valuation models",
                 "texte": "Studies of solar projects, including a park in Andalusia"}]},
        {"id": "espagnol_avance", "valide": True, "priorite": 3,
         "declencheurs": [r"espagnol", r"spanish", r"español"],
         "fr": [{"op": "remplace", "ancre": "Espagnol (débutant)", "texte": "Espagnol (avancé)"}],
         "en": [{"op": "remplace", "ancre": "Spanish (beginner)", "texte": "Spanish (advanced)"}]},
        {"id": "client_unique", "valide": False, "priorite": 9, "declencheurs": [r"photovolta"],
         "fr": [{"op": "ajoute_apres", "ancre": "Construction de modèles",
                 "texte": "Mission chez un client précis"}]},
    ],
    "allegements": {"fr": ["Ligne facultative 1", "Ligne facultative 2"], "en": ["Optional line"]},
}
_rt = cv_auto.retouches
cv_auto.retouches = lambda t, l="fr", allege=0, b=None: _rt(t, l, allege, BANQUE if b is None else b)


def ids(t):
    return [x["id"] for x in cv_auto.faits_retenus(t, BANQUE)]


ck("photovoltaique -> renouvelables", "renouvelables" in ids("Investment analyst, centrales photovoltaïques"))
ck("fait desactive jamais retenu", "client_unique" not in ids("photovoltaïque"))
ck("« faire preuve d'énergie » ne declenche rien", ids("Data engineer : faire preuve d'énergie") == [])
ck("español -> espagnol avance", "espagnol_avance" in ids("Langues : Español avanzado requis"))

# ── 3. application a des modeles .docx, construits a la volee ───────────────
import tempfile
from pathlib import Path
_tmp = Path(tempfile.mkdtemp())


def modele(lignes, nom):
    d = Document()
    for texte, gras in lignes:
        r = d.add_paragraph().add_run(texte)
        r.bold = gras
    chemin = _tmp / nom
    d.save(str(chemin))
    return chemin


FIN_FR = modele([("Analyste Financier Junior : Acme Finance", True),
                 ("Construction de modèles de valorisation par DCF", False),
                 ("Ligne facultative 1", False), ("Ligne facultative 2", False),
                 ("Espagnol (débutant)", False)], "fr.docx")
FIN_EN = modele([("Junior Financial Analyst: Acme Finance", True),
                 ("Built valuation models using DCF", False), ("Spanish (beginner)", False)], "en.docx")
annonce = "Analyste en investissement photovoltaïque, espagnol B2/C1"

d = Document(str(FIN_FR))
manquees = ta.appliquer_cv_sur_mesure(d, cv_auto.retouches(annonce, "fr"))
textes = [p.text for p in d.paragraphs]
t = "\n".join(textes)
ck("FR : ligne du fait ajoutee", "parc en Andalousie" in t)
ck("FR : ajoutee juste apres son ancre",
   textes.index(next(x for x in textes if "Andalousie" in x)) ==
   textes.index(next(x for x in textes if x.startswith("Construction de modèles"))) + 1)
ck("FR : espagnol avance", "Espagnol (avancé)" in t and "Espagnol (débutant)" not in t)
ck("FR : toutes les ancres trouvees", manquees == [])
gras = next(p for p in d.paragraphs if p.text.startswith("Analyste Financier Junior"))
ck("FR : le titre garde son gras", all(r.bold for r in gras.runs if r.text.strip()))

d = Document(str(FIN_EN))
ta.appliquer_cv_sur_mesure(d, cv_auto.retouches(annonce + " Spanish", "en"))
t = "\n".join(p.text for p in d.paragraphs)
ck("EN : ligne du fait en anglais", "park in Andalusia" in t)
ck("EN : Spanish (advanced)", "Spanish (advanced)" in t and "Spanish (beginner)" not in t)

d = Document(str(FIN_FR))
avant = len([p for p in d.paragraphs if p.text.strip()])
ta.appliquer_cv_sur_mesure(d, cv_auto.retouches("comptable", "fr", allege=2))
apres = len([p for p in d.paragraphs if p.text.strip()])
ck("allegements : deux lignes du modele retirees", avant - apres == 2)

# ── 4. le sur-mesure l'emporte sur l'automatique ─────────────────────────────
import chemins
_cvsm = chemins.CV_SUR_MESURE
chemins.CV_SUR_MESURE = _tmp
(_tmp / "SOLAIRE SA__Analyste Investissement (H-F).json").write_text(
    '{"remplace": [["DCF", "DCF et LBO"]]}', encoding="utf-8")
ck("une offre avec retouches a son CV sur mesure",
   bool(ta.cv_sur_mesure(dict(company="SOLAIRE SA", role="Analyste Investissement (H/F)"))))
ck("une offre quelconque n'en a pas", ta.cv_sur_mesure(dict(company="X", role="Y")) is None)
chemins.CV_SUR_MESURE = _cvsm

print(f"\n=== BILAN : {ok} ✅  /  {ko} ❌  ({ok}/{ok + ko}) ===")
sys.exit(1 if ko else 0)
