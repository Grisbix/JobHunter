"""Saved views and columns of the web offers screen (jobhunter.web.saved_views)."""

import json

from jobhunter.web import saved_views as V
from jobhunter.web.api import offres


def test_lire_absent_donne_les_colonnes_par_defaut(tmp_path):
    assert V.lire(tmp_path / "absent.json") == {"vues": {}, "colonnes": V.PAR_DEFAUT}


def test_lire_illisible(tmp_path):
    f = tmp_path / V.FICHIER
    f.write_text("{pas du json", encoding="utf-8")
    assert V.lire(f)["vues"] == {}


def test_enregistrer_garde_seulement_les_filtres_connus(tmp_path):
    f = tmp_path / V.FICHIER
    assert V.enregistrer("ESG 8+", {"zone": "prioritaire", "fit_min": "8", "page": 3, "x": 1}, f)
    # a view saved before 3.31 held one value: it becomes a list of one
    assert V.lire(f)["vues"] == {"ESG 8+": {"zone": ["prioritaire"], "fit_min": 8.0}}


def test_filtres_a_plusieurs_valeurs(tmp_path):
    f = tmp_path / V.FICHIER
    assert V.enregistrer("Europe", {"region": ["Europe", "Asie", ""], "pays": 3}, f)
    assert V.lire(f)["vues"] == {"Europe": {"region": ["Europe", "Asie"]}}
    assert not V.enregistrer("  ", {}, f)


def test_supprimer(tmp_path):
    f = tmp_path / V.FICHIER
    V.enregistrer("a", {"tri": "date"}, f)
    assert V.supprimer("a", f)
    assert not V.supprimer("a", f)


def test_colonnes_dans_l_ordre_du_tableau(tmp_path):
    f = tmp_path / V.FICHIER
    assert V.memoriser_colonnes(["pays", "inconnue", "lieu"], f)
    assert V.lire(f)["colonnes"] == ["lieu", "pays"]
    assert not V.memoriser_colonnes(["inconnue"], f)
    assert not V.memoriser_colonnes("lieu", f)
    V.enregistrer("v", {}, f)
    assert json.loads(f.read_text(encoding="utf-8"))["colonnes"] == ["lieu", "pays"]


def _o(entreprise, lieu, fit=8, **kw):
    return {
        "entreprise": entreprise,
        "poste": "Analyste",
        "fit": fit,
        "localisation": lieu,
        "statut": "Scan 2026-10-25",
        **kw,
    }


def test_offres_filtre_pays_et_region():
    file = [_o("A", "Paris, France"), _o("B", "Berlin, Germany"), _o("C", "New York, NY, USA")]
    tout = offres(file, {})
    assert "Allemagne" in tout["pays"] and tout["regions"]
    assert [x["entreprise"] for x in offres(file, {}, pays="Allemagne")["lignes"]] == ["B"]
    europe = offres(file, {}, region=tout["lignes"][0]["region"])["lignes"]
    assert {x["entreprise"] for x in europe} >= {"A"}


def test_ligne_porte_les_colonnes_du_bureau():
    lig = offres(
        [
            _o(
                "A",
                "Lyon",
                date_publication="2026-10-20",
                ls_check="2026-10-24",
                vu_le="2026-10-22",
                signal="⚠ permis",
            )
        ],
        {},
    )["lignes"][0]
    # found / checked dates are the app's business, not columns (the user, 2026-10-27)
    assert lig["publiee"] == "2026-10-20" and "verifiee" not in lig
    assert lig["alerte"] == "⚠" and lig["pays"] == "France"
