"""Where an offer was seen, what its site changed, and views that follow the queue.

Ideas 1, 9 and 14 of the architecture notes of 2026-10-20: keep every source that
served a posting, record what the same site changes in it (never replacing a value),
and reload the table when another program writes the queue.
"""

from types import SimpleNamespace

import pytest

from jobhunter import sources as J
from jobhunter.app import data as D
from jobhunter.sources import merge as M
from jobhunter.storage import atomic as atomique
from jobhunter.storage import queue as queue_io


def test_noter_source_garde_la_premiere_et_sans_doublon():
    x = {"source": "linkedin-search:analyste esg"}
    M.noter_source(x, "workday:pwc")
    M.noter_source(x, "workday:pwc")
    M.noter_source(x, "")
    assert x["vus_sur"] == ["linkedin-search:analyste esg", "workday:pwc"]


def test_noter_source_borne():
    x: dict = {}
    for i in range(M.MAX_VUS_SUR + 5):
        M.noter_source(x, f"s:{i}")
    assert len(x["vus_sur"]) == M.MAX_VUS_SUR


def test_changement_du_meme_site_note_une_seule_fois():
    x = {"source": "adzuna:fr", "poste": "Analyste ESG", "salaire": "40 k€", "contrat": "CDI"}
    o = {"source": "adzuna:fr", "titre": "Analyste ESG", "salaire": "45 k€", "contrat": "CDI"}
    assert M.changements(x, o, "2026-10-21") == [
        {"date": "2026-10-21", "champ": "salaire", "avant": "40 k€", "apres": "45 k€"}
    ]
    assert M.changements(x, o, "2026-10-22") == []  # the same new value, the next day
    assert x["salaire"] == "40 k€"  # recorded, not replaced
    assert len(x["changements"]) == 1


@pytest.mark.parametrize(
    "o",
    [
        # another site: its wording is not a change
        {"source": "glassdoor", "titre": "ESG Analyst", "salaire": "50 k€"},
        # nothing said, or "non precise"
        {"source": "adzuna:fr", "titre": "Analyste ESG", "contrat": "non precise"},
        # the same place, said more precisely
        {"source": "adzuna:fr", "titre": "Analyste ESG", "location": "Paris, Ile-de-France"},
        # case and spaces only
        {"source": "adzuna:fr", "titre": "analyste  esg"},
    ],
)
def test_pas_de_faux_changement(o):
    x = {"source": "adzuna:fr", "poste": "Analyste ESG", "localisation": "Paris", "contrat": "CDI"}
    assert M.changements(x, o, "2026-10-21") == []
    assert "changements" not in x


def test_comparaison_avec_la_source_d_avant_la_promotion():
    # The offer came from LinkedIn and a better link (Workday) just replaced it:
    # Workday's wording is compared with nothing, not with LinkedIn's.
    x = {"source": "workday:pwc", "poste": "Analyste ESG", "salaire": "40 k€"}
    o = {"source": "workday:pwc", "titre": "Analyste ESG", "salaire": "45 k€"}
    assert M.changements(x, o, "2026-10-21", source_x="linkedin-search:esg") == []


@pytest.fixture
def file_de_fusion(tmp_path, monkeypatch, suivi_temporaire):
    q = tmp_path / "q.json"
    monkeypatch.setattr(J, "QUEUE", q)
    monkeypatch.setattr(J, "REJETS_TRI", tmp_path / "rej.json")
    return q


def test_fusion_garde_les_provenances_et_les_changements(file_de_fusion):
    url = "https://www.adzuna.fr/details/42"
    atomique.ecrire_json(
        file_de_fusion,
        [
            {
                "entreprise": "Mirova",
                "poste": "Analyste ESG",
                "url": url,
                "source": "adzuna:fr",
                "salaire": "40 k€",
                "statut": "Scan x",
            }
        ],
    )
    meme_site = J._mk("Analyste ESG", url, "Mirova", location="Paris", source="adzuna:fr")
    meme_site["salaire"] = "45 k€"
    autre = J._mk(
        "Analyste ESG",
        "https://www.linkedin.com/jobs/view/7",
        "Mirova",
        source="linkedin-search:esg",
    )
    bilan = J.merge_into_queue([meme_site, autre], dry=False)
    (o,) = queue_io.charger(file_de_fusion)
    assert o["vus_sur"] == ["adzuna:fr", "linkedin-search:esg"]
    assert [c["champ"] for c in o["changements"]] == ["salaire"]
    assert o["salaire"] == "40 k€"
    assert bilan["modifiees"] == 1


class _Vue:
    """What the queue watcher uses of the application."""

    def __init__(self, f):
        self.f = f
        self.proc = None
        self.journal: list[str] = []
        self.charges = 0
        self.focus = None
        self.root = SimpleNamespace(after=lambda *a: None, focus_get=lambda: self.focus)

    def _surveiller_file(self):
        pass  # the next check, scheduled by root.after

    def _empreinte_donnees(self):
        return (self.f.stat().st_mtime_ns,)

    def _log(self, t):
        self.journal.append(t)

    def load_offers(self):
        self.charges += 1
        self._empreinte_file = self._empreinte_donnees()


def test_la_vue_suit_la_file(tmp_path):
    f = tmp_path / "q.json"
    f.write_text("[]", encoding="utf-8")
    v = _Vue(f)
    v.load_offers()
    D.DonneesMixin._surveiller_file(v)
    assert v.charges == 1  # nothing changed
    f.write_text("[{}]", encoding="utf-8")
    import os

    os.utime(f, ns=(1, v._empreinte_file[0] + 10**9))
    v.focus = SimpleNamespace(winfo_class=lambda: "Entry")
    D.DonneesMixin._surveiller_file(v)
    assert v.charges == 1  # the user is typing: later
    v.focus = None
    D.DonneesMixin._surveiller_file(v)
    assert v.charges == 2 and v.journal
