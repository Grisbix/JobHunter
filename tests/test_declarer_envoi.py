"""suivi_io.declarer_envoi: an application sent, with the state of its proof (ADR 0009).

A single write in suivi.json; the note and follow-ups kept; a more advanced
status does not move back; a declaration without proof never erases an observed proof.
"""

import datetime
import json

import pytest

from jobhunter.stockage import suivi as suivi_io

OID = "Amundi|Analyste ESG"
PREUVE = {
    "texte": "Merci pour votre candidature",
    "url": "https://ats.example/thank-you",
    "capture": "x.png",
    "le": "2026-10-19T12:00:00",
}
AUJOURD_HUI = datetime.date.today().isoformat()


@pytest.fixture
def suivi(tmp_path):
    chemin = tmp_path / "suivi.json"

    def avec(contenu):
        chemin.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")
        return chemin

    return avec


def lire(chemin):
    return json.loads(chemin.read_text(encoding="utf-8"))


def test_nouvelle_candidature_confirmee(suivi):
    c = suivi({})
    suivi_io.declarer_envoi(OID, "confirmé", PREUVE, chemin=c)
    assert lire(c)[OID] == {"s": "postulé", "d": AUJOURD_HUI, "envoi": "confirmé", "preuve": PREUVE}


def test_note_gardee_et_date_du_jour(suivi):
    c = suivi({OID: {"s": "à postuler", "d": "2026-09-01", "n": "relire la lettre"}})
    suivi_io.declarer_envoi(OID, "incertain", PREUVE, chemin=c)
    rec = lire(c)[OID]
    assert (rec["s"], rec["d"], rec["n"], rec["envoi"]) == (
        "postulé",
        AUJOURD_HUI,
        "relire la lettre",
        "incertain",
    )


@pytest.mark.parametrize("statut", ["relancé", "entretien", "refus"])
def test_statut_plus_avance_ne_recule_pas(suivi, statut):
    c = suivi({OID: {"s": statut, "d": "2026-09-20"}})
    suivi_io.declarer_envoi(OID, "confirmé", PREUVE, chemin=c)
    assert lire(c)[OID]["s"] == statut and lire(c)[OID]["d"] == "2026-09-20"


def test_declaration_manuelle_n_efface_pas_la_preuve(suivi):
    c = suivi({OID: {"s": "postulé", "d": "2026-10-19", "envoi": "confirmé", "preuve": PREUVE}})
    suivi_io.declarer_envoi(OID, "déclaré", chemin=c)
    rec = lire(c)[OID]
    assert rec["envoi"] == "confirmé" and rec["preuve"] == PREUVE


def test_declaration_manuelle_sans_preuve(suivi):
    c = suivi({})
    suivi_io.declarer_envoi(OID, "déclaré", chemin=c)
    assert lire(c)[OID] == {"s": "postulé", "d": AUJOURD_HUI, "envoi": "déclaré"}


def test_autres_candidatures_intactes(suivi):
    autre = {"BNP|Analyste": {"s": "relancé", "d": "2026-09-01", "n": "x"}}
    c = suivi(dict(autre))
    suivi_io.declarer_envoi(OID, "confirmé", PREUVE, chemin=c)
    assert lire(c)["BNP|Analyste"] == autre["BNP|Analyste"]
