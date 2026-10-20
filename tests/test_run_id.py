"""Which run produced a result (jobhunter.run_id), idea 17 of the architecture notes."""

import json

from jobhunter import run_id
from jobhunter.programs import source_yield as prog
from jobhunter.scoring import history as H
from jobhunter.sources import source_yield as R


def test_cree_puis_herite(monkeypatch):
    monkeypatch.delenv(run_id.ENV, raising=False)
    ident = run_id.courant()
    assert run_id.courant() == ident  # the same for the whole run
    # put in the environment: the programs this one starts inherit it
    import os

    assert os.environ[run_id.ENV] == ident


def test_herite_de_l_environnement(monkeypatch):
    monkeypatch.setenv(run_id.ENV, "20261021-080000-abcd")
    assert run_id.courant() == "20261021-080000-abcd"


def test_historique_du_score_porte_l_execution(monkeypatch):
    monkeypatch.setenv(run_id.ENV, "20261021-080000-abcd")
    o = {"fit": 6, "process": "2026-10-01"}
    H.poser(o, 9, 0, 9.0, "description")
    assert o["historique_fit"][-1]["execution"] == "20261021-080000-abcd"


def test_journal_de_rendement_porte_l_execution(tmp_path, monkeypatch):
    monkeypatch.setenv(run_id.ENV, "20261021-080000-abcd")
    monkeypatch.setattr(R, "MESURES", {"adzuna": {"ramenees": 3, "verdict": "ok"}})
    journal = tmp_path / "_rendement.jsonl"
    R.enregistrer(journal)
    assert json.loads(journal.read_text("utf-8"))["execution"] == "20261021-080000-abcd"


def test_yield_execution(tmp_path, monkeypatch, capsys):
    (tmp_path / "_rendement.jsonl").write_text(
        json.dumps(
            {
                "le": "2026-10-21T08:10:00",
                "execution": "X1",
                "sources": {"adzuna": {"ramenees": 12, "nouvelles": 4, "verdict": "ok"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(prog._racine, "scripts", lambda: tmp_path)
    from jobhunter.storage import queue as queue_io

    monkeypatch.setattr(
        queue_io,
        "charger",
        lambda **_: [
            {"entreprise": "A", "poste": "Analyste", "fit": 8, "execution": "X1"},
            {"entreprise": "B", "poste": "Autre", "fit": 9, "execution": "X0"},
        ],
    )
    assert prog.main(["--execution", "X1"]) == 0
    out = capsys.readouterr().out
    assert "adzuna" in out and "1 offre(s)" in out and "A — Analyste" in out
    assert "B — Autre" not in out
    assert prog.main(["--execution", "inconnue"]) == 1
