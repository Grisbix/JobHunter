"""An offer removed by the sort does not come back at collection (rejets_tri, job_sources).

Memorisation, 30-day expiry, original date kept, and the merge that
ignores a NEW rejected offer without touching an offer already in the queue. Without
network, on throwaway files. Converted from Scripts/test_rejets_tri.py.
"""

import datetime
import json

import pytest

from jobhunter import sources as J
from jobhunter.programs import sort_rejections as R

J0 = datetime.date(2026, 10, 5)
CLE = "Acme|Senior ESG Manager"


@pytest.fixture
def memoire(tmp_path):
    f = tmp_path / "rej.json"
    R.ajouter({CLE: "seniorite"}, f, J0)
    return f


def test_rejet_memorise(memoire):
    assert CLE in R.charger(memoire, J0)


def test_motif_garde(memoire):
    assert R.charger(memoire, J0)[CLE]["m"] == "seniorite"


def test_valable_a_j_plus_29(memoire):
    assert CLE in R.charger(memoire, J0 + datetime.timedelta(29))


def test_expire_a_j_plus_30(memoire):
    assert CLE not in R.charger(memoire, J0 + datetime.timedelta(30))


def test_re_rejet_garde_la_date_d_origine(memoire):
    jour = J0 + datetime.timedelta(10)
    R.ajouter({CLE: "experience"}, memoire, jour)
    assert R.charger(memoire, jour)[CLE]["d"] == J0.isoformat()


def test_expires_purges_a_l_ecriture(memoire):
    R.ajouter({"B|X": "experience"}, memoire, J0 + datetime.timedelta(31))
    assert sorted(json.loads(memoire.read_text(encoding="utf-8"))) == ["B|X"]


def test_fichier_absent(tmp_path):
    assert R.charger(tmp_path / "absent.json") == {}


@pytest.fixture
def fusion(tmp_path, monkeypatch):
    """A queue with Mirova already in it; Deloitte and Mirova rejected by the sort."""
    q = tmp_path / "q.json"
    q.write_text(
        json.dumps(
            [
                {
                    "entreprise": "Mirova",
                    "poste": "Analyste ESG",
                    "statut": "Scan 2026-10-01",
                    "url": "https://www.linkedin.com/jobs/view/1",
                    "fit": 9,
                    "description": "",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rej = tmp_path / "rej_merge.json"
    R.ajouter(
        {"Deloitte|Senior Manager ESG": "seniorite", "Mirova|Analyste ESG": "experience"}, rej
    )
    monkeypatch.setattr(J, "QUEUE", q)
    monkeypatch.setattr(J, "REJETS_TRI", rej)
    entrant = [
        J._mk("Senior Manager ESG", "https://www.linkedin.com/jobs/view/2", "Deloitte"),
        J._mk("Analyste ESG", "https://www.linkedin.com/jobs/view/1", "Mirova"),
        J._mk("Chargé de mission ESG", "https://www.linkedin.com/jobs/view/3", "Bpifrance"),
    ]
    bilan = J.merge_into_queue(entrant, dry=False)
    apres = {f"{o['entreprise']}|{o['poste']}" for o in json.loads(q.read_text(encoding="utf-8"))}
    return bilan, apres


def test_offre_rejetee_non_reprise(fusion):
    assert "Deloitte|Senior Manager ESG" not in fusion[1]


def test_compteur_rejetees_tri(fusion):
    assert fusion[0].get("rejetees_tri") == 1


def test_offre_deja_en_file_intacte(fusion):
    assert "Mirova|Analyste ESG" in fusion[1]


def test_offre_nouvelle_ajoutee(fusion):
    assert "Bpifrance|Chargé de mission ESG" in fusion[1]
