"""Sources for a profile outside finance (measured 2026-10-24, aerospace engineer).

- eFC and FIR only list finance and ESG jobs: skipped when the title filter keeps
  no finance title, kept for the reference profile.
- A company feed guessed from the name is followed only when it holds one of the
  offers already seen at that company ("aura" is not AURA-AERO).
"""

from jobhunter.programs import probe_ats_queue as pq
from jobhunter.sources import cli
from jobhunter.sources import common as _commun


def test_profil_de_reference_vise_la_finance():
    assert cli._vise_finance()


def test_profil_ingenieur_ne_vise_pas_la_finance(monkeypatch):
    monkeypatch.setattr(_commun, "title_ok", lambda t: "ingénieur" in t.lower())
    assert not cli._vise_finance()


def test_flux_confirme_par_une_offre_deja_vue():
    vus = pq.titres_par_entreprise(
        [
            {"entreprise": "AURA-AERO", "poste": "Ingénieur  Structure"},
            {"entreprise": "Relativity Space", "poste": "Structural Analysis Engineer II"},
        ]
    )
    assert pq.confirme(
        ["Structural Analysis Engineer II", "Weld Engineer"], vus["Relativity Space"]
    )
    assert not pq.confirme(["Senior Software Engineer, Device Platform"], vus["AURA-AERO"])
    assert pq.confirme(["ingénieur structure"], vus["AURA-AERO"])  # case and blanks


def test_ajouter_les_flux_confirmes(monkeypatch, tmp_path):
    import json

    monkeypatch.setattr(pq, "HERE", tmp_path)
    (tmp_path / "sources_config.json").write_text('{"ats_slugs": {}}', encoding="utf-8")
    r = {"ats": "greenhouse", "slug": "relativity", "entreprise": "Relativity Space"}
    pq.ajouter([r])
    pq.ajouter([r])  # twice: followed once
    cfg = json.loads((tmp_path / "sources_config.json").read_text(encoding="utf-8"))
    assert cfg["ats_slugs"] == {"greenhouse": ["relativity"]}
