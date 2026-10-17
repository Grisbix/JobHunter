"""LinkedIn (job_sources.scan_linkedin) : un 429 s'attend et reprend la MEME page ;
403/999 arretent tout ; la passe s'arrete proprement a sa duree maximale.

Mesure du 2026-10-17 : a 1,2 s entre pages, l'API invite repondait 429 des les
premieres requetes et le code jetait chaque page limitee. Converti depuis la fin de
Scripts/test_lecteurs_ats.py.
"""

import pytest
from conftest import Reponse

import job_sources as J

CARTE_LI = (
    '<li><div class="base-card"><a href="https://fr.linkedin.com/jobs/view/42?trk=x">'
    '<span class="sr-only">Sustainable Finance Analyst</span></a>'
    '<h4 class="base-search-card__subtitle"><a>Societe</a></h4>'
    '<span class="job-search-card__location">Paris</span></div></li>'
)


def page():
    return Reponse(CARTE_LI)


def limite(retry_after=None):
    return Reponse("", 429, {"Retry-After": retry_after} if retry_after else None)


@pytest.fixture
def li(faux_reseau, horloge, monkeypatch):
    """li(*reponses, mots, lieux) -> (offres, urls, pauses de limite)."""
    monkeypatch.setattr(J, "LI_PAUSE", 0)

    def faire(*reponses, mots=("esg",), lieux=None):
        monkeypatch.setattr(J, "KEYWORDS", list(mots))
        faux_reseau.sequence(*reponses)
        r = J.scan_linkedin(lieux=lieux or {"France": 1})
        return r, faux_reseau.appels, [p for p in horloge.pauses if p]

    return faire


@pytest.fixture
def une_limite(li):
    return li(limite(), page())


def test_429_page_redemandee_apres_la_pause(une_limite):
    assert (len(une_limite[0]), len(une_limite[1])) == (1, 2)


def test_429_pause_de_60s_sans_retry_after(une_limite):
    assert une_limite[2] == [60]


def test_429_compte_en_incident(une_limite):
    assert dict(J.INCIDENTS["linkedin_http"]) == {429: 1}


@pytest.mark.parametrize(
    ("entete", "pause"), [("7", 7), ("86400", 240)], ids=["respecte", "plafonne"]
)
def test_429_retry_after(li, entete, pause):
    assert li(limite(entete), page())[2] == [pause]


def test_429_pauses_doublees(li):
    assert li(limite(), limite(), page())[2] == [60, 120]


@pytest.fixture
def persistante(li, horloge):
    r = li(limite(), mots=("esg", "csrd", "isr"))
    return r, sum(horloge.pauses)


def test_429_persistant_arret_a_la_duree_max(persistante):
    assert persistante[1] <= J.LI_DUREE_MAX


def test_429_persistant_attente_avant_abandon(persistante):
    assert persistante[1] > J.LI_DUREE_MAX - 240


def test_429_persistant_plus_aucun_mot_cle(persistante):
    assert all("keywords=esg" in u for u in persistante[0][1])


def test_999_une_seule_requete_aucune_pause(li):
    _, urls, pauses = li(
        Reponse("", 999), mots=("esg", "csrd", "isr"), lieux={"France": 2, "Worldwide": 2}
    )
    assert (len(urls), pauses) == (1, [])


def test_403_arret_immediat(li):
    assert len(li(Reponse("", 403), mots=("esg", "csrd"))[1]) == 1


def test_compteur_de_pauses_repart_apres_une_page(li):
    assert li(limite(), page(), limite(), page(), mots=("esg", "csrd"))[2] == [60, 60]


def test_sans_incident_aucune_pause(li):
    assert li(page())[2] == []


def test_duree_max_depassee_sans_429(faux_reseau, horloge, monkeypatch):
    """La premiere page a pris toute la duree : les mots-cles suivants sont sautes."""
    monkeypatch.setattr(J, "LI_PAUSE", 0)
    monkeypatch.setattr(J, "KEYWORDS", ["esg", "csrd", "isr"])

    def passe_trop_longue(_client, url, **kw):
        faux_reseau.appels.append(url)
        horloge.t += J.LI_DUREE_MAX
        return page()

    monkeypatch.setattr(J, "_get_borne", passe_trop_longue)
    r = J.scan_linkedin(lieux={"France": 1})
    assert (len(r), len(faux_reseau.appels)) == (1, 1)
