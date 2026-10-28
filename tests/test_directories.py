"""3.51: the country's large employers from open directories (Wikidata, SIRENE)."""

from jobhunter.sources import directories as d
from jobhunter.storage import companies


def _b(nom, emp, site="", ind=""):
    x = {"cLabel": {"value": nom}, "emp": {"value": str(emp)}}
    if site:
        x["site"] = {"value": site}
    if ind:
        x["ind"] = {"value": ind}
    return x


def test_lignes_wikidata():
    rep = {
        "results": {
            "bindings": [
                _b("Example Bank", 50000, "https://bank.example", "banking|financial services"),
                _b("Example Bank", 50000, "https://bank.example/de"),  # same company again
                _b("Q123456", 900),  # no label in these languages
                _b("Sample Hospital", 8000, ind="hospitals and rehabilitation"),
            ]
        }
    }
    out = d.lignes_wikidata(rep)
    assert [e["nom"] for e in out] == ["Example Bank", "Sample Hospital"]
    assert out[0]["effectif"] == 50000 and out[0]["site_web"] == "https://bank.example"
    assert out[0]["secteurs"] == ["banking", "financial services"]


def test_lignes_sirene():
    rep = {"results": [{"nom_raison_sociale": "EXEMPLE SA", "activite_principale": "64.19Z"}]}
    assert d.lignes_sirene(rep)[0]["nom"] == "EXEMPLE SA"


def test_filtre_des_familles():
    mots, sections = d.filtre(["finance", "rse"])
    assert "bank" in mots and "energy" in mots
    assert sections == "KDEM"
    # A legal or sales profile works in every industry.
    assert d.filtre(["juridique"]) is None
    assert d.filtre([]) is None


def test_du_secteur_garde_le_metier_puis_l_inconnu():
    entreprises = [
        {"nom": "Inconnue", "secteurs": [], "source": "wikidata"},
        {"nom": "Carmaker", "secteurs": ["automotive industry"], "source": "wikidata"},
        {"nom": "Hospital", "secteurs": ["hospitals and rehabilitation"], "source": "wikidata"},
        {"nom": "SIRENE SA", "secteurs": ["86.10Z"], "source": "sirene"},
    ]
    f = d.filtre(["sante"])
    assert [e["nom"] for e in d.du_secteur(entreprises, f)] == ["Hospital", "SIRENE SA", "Inconnue"]
    assert len(d.du_secteur(entreprises, None)) == 4


def test_ajouter_annuaire(tmp_path):
    q = tmp_path / "apply_queue.json"
    companies.noter(
        q, [{"entreprise": "Example Bank", "source": "linkedin-search:x"}], "2026-10-01"
    )
    n = companies.ajouter_annuaire(
        q,
        [
            {"nom": "example bank", "site_web": "https://bank.example", "effectif": 50000,
             "source": "wikidata"},
            {"nom": "Sample Hospital", "site_web": "", "effectif": 8000, "source": "wikidata"},
        ],
        "2026-10-28",
    )  # fmt: skip
    reg = companies.charger(q)
    assert n == 1
    assert reg["example bank"]["site_web"] == "https://bank.example"
    assert reg["example bank"]["sites"] == ["linkedin", "wikidata"]
    # Never seen in a collection: no « dernière vue », asked after the companies seen.
    assert "derniere_vue" not in reg["sample hospital"]


def test_les_entreprises_vues_d_abord(monkeypatch):
    from jobhunter.sources import company_sites as cs

    monkeypatch.setattr(cs, "_suivis", lambda: (set(), set()))
    reg = {
        "annuaire": {"nom": "Annuaire", "premiere_vue": "2026-10-28", "sites": ["wikidata"]},
        "vue": {"nom": "Vue", "premiere_vue": "2026-10-20", "derniere_vue": "2026-10-27"},
    }
    lot = cs.a_demander(reg, {}, "2026-10-28", 2, {})
    assert [e["_cle"] for e in lot] == ["vue", "annuaire"]
