"""Application driven by the application (apply_runner --pilote) and proof of sending.

The protocol (`@JH {json}` events, commands on stdin), the sending declaration
that observes the page and writes the tracker (ADR 0009), and the safeguard: the program
NEVER clicks the send button. End to end on local pages: it is the TEST that
clicks Send, in place of the human; no real application is sent.
"""

import functools
import io
import json

import pytest

from jobhunter.navigation import confirmation
from jobhunter.programs import apply_runner as ar

OFFRE = {"comp": "Acme", "role": "Analyste ESG", "url": "https://ats.example/job/1"}

# A fake application form: sending replaces the page with a thank-you message.
# Each click on the button is counted in window.__clics.
FORMULAIRE = """
<form id=f onsubmit="event.preventDefault();
    document.body.innerHTML = '<h1>Merci pour votre candidature !</h1>';">
  <input name=nom value=Gabriel><input name=mail type=email value=g@example.com>
  <input type=file name=cv>
  <button type=submit onclick="window.__clics = (window.__clics || 0) + 1">
    Envoyer ma candidature</button>
</form>
"""


# ── the protocol ──────────────────────────────────────────────────────────────
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
    assert '"attente"' in capsys.readouterr().out  # the app knows it is being waited for


def test_aucune_commande_n_envoie():
    """No command of the protocol corresponds to a send click: `envoye` DECLARES."""
    assert set(ar._COMMANDES) == {"envoye", "saute", "reremplir", "rouvrir", "quitter"}


# ── sending declaration, end to end on a local page ─────────────────────────
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
    page.click("button")  # The HUMAN clicks Send (here, the test)
    res = ar.declarer_envoi(page, OFFRE)
    rec = lire(preuves)["Acme|Analyste ESG"]
    assert res["etat"] == rec["envoi"] == "confirmé"
    assert rec["s"] == "postulé" and "Merci pour votre candidature" in rec["preuve"]["texte"]
    assert (tmp_path / "preuves" / "p.png").exists()


def test_envoi_non_fait_incertain(page, preuves):
    page.set_content(FORMULAIRE)  # nobody clicked: the form is still there
    res = ar.declarer_envoi(page, OFFRE)
    assert res["etat"] == lire(preuves)["Acme|Analyste ESG"]["envoi"] == "incertain"


# ── the safeguard: the program never clicks Send ─────────────────────────
def test_le_programme_ne_clique_jamais_envoyer(page, preuves, monkeypatch):
    page.set_content(FORMULAIRE)
    assert ar.highlight_submit(page) == "Envoyer ma candidature"  # highlighted, not clicked
    monkeypatch.setattr(ar.sys, "stdin", io.StringIO("envoye\n"))
    marques = []
    assert ar._decision_pilote(ar._Pilote(), page, OFFRE, marques.append) == "s"
    assert page.evaluate("window.__clics || 0") == 0
    assert marques == ["ENVOYÉ"]
    # nobody clicked: the declaration stays without confirmation
    assert lire(preuves)["Acme|Analyste ESG"]["envoi"] == "incertain"


def test_sauter_n_ecrit_pas_le_suivi(page, preuves, monkeypatch):
    page.set_content(FORMULAIRE)
    monkeypatch.setattr(ar.sys, "stdin", io.StringIO("saute\n"))
    marques = []
    assert ar._decision_pilote(ar._Pilote(), page, OFFRE, marques.append) == "k"
    assert marques == ["SAUTÉ"] and not preuves.exists()
