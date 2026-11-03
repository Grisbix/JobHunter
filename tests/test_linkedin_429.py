"""LinkedIn (job_sources.scan_linkedin): a 429 is waited for and resumes the SAME page;
403/999 stop everything; the pass stops cleanly at its maximum duration.

Measurement of 2026-10-17: at 1.2 s between pages, the guest API answered 429 from the
first requests and the code threw away each limited page. Converted from the end of
Scripts/test_ats_readers.py.
"""

import pytest
from conftest import Reponse

from jobhunter import sources as J

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
    """li(*responses, words, places) -> (offers, urls, limit pauses)."""
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
    """The first page took the whole duration: the following keywords are skipped."""
    monkeypatch.setattr(J, "LI_PAUSE", 0)
    monkeypatch.setattr(J, "KEYWORDS", ["esg", "csrd", "isr"])

    def passe_trop_longue(_client, url, **kw):
        faux_reseau.appels.append(url)
        horloge.t += J.LI_DUREE_MAX
        return page()

    monkeypatch.setattr(J, "_get_borne", passe_trop_longue)
    r = J.scan_linkedin(lieux={"France": 1})
    assert (len(r), len(faux_reseau.appels)) == (1, 1)


def test_date_de_publication_de_la_carte(li):
    carte = CARTE_LI.replace(
        "</div></li>",
        '<time class="job-search-card__listdate" datetime="2026-10-08">2 weeks ago</time>'
        "</div></li>",
    )
    offres, _, _ = li(Reponse(carte))
    assert offres and offres[0]["date"] == "2026-10-08"
    assert li(page())[0][0]["date"] == ""  # a card without a date: none invented


# ── The cursor (3.79): the next pass resumes where this one stopped ──────────────
def _mots(appels):
    return [u.split("keywords=")[1].split("&")[0] for u in appels]


def test_la_passe_suivante_reprend_au_mot_coupe(li, faux_reseau):
    li(page(), Reponse("", 403), mots=("esg", "csrd", "isr"))
    faux_reseau.appels.clear()
    li(page(), page(), page(), mots=("esg", "csrd", "isr"))
    assert _mots(faux_reseau.appels) == ["csrd", "isr", "esg"]


def test_un_tour_complet_efface_le_curseur(li, faux_reseau):
    from jobhunter.sources import linkedin

    li(page(), page(), mots=("esg", "csrd"))
    assert linkedin._lire_curseur() is None
    faux_reseau.appels.clear()
    li(page(), page(), mots=("esg", "csrd"))
    assert _mots(faux_reseau.appels) == ["esg", "csrd"]


def test_le_curseur_traverse_les_lieux(li, faux_reseau):
    li(page(), page(), Reponse("", 403), mots=("esg", "csrd"), lieux={"France": 1, "Worldwide": 1})
    faux_reseau.appels.clear()
    li(page(), page(), page(), page(), mots=("esg", "csrd"), lieux={"France": 1, "Worldwide": 1})
    assert [u.split("location=")[1].split("&")[0] for u in faux_reseau.appels][:2] == [
        "Worldwide",
        "Worldwide",
    ]


def test_un_curseur_inconnu_repart_du_debut(li, faux_reseau):
    from jobhunter.sources import linkedin

    linkedin._ecrire_curseur(("Mars", "rien"))
    li(page(), page(), mots=("esg", "csrd"))
    assert _mots(faux_reseau.appels) == ["esg", "csrd"]


def test_une_duree_courte_s_arrete_plus_tot(faux_reseau, horloge, monkeypatch):
    monkeypatch.setattr(J, "LI_PAUSE", 0)
    monkeypatch.setattr(J, "KEYWORDS", ["esg", "csrd", "isr"])

    def page_de_dix_minutes(_client, url, **kw):
        faux_reseau.appels.append(url)
        horloge.t += 600
        return page()

    monkeypatch.setattr(J, "_get_borne", page_de_dix_minutes)
    J.scan_linkedin(lieux={"France": 1}, duree_max=900)
    assert len(faux_reseau.appels) == 2


def test_la_duree_se_regle_en_ligne_de_commande():
    from jobhunter.programs import daily_pipeline
    from jobhunter.sources import cli

    source = open(cli.__file__, encoding="utf-8").read()
    assert '"--linkedin-minutes"' in source and "duree_max=" in source
    pipe = open(daily_pipeline.__file__, encoding="utf-8").read()
    assert '["--linkedin", "--linkedin-minutes", str(LINKEDIN_MINUTES)]' in pipe
    assert daily_pipeline.LINKEDIN_MINUTES * 60 < J.LI_DUREE_MAX


def test_une_page_incomplete_est_la_derniere(li):
    # 1 card < 25: page 2 would be empty, it is not asked for.
    assert len(li(page(), page(), lieux={"France": 3})[1]) == 1


def test_une_page_pleine_demande_la_suivante(li):
    pleine = Reponse(CARTE_LI * 25)
    assert len(li(pleine, page(), lieux={"France": 3})[1]) == 2
