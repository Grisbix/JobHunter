"""Sources Adzuna et Jooble (API officielles), sans reseau.

Sans cle la source se tait et le dit ; un refus d'entree arrete au 3e ; un 429 fait
une pause puis reprend ; la cle ne fuit JAMAIS dans la sortie, meme dans une
exception. Converti depuis Scripts/test_agregateurs.py.
"""

import json

import pytest

import job_sources as js

CLE = "CLE-SECRETE-123"


class R:
    def __init__(self, code, data=None):
        self.status_code, self._d = code, data or {}

    def json(self):
        return self._d


@pytest.fixture
def agreg(monkeypatch, tmp_path, capsys):
    """Rend scan(fonction, reponses) -> (offres, sortie, appels, pauses).
    Les cles sont dans des fichiers jetables ; sans `cles`, ils n'existent pas."""
    pauses = []
    monkeypatch.setattr(js.time, "sleep", pauses.append)
    monkeypatch.setattr(js, "ADZUNA_CFG", tmp_path / "adzuna.json")
    monkeypatch.setattr(js, "JOOBLE_CFG", tmp_path / "jooble.json")

    def scan(fonction, reponses=(), cles=True):
        if cles:
            js.ADZUNA_CFG.write_text(json.dumps({"app_id": "ID", "app_key": CLE}), encoding="utf-8")
            js.JOOBLE_CFG.write_text(json.dumps({"key": CLE}), encoding="utf-8")
        it = iter(reponses)
        appels = []

        def appel(_envoi, url, **kw):
            appels.append((url, kw))
            x = next(it, R(200, {}))
            if isinstance(x, Exception):
                raise x
            return x

        monkeypatch.setattr(js, "_get_borne", appel)
        monkeypatch.setattr(js, "_post_borne", appel)
        js.INCIDENTS.clear()
        pauses.clear()
        res = fonction()
        return res, capsys.readouterr().out, appels, list(pauses)

    yield scan
    js.INCIDENTS.clear()


# ── sans cle : la source se tait et le dit ─────────────────────────────────────
def test_adzuna_sans_cle_aucune_offre(agreg):
    assert agreg(js.scan_adzuna, cles=False)[0] == []


def test_adzuna_sans_cle_le_dit(agreg):
    assert "adzuna.json absent" in agreg(js.scan_adzuna, cles=False)[1]


def test_jooble_sans_cle(agreg):
    res, sortie, _, _ = agreg(js.scan_jooble, cles=False)
    assert res == [] and "jooble.json absent" in sortie


# ── Adzuna : lecture et filtres ────────────────────────────────────────────────
PAGE = {
    "results": [
        {
            "title": "ESG Analyst",
            "redirect_url": "https://www.adzuna.fr/land/ad/1",
            "company": {"display_name": "Mirova"},
            "location": {"display_name": "Paris"},
            "created": "2026-10-01T08:00:00Z",
            "description": "<b>SFDR</b> reporting",
            "contract_type": "permanent",
        },
        {
            "title": "Stage analyste ESG",
            "redirect_url": "https://www.adzuna.fr/land/ad/2",
            "company": {"display_name": "X"},
            "location": {},
        },
        {
            "title": "Chauffeur livreur",
            "redirect_url": "https://www.adzuna.fr/land/ad/3",
            "company": {"display_name": "Y"},
            "location": {},
        },
    ]
}


@pytest.fixture
def adzuna(agreg):
    return agreg(js.scan_adzuna, [R(200, PAGE)])


def test_adzuna_offre_esg_lue(adzuna):
    assert len(adzuna[0]) == 1 and adzuna[0][0]["titre"] == "ESG Analyst"


def test_adzuna_stage_et_hors_metier_ecartes(adzuna):
    assert len(adzuna[0]) == 1


def test_adzuna_permanent_devient_cdi(adzuna):
    assert adzuna[0][0].get("contrat") == "CDI"


def test_adzuna_extrait_partiel_sans_html(adzuna):
    o = adzuna[0][0]
    assert o.get("desc_partielle") and "<b>" not in o["description"]


def test_adzuna_date_courte(adzuna):
    assert adzuna[0][0]["date"] == "2026-10-01"


def test_adzuna_france_puis_pays(adzuna):
    attendu = len(js.AGREG_MOTS_FR) + len(js.ADZUNA_PAYS) * len(js.AGREG_MOTS_EN)
    assert len(adzuna[2]) == attendu


def test_adzuna_cle_absente_de_la_sortie(adzuna):
    assert CLE not in adzuna[1]


# ── refus d'entree : arret au 3e ───────────────────────────────────────────────
@pytest.fixture
def refus(agreg):
    return agreg(js.scan_adzuna, [R(403)] * 20)


def test_adzuna_403_arret(refus):
    assert len(refus[2]) == js.AGREG_ABANDON


def test_adzuna_403_le_dit(refus):
    assert "refus d'affilee" in refus[1]


# ── limite de debit : pause, reprise, puis abandon ─────────────────────────────
@pytest.fixture
def limite(agreg):
    return agreg(js.scan_adzuna, [R(429), R(200, PAGE)] + [R(429)] * 5)


def test_adzuna_429_pause(limite):
    assert js.AGREG_REPOS_429 in limite[3]


def test_adzuna_429_reprise(limite):
    assert len(limite[0]) == 1


def test_adzuna_429_persistant_arret(limite):
    assert "limite de debit persistante" in limite[1]


# ── la cle ne fuit jamais, meme dans une exception ─────────────────────────────
@pytest.fixture
def exception(agreg):
    erreur = RuntimeError(f"echec sur https://api.adzuna.com/?app_key={CLE}")
    return agreg(js.scan_adzuna, [erreur] * 80)


def test_exception_cle_absente_de_la_sortie(exception):
    assert CLE not in exception[1]


def test_exception_comptee_par_son_type(exception):
    assert js.INCIDENTS["adzuna"].get("RuntimeError", 0) > 0


# ── Jooble ─────────────────────────────────────────────────────────────────────
PAGE_JOOBLE = {
    "jobs": [
        {
            "title": "Analyste crédit junior",
            "link": "https://jooble.org/desc/9",
            "company": "BNP",
            "location": "Paris",
            "snippet": "crédit corporate",
            "type": "CDI",
            "updated": "2026-09-30T00:00:00",
        }
    ]
}


@pytest.fixture
def jooble(agreg):
    return agreg(js.scan_jooble, [R(200, PAGE_JOOBLE)])


def test_jooble_offre_lue(jooble):
    assert len(jooble[0]) == 1 and jooble[0][0]["entreprise"] == "BNP"


def test_jooble_type_cdi_repris(jooble):
    assert jooble[0][0].get("contrat") == "CDI"


def test_jooble_post_avec_france(jooble):
    assert jooble[2][0][1].get("json", {}).get("location") == "France"


def test_jooble_cle_absente_de_la_sortie(jooble):
    assert CLE not in jooble[1]
