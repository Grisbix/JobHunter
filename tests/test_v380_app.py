"""3.80, the window: daily triage, archiving, the board's follow-ups, documents' offers."""

from datetime import date, timedelta

import pytest

from jobhunter import root
from jobhunter.web import api as api_mod
from jobhunter.web import opened
from jobhunter.web.api import Api


@pytest.fixture
def donnees(tmp_path, monkeypatch):
    monkeypatch.setattr(root, "scripts", lambda: tmp_path)
    return tmp_path


def _scan(jours):
    return f"Scan {(date.today() - timedelta(days=jours)).isoformat()}"


def _api(offres, suivi=None):
    a = Api()
    a._file = lambda: offres
    a._suivi = lambda: suivi or {}
    a._descriptions = lambda: {}
    return a


def test_ouvertes_notees_une_fois(donnees):
    assert opened.lire() == {}
    assert opened.noter("A|P") is True
    assert opened.noter(["A|P"]) is False
    assert opened.lire() == {"A|P": date.today().isoformat()}


def test_tri_bonnes_jamais_ouvertes_meilleures_d_abord(donnees):
    a = _api(
        [
            {"entreprise": "A", "poste": "P", "fit": 8, "statut": _scan(1)},
            {"entreprise": "B", "poste": "P", "fit": 10, "statut": _scan(1)},
            {"entreprise": "C", "poste": "P", "fit": 5, "statut": _scan(1)},  # under 8
            {"entreprise": "D", "poste": "P", "fit": 9, "statut": _scan(1)},  # applied
        ],
        {"D|P": {"s": "postulé"}},
    )
    assert a.a_trier() == {"total": 2, "ids": ["B|P", "A|P"]}
    assert a.offre("B|P")["poste"] == "P"  # opening it takes it out
    assert a.a_trier()["ids"] == ["A|P"]


def test_archiver_epargne_ouvertes_suivies_bonnes_et_recentes(donnees, monkeypatch):
    offres = [
        {"entreprise": "Vieille", "poste": "P", "fit": 5, "statut": _scan(90)},
        {"entreprise": "Ouverte", "poste": "P", "fit": 5, "statut": _scan(90)},
        {"entreprise": "Suivie", "poste": "P", "fit": 5, "statut": _scan(90)},
        {"entreprise": "Bonne", "poste": "P", "fit": 9, "statut": _scan(90)},
        {"entreprise": "Recente", "poste": "P", "fit": 5, "statut": _scan(10)},
    ]
    opened.noter("Ouverte|P")
    a = _api(offres, {"Suivie|P": {"s": "pas intéressé"}})
    pris = []
    monkeypatch.setattr(a, "supprimer", lambda ids: pris.extend(ids) or {"ok": True, "n": len(ids)})
    assert a.archivables(60) == 1
    assert a.archiver(60) == {"ok": True, "n": 1}
    assert pris == ["Vieille|P"]


def test_kanban_jours_relance_et_brouillon(donnees, tmp_path, monkeypatch):
    brouillons = tmp_path / "relances"
    brouillons.mkdir()
    (brouillons / "Relance_J7_DAHER_BUSINESS_Charge_ESG.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(api_mod, "_dossier_relances", lambda: brouillons)
    il_y_a = lambda j: (date.today() - timedelta(days=j)).isoformat()  # noqa: E731
    a = _api(
        [],
        {
            "DAHER BUSINESS|Chargé ESG": {"s": "postulé", "d": il_y_a(9)},
            "Autre|P": {"s": "postulé", "d": il_y_a(8)},
            "Neuve|P": {"s": "postulé", "d": il_y_a(2)},
            "Entretien|P": {"s": "entretien", "d": il_y_a(30)},
        },
    )
    cartes = {e["entreprise"]: e for c in a.candidatures()["colonnes"] for e in c["entrees"]}
    assert (cartes["DAHER BUSINESS"]["jours"], cartes["DAHER BUSINESS"]["relance_due"]) == (9, True)
    assert cartes["DAHER BUSINESS"]["brouillon"] is True
    assert (cartes["Autre"]["relance_due"], cartes["Autre"]["brouillon"]) == (True, False)
    assert cartes["Neuve"]["relance_due"] is False
    assert cartes["Entretien"]["jours"] is None and cartes["Entretien"]["relance_due"] is False


def test_documents_relies_a_leur_offre_et_filtre_envoyees(donnees, tmp_path, monkeypatch):
    cvs = tmp_path / "cv"
    cvs.mkdir()
    (cvs / "CV_A_P.pdf").write_bytes(b"x")
    (cvs / "CV_B_P.pdf").write_bytes(b"x")
    monkeypatch.setattr(api_mod, "_dossiers_documents", lambda: {"CV": cvs})
    a = _api(
        [
            {"entreprise": "A", "poste": "P", "cv": str(cvs / "CV_A_P.pdf")},
            {"entreprise": "B", "poste": "P", "cv": str(cvs / "CV_B_P.pdf")},
        ],
        {"A|P": {"s": "postulé"}},
    )
    tous = {f["nom"]: (f["offre"], f["statut"]) for f in a.documents()["fichiers"]}
    assert tous == {"CV A P": ("A|P", "postulé"), "CV B P": ("B|P", "")}
    envoyes = a.documents({"en_cours": True})["fichiers"]
    assert [f["nom"] for f in envoyes] == ["CV A P"]


def test_maintenance_distingue_suivies_et_envoyees(donnees, monkeypatch):
    a = _api(
        [],
        {
            "A|P": {"s": "postulé"},
            "B|P": {"s": "refus"},
            "C|P": {"s": "pas intéressé"},
            "D|P": {"s": ""},
        },
    )
    m = a.maintenance()
    assert (m["candidatures"], m["envoyees"], m["archivables"]) == (3, 2, 0)


def test_kanban_compte_les_jours_depuis_le_jour_donne():
    """The board's pure function takes the day, like tableau(): no clock in the test."""
    suivi = {
        "A|P": {"s": "postulé", "d": "2026-11-01"},
        "B|P": {"s": "relancé", "d": "2026-10-27"},
    }
    d = api_mod.candidatures([], suivi, aujourd_hui=date(2026, 11, 3))
    cartes = {e["entreprise"]: e for c in d["colonnes"] for e in c["entrees"]}
    assert (cartes["A"]["jours"], cartes["A"]["relance_due"]) == (2, False)
    assert (cartes["B"]["jours"], cartes["B"]["relance_due"]) == (7, True)


def test_passer_remet_l_offre_a_la_fin_du_tri(donnees):
    """« Passer » (the user, 2026-11-05): next offer, nothing deleted, back at the end."""
    a = _api(
        [
            {"entreprise": "A", "poste": "P", "fit": 10, "statut": _scan(1)},
            {"entreprise": "B", "poste": "P", "fit": 9, "statut": _scan(1)},
            {"entreprise": "C", "poste": "P", "fit": 8, "statut": _scan(1)},
        ]
    )
    a.offre("A|P")  # shown: opened
    assert a.passer("A|P") == {"ok": True}
    assert a.a_trier() == {"total": 3, "ids": ["B|P", "C|P", "A|P"]}
    a.offre("B|P")
    a.passer("B|P")
    assert a.a_trier()["ids"] == ["C|P", "A|P", "B|P"]
    a.offre("A|P")
    a.passer("A|P")  # passed again: to the very end
    assert a.a_trier()["ids"] == ["C|P", "B|P", "A|P"]
