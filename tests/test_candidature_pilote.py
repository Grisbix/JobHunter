"""Candidature pilotée par l'application (apply_runner --pilote) et preuve d'envoi.

Le protocole (événements `@JH {json}`, commandes sur stdin), la déclaration d'envoi
qui observe la page et écrit le suivi (ADR 0009), et le garde-fou : le programme ne
clique JAMAIS le bouton d'envoi. Bout en bout sur des pages locales : c'est le TEST qui
clique Envoyer, à la place de l'humain ; aucune vraie candidature n'est envoyée.
"""

import functools
import io
import json

import pytest

from jobhunter.navigation import confirmation
from jobhunter.programmes import apply_runner as ar

OFFRE = {"comp": "Acme", "role": "Analyste ESG", "url": "https://ats.example/job/1"}

# Un faux formulaire de candidature : l'envoi remplace la page par un message de merci.
# Chaque clic sur le bouton est compté dans window.__clics.
FORMULAIRE = """
<form id=f onsubmit="event.preventDefault();
    document.body.innerHTML = '<h1>Merci pour votre candidature !</h1>';">
  <input name=nom value=Gabriel><input name=mail type=email value=g@example.com>
  <input type=file name=cv>
  <button type=submit onclick="window.__clics = (window.__clics || 0) + 1">
    Envoyer ma candidature</button>
</form>
"""


# ── le protocole ──────────────────────────────────────────────────────────────
def test_evenement_ligne_json(capsys):
    ar._Pilote().evenement("offre", i=1, total=3, entreprise="Acme")
    ligne = capsys.readouterr().out.strip()
    assert ligne.startswith("@JH ")
    assert json.loads(ligne[4:]) == {"type": "offre", "i": 1, "total": 3, "entreprise": "Acme"}


@pytest.mark.parametrize(
    ("ligne", "touche"),
    [
        ("envoye\n", "s"),
        ("saute\n", "k"),
        ("reremplir\n", "r"),
        ("rouvrir\n", "o"),
        ("quitter\n", "q"),
        ("n'importe quoi\n", ""),
        ("", "q"),
    ],
)
def test_commandes(monkeypatch, capsys, ligne, touche):
    monkeypatch.setattr(ar.sys, "stdin", io.StringIO(ligne))
    assert ar._Pilote().commande("invite ignorée") == touche
    assert '"attente"' in capsys.readouterr().out  # l'app sait qu'on l'attend


def test_aucune_commande_n_envoie():
    """Aucune commande du protocole ne correspond à un clic d'envoi : `envoye` DÉCLARE."""
    assert set(ar._COMMANDES) == {"envoye", "saute", "reremplir", "rouvrir", "quitter"}


# ── déclaration d'envoi, bout en bout sur une page locale ─────────────────────────
@pytest.fixture
def preuves(tmp_path, monkeypatch, suivi_temporaire):
    monkeypatch.setattr(ar, "_chemin_preuve", lambda d: tmp_path / "preuves" / "p.png")
    monkeypatch.setattr(
        confirmation,
        "observer_confirmation",
        functools.partial(confirmation.observer_confirmation, attente=1.0, pas=0.1),
    )
    return suivi_temporaire


def lire(chemin):
    return json.loads(chemin.read_text(encoding="utf-8"))


def test_envoi_confirme(page, preuves, tmp_path):
    page.set_content(FORMULAIRE)
    page.click("button")  # L'HUMAIN clique Envoyer (ici, le test)
    res = ar.declarer_envoi(page, OFFRE)
    rec = lire(preuves)["Acme|Analyste ESG"]
    assert res["etat"] == rec["envoi"] == "confirmé"
    assert rec["s"] == "postulé" and "Merci pour votre candidature" in rec["preuve"]["texte"]
    assert (tmp_path / "preuves" / "p.png").exists()


def test_envoi_non_fait_incertain(page, preuves):
    page.set_content(FORMULAIRE)  # personne n'a cliqué : le formulaire est toujours là
    res = ar.declarer_envoi(page, OFFRE)
    assert res["etat"] == lire(preuves)["Acme|Analyste ESG"]["envoi"] == "incertain"


# ── le garde-fou : le programme ne clique jamais Envoyer ─────────────────────────
def test_le_programme_ne_clique_jamais_envoyer(page, preuves, monkeypatch):
    page.set_content(FORMULAIRE)
    assert ar.highlight_submit(page) == "Envoyer ma candidature"  # surligné, pas cliqué
    monkeypatch.setattr(ar.sys, "stdin", io.StringIO("envoye\n"))
    marques = []
    assert ar._decision_pilote(ar._Pilote(), page, OFFRE, marques.append) == "s"
    assert page.evaluate("window.__clics || 0") == 0
    assert marques == ["ENVOYÉ"]
    # personne n'a cliqué : la déclaration reste sans confirmation
    assert lire(preuves)["Acme|Analyste ESG"]["envoi"] == "incertain"


def test_sauter_n_ecrit_pas_le_suivi(page, preuves, monkeypatch):
    page.set_content(FORMULAIRE)
    monkeypatch.setattr(ar.sys, "stdin", io.StringIO("saute\n"))
    marques = []
    assert ar._decision_pilote(ar._Pilote(), page, OFFRE, marques.append) == "k"
    assert marques == ["SAUTÉ"] and not preuves.exists()
