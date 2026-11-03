"""3.75: the interface audit of 2026-11-02 — no dead button, no duplicate, words a user reads.

Synthetic data only (public repository).
"""

import re
import sys
from pathlib import Path

import pytest

from jobhunter.programs import follow_ups
from jobhunter.storage import applications
from jobhunter.web import api, i18n, messages
from jobhunter.web.texts import TEXTES

STATIQUE = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
JS = (STATIQUE / "app.js").read_text(encoding="utf-8")


# --- No button asks for something that does not exist ----------------------------------------


def test_chaque_tache_lancee_existe():
    for cle in re.findall(r"""lancer\(\s*"([a-z_]+)\"""", JS):
        assert cle in api.TACHES, cle


def test_chaque_ecriture_existe():
    for nom in set(re.findall(r"""(?:ecrire|appel|choixFichier)\(\s*"([a-z_]+)\"""", JS)):
        assert hasattr(api.Api, nom), nom


def test_brouillon_de_relance_d_une_offre(monkeypatch):
    vus = []
    monkeypatch.setattr(
        follow_ups,
        "make_draft",
        lambda k, j=7, open_mailto=True: vus.append((k, j, open_mailto)) or True,
    )
    monkeypatch.setattr(
        applications, "charger", lambda *a, **k: {"Acme|Analyste": {"s": "relancé"}}
    )
    monkeypatch.setattr(sys, "argv", ["follow_ups", "--brouillon-de", "Acme|Analyste"])
    with pytest.raises(SystemExit) as fin:
        follow_ups.main()
    assert fin.value.code == 0
    assert vus == [("Acme|Analyste", 10, False)]  # J+10 after a follow-up; no mail client


def test_la_tache_relance_prend_l_offre(monkeypatch):
    a = api.Api()
    monkeypatch.setattr(a, "_file", lambda *x, **k: [{"entreprise": "Acme", "poste": "Analyste"}])
    lances = []
    monkeypatch.setattr(a, "_demarrer", lambda cle, lib, args: lances.append(args) or {"ok": True})
    assert a.lancer("relance", "Acme|Analyste")["ok"]
    assert lances[0][-2:] == ["--brouillon-de", "Acme|Analyste"]
    assert not a.lancer("relance", "Inconnue|X")["ok"]


# --- No duplicate ---------------------------------------------------------------------------


def test_supprimer_n_existe_plus_dans_la_fenetre():
    assert "supprimer(" not in JS and '"Supprimer…"' not in JS


def test_le_menu_outils_ne_repete_aucun_bouton():
    noms = [o for g in api.Api().outils() for o in g["outils"]]
    libelles = {o["libelle"] for o in noms}
    for repete in ("CV/lettres…", "Relances", "Re-score", "URLs mortes", "Profils…"):
        assert repete not in libelles
    assert all(o["nom"] and o["aide"] for o in noms)  # a clear name and what it is for
    assert '"Scan offres"' not in JS and '"Recharger"' not in JS


def test_une_seule_place_pour_les_lettres():
    assert "cartesDocumentsBase" not in JS and "remplacerCvBase" not in JS
    assert "function phrase(m)" in JS


# --- Words ----------------------------------------------------------------------------------


def test_un_seul_mot_pour_la_note():
    textes = re.findall(r'"([^"]*)"', JS)
    assert not [t for t in textes if re.search(r"\b[Ff]it\b", t) and " " in t]
    assert api.TACHES["rescore"][0] == "Recalculer les scores"


def test_aucune_exception_brute():
    racine = STATIQUE.parent
    for f in racine.glob("*.py"):
        assert "type(e).__name__}: {e}" not in f.read_text(encoding="utf-8"), f.name
    assert messages.echec(PermissionError(13, "x")).startswith("Le fichier est ouvert")
    assert messages.echec(ValueError("mauvais")) == "Échec : mauvais"


def test_aucun_nom_de_fichier_montre():
    assert ".bak" not in re.sub(r"//[^\n]*", "", JS)
    assert "_corbeille" not in JS


def test_les_messages_commencent_par_une_majuscule():
    for f in STATIQUE.parent.glob("*.py"):
        for m in re.finditer(r'"erreur":\s*f?"(.)', f.read_text(encoding="utf-8")):
            assert not m.group(1).islower(), (f.name, m.group(0))


def test_chaque_texte_de_la_fenetre_est_traduit():
    """Every literal the page shows in a button, card, dialog or toast has its English."""
    # a word the same in English ("Documents") is dropped from the catalogue: TEXTES has it
    connus = set(i18n.catalogue("en")["textes"]) | set(TEXTES)
    motif = r'(?:(?:bouton|action|carte|dialogue|toast)\(|h\("(?:h2|h3|summary)", \{\},)\s*"([^"]*[a-zà-ÿ][^"]*)"'
    manque = sorted({t for t in re.findall(motif, JS) if t.strip() and t not in connus})
    assert not manque, manque


def test_les_puces_se_replient():
    assert "const PUCES_MAX = 15;" in JS and "`+ ${reste} autres`" in JS
    # replaceChildren writes a null as the text « null »: no bare null among its arguments
    corps = JS[JS.index("function editeurPuces") : JS.index("function editeurLieux")]
    assert '"Replier") : null' not in corps
