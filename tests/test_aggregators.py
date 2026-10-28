"""Adzuna and Jooble sources (official APIs), without network.

Without a key the source stays silent and says so; a refusal of entry stops at the 3rd; a 429 pauses
then resumes; the key NEVER leaks into the output, even in an
exception. Converted from Scripts/test_aggregators.py.
"""

import json

import pytest

from jobhunter import sources as js

CLE = "CLE-SECRETE-123"


class R:
    def __init__(self, code, data=None):
        self.status_code, self._d = code, data or {}

    def json(self):
        return self._d


@pytest.fixture
def agreg(monkeypatch, tmp_path, capsys):
    """Returns scan(function, responses) -> (offers, output, calls, pauses).
    The keys are in throwaway files; without `cles`, they do not exist."""
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


# ── without a key: the source stays silent and says so ─────────────────────────────────────
def test_adzuna_sans_cle_aucune_offre(agreg):
    assert agreg(js.scan_adzuna, cles=False)[0] == []


def test_adzuna_sans_cle_le_dit(agreg):
    assert "adzuna.json absent" in agreg(js.scan_adzuna, cles=False)[1]


def test_jooble_sans_cle(agreg):
    res, sortie, _, _ = agreg(js.scan_jooble, cles=False)
    assert res == [] and "jooble.json absent" in sortie


# ── Adzuna: reading and filters ────────────────────────────────────────────────
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


# ── refusal of entry: stop at the 3rd ───────────────────────────────────────────────
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


# ── the key never leaks, even in an exception ─────────────────────────────
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


# ── freehire (public API, no key) ─────────────────────────────────────────────
PAGE_FREEHIRE = {
    "data": [
        {
            "title": "Analyste ESG",
            "url": "https://boards.greenhouse.io/alpha/jobs/1?gh_jid=1&utm_source=freehire.me",
            "company": "Alpha",
            "location": "Paris, FR",
            "description": "<p>Analyse ESG des émetteurs</p>",
            "posted_at": "2026-10-20T08:00:00Z",
            "source": "greenhouse",
        },
        {
            "title": "Chargé RSE",
            "url": "https://x.wd3.myworkdayjobs.com/fr/job/2?utm_source=freehire.me",
            "company": "x.wd3.myworkdayjobs.com/",
            "location": "Lyon",
            "description": "",
            "source": "workday",
        },
    ]
}


@pytest.fixture
def freehire(agreg):
    return agreg(js.scan_freehire, [R(200, PAGE_FREEHIRE)])


def test_freehire_lien_de_l_entreprise_sans_marqueur(freehire):
    urls = [o["url"] for o in freehire[0]]
    assert urls[0] == "https://boards.greenhouse.io/alpha/jobs/1?gh_jid=1"
    assert all("utm_source" not in u for u in urls)


def test_freehire_offre_et_provenance(freehire):
    o = freehire[0][0]
    assert (o["entreprise"], o["source"]) == ("Alpha", "freehire:greenhouse")
    assert freehire[0][1]["entreprise"] == "x.wd3.myworkdayjobs.com"
    assert o.get("desc_partielle")


@pytest.fixture
def sans_config(monkeypatch, tmp_path):
    from jobhunter.sources import common

    monkeypatch.setattr(common, "SOURCES_CFG", tmp_path / "sources_config.json")
    return common.SOURCES_CFG


def test_freehire_monde_30_jours_et_projet_nomme(sans_config, agreg):
    _, _, appels, _ = agreg(js.scan_freehire, [R(200, PAGE_FREEHIRE)])
    url, kw = appels[0]
    assert url == js.freehire.API
    assert "countries" not in kw["params"] and kw["params"]["posted_within_days"] == 30
    assert "JobHunter" in kw["headers"]["User-Agent"]


def test_freehire_pays_choisis(sans_config, agreg):
    sans_config.write_text(
        json.dumps({"freehire_pays": ["DE", "ch", "x", "fra"]}), encoding="utf-8"
    )
    _, _, appels, _ = agreg(js.scan_freehire, [R(200, PAGE_FREEHIRE)])
    assert appels[0][1]["params"]["countries"] == ["de", "ch"]


# ── Bundesagentur für Arbeit (public Jobsuche API, v6) ───────────────────────
PAGE_BA = {
    "ergebnisliste": [
        {
            "stellenangebotsTitel": "Senior Manager ESG (m/w/d)",
            "firma": "Alpha Wohnen GmbH",
            "referenznummer": "14012-ABC/1-S",
            "hauptberuf": "ESG-Manager/in",
            "datumErsteVeroeffentlichung": "2026-10-20",
            "stellenlokationen": [{"adresse": {"ort": "Frankfurt am Main", "land": "DEUTSCHLAND"}}],
        },
        {
            "stellenangebotsTitel": "ESG Specialist (m/w/d)",
            "firma": "Beta AG",
            "referenznummer": "10001-2-S",
            "stellenlokationen": [{"adresse": {"ort": "Salzburg", "land": "OESTERREICH"}}],
        },
        {"stellenangebotsTitel": "Sans référence", "firma": "Gamma"},
    ]
}


def test_arbeitsagentur_offres_lien_et_lieu(agreg):
    offres, _, appels, _ = agreg(js.scan_arbeitsagentur, [R(200, PAGE_BA)])
    assert [o["entreprise"] for o in offres] == ["Alpha Wohnen GmbH", "Beta AG"]
    assert offres[0]["url"] == js.arbeitsagentur.FICHE + "14012-ABC%2F1-S"
    assert offres[0]["location"] == "Frankfurt am Main, Deutschland"
    assert offres[1]["location"] == "Salzburg, Österreich"
    url, kw = appels[0]
    assert url == js.arbeitsagentur.API and kw["params"]["angebotsart"] == 1
    assert (
        kw["headers"]["X-API-Key"] == "jobboerse-jobsuche"
        and "JobHunter" in kw["headers"]["User-Agent"]
    )
    assert len(appels) == len(js.arbeitsagentur.MOTS)  # one request per keyword


def test_arbeitsagentur_refus_arrete(agreg):
    offres, _, appels, _ = agreg(js.scan_arbeitsagentur, [R(403)] * 20)
    assert offres == [] and len(appels) < len(js.arbeitsagentur.MOTS)


def test_freehire_page_courte_pas_de_page_suivante(freehire):
    # 2 offers < 50: one request per word searched, never a second page
    from jobhunter.sources import keywords

    assert len(freehire[2]) == len(
        keywords.mots("freehire", js.freehire.MOTS, len(js.freehire.MOTS))
    )


def test_freehire_429_attend_puis_s_arrete(agreg):
    offres, _, appels, pauses = agreg(js.scan_freehire, [R(429)] * 5)
    assert offres == [] and len(pauses) >= 2
    assert js.INCIDENTS["freehire"]["HTTP 429"] == 3
