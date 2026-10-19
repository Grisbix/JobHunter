"""Rendement des sources (sources.rendement) : mesure, verdicts, journal et bilan.

Une collecte vide a des causes opposées ; le verdict les distingue (ADR 0004).
"""

import collections
import datetime
import json

import pytest

from jobhunter.programmes import rendement_sources as prog
from jobhunter.reseau import INCIDENTS
from jobhunter.sources import rendement as R


@pytest.fixture(autouse=True)
def propre():
    R.MESURES.clear()
    INCIDENTS.clear()
    yield
    R.MESURES.clear()
    INCIDENTS.clear()


@pytest.mark.parametrize(
    ("ramenees", "incidents", "attendu"),
    [
        (12, {}, R.OK),
        (0, {}, R.VIDE),
        (0, {"apec HTTP 403": 3}, R.REFUSE),
        (0, {"wtj challenge anti-bot": 1}, R.REFUSE),
        (40, {"linkedin HTTP 429": 2}, R.LIMITE),
        (0, {"linkedin HTTP 429": 2}, R.LIMITE),
        (5, {"ats:lever ReadTimeout": 1}, R.PARTIEL),
        (0, {"ats:lever ReadTimeout": 1}, R.PARTIEL),
        (7, {"glassdoor HTTP 403": 1}, R.PARTIEL),  # refusé en partie, mais des offres
    ],
)
def test_verdict(ramenees, incidents, attendu):
    assert R.verdict(ramenees, incidents) == attendu


def test_mesurer_etiquette_et_compte_les_incidents_de_l_appel():
    INCIDENTS["linkedin"]["HTTP 429"] += 1  # avant l'appel : ne compte pas

    def source():
        INCIDENTS["linkedin"]["HTTP 429"] += 2
        return [{"titre": "A"}, {"titre": "B"}]

    offres = R.mesurer("linkedin", source)
    assert [o["_passe"] for o in offres] == ["linkedin", "linkedin"]
    m = R.MESURES["linkedin"]
    assert m["ramenees"] == 2 and m["incidents"] == {"linkedin HTTP 429": 2}


def test_mesurer_note_meme_si_la_source_plante():
    def source():
        INCIDENTS["apec"]["HTTP 403"] += 1
        raise RuntimeError("refus")

    with pytest.raises(RuntimeError):
        R.mesurer("apec", source)
    assert R.MESURES["apec"]["ramenees"] == 0
    assert R.MESURES["apec"]["incidents"] == {"apec HTTP 403": 1}


def test_completer_et_journal(tmp_path):
    offres = R.mesurer("ats", lambda: [{"titre": "A"}, {"titre": "A bis"}, {"titre": "B"}])
    R.mesurer("apec", lambda: [])
    R.completer(offres[:2], {"ats": {"nouvelles": 2, "pertinentes": 1}})
    assert R.MESURES["ats"] | {"duree": 0} == {
        "ramenees": 3,
        "duree": 0,
        "incidents": {},
        "uniques": 2,
        "nouvelles": 2,
        "pertinentes": 1,
        "verdict": R.OK,
    }
    assert R.MESURES["apec"]["verdict"] == R.VIDE
    journal = tmp_path / "_rendement.jsonl"
    R.enregistrer(journal, datetime.datetime(2026, 10, 19, 8, 0))
    R.enregistrer(journal, datetime.datetime(2026, 10, 20, 8, 0))
    lignes = R.lire_journal(journal)
    assert len(lignes) == 2 and lignes[0]["le"] == "2026-10-19T08:00:00"
    total = R.bilan(lignes, depuis="2026-10-20")
    assert total["ats"]["collectes"] == 1 and total["ats"]["pertinentes"] == 1


def test_journal_ligne_abimee_sautee(tmp_path):
    journal = tmp_path / "j.jsonl"
    journal.write_text('{"le": "2026-10-19", "sources": {}}\npas du json\n', encoding="utf-8")
    assert len(R.lire_journal(journal)) == 1
    assert R.lire_journal(tmp_path / "absent.jsonl") == []


def test_bilan_signale_une_source_toujours_refusee(tmp_path, monkeypatch, capsys):
    aujourd_hui = datetime.date.today().isoformat()
    lignes = [
        {
            "le": aujourd_hui,
            "sources": {
                "apec": {"ramenees": 0, "duree": 3, "verdict": R.REFUSE},
                "ats": {
                    "ramenees": 9,
                    "nouvelles": 4,
                    "pertinentes": 2,
                    "duree": 60,
                    "verdict": R.OK,
                },
            },
        }
    ] * 2
    (tmp_path / "_rendement.jsonl").write_text(
        "\n".join(json.dumps(l, ensure_ascii=False) for l in lignes), encoding="utf-8"
    )
    monkeypatch.setattr(prog._racine, "scripts", lambda: tmp_path)
    assert prog.main([]) == 0
    sortie = capsys.readouterr().out
    assert "Refusées à CHAQUE collecte : apec" in sortie
    assert sortie.index("ats") < sortie.index("apec")  # les plus rentables d'abord


def test_bilan_cumule():
    total = R.bilan(
        [
            {
                "le": "2026-10-19",
                "sources": {"ats": {"ramenees": 3, "nouvelles": 1, "duree": 10, "verdict": "ok"}},
            },
            {
                "le": "2026-10-20",
                "sources": {
                    "ats": {"ramenees": 2, "nouvelles": 0, "duree": 5, "verdict": "limité"}
                },
            },
        ]
    )
    assert total["ats"]["ramenees"] == 5 and total["ats"]["duree"] == 15
    assert total["ats"]["verdicts"] == collections.Counter({"ok": 1, "limité": 1})


def test_fusion_compte_les_nouvelles_par_source(tmp_path, monkeypatch):
    from jobhunter import sources as J

    q = tmp_path / "q.json"
    q.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(J, "QUEUE", q)
    monkeypatch.setattr(J, "REJETS_TRI", tmp_path / "rejets.json")
    entrant = [
        J._mk("Analyste ESG", "https://boards.greenhouse.io/a/jobs/1", "Mirova"),
        J._mk("Chargé de mission RSE", "https://www.linkedin.com/jobs/view/3", "Bpifrance"),
    ]
    entrant[0]["_passe"], entrant[1]["_passe"] = "ats", "linkedin"
    bilan = J.merge_into_queue(entrant, dry=False)
    file = json.loads(q.read_text(encoding="utf-8"))
    assert all("_passe" not in o for o in file)  # l'etiquette ne part pas dans la file
    par = bilan["par_source"]
    assert bilan["added"] >= 1 and set(par) <= {"ats", "linkedin"}
    assert sum(c["nouvelles"] for c in par.values()) == bilan["added"] == len(file)
    assert sum(c["pertinentes"] for c in par.values()) == sum(o["fit"] >= 8 for o in file)
