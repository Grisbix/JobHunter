"""Glassdoor facing a refusal of entry, without network (job_sources.scan_glassdoor).

Stop at the first 403, without rest or second request; refusal counted in
INCIDENTS; offers already read kept; a 429 keeps its pause and its second
chance. Converted from Scripts/test_glassdoor_refusal.py, which replaced
time.sleep and urlopen for the whole process without putting them back.
"""

import io
import urllib.error
import urllib.request

import pytest

from jobhunter import sources as js

PAGE = (
    '<a class="x" data-test="job-title" href="https://www.glassdoor.fr/job/{n}">'
    'Analyste ESG junior</a><div data-test="emp-location">Paris</div>'
)
MOTS = [f"mot {i}" for i in range(10)]


@pytest.fixture
def glassdoor(monkeypatch, capsys):
    """Replays a series of responses: an HTTP code raises the error, a text is the page.
    Returns a function scan(responses, words) -> (offers, output, urls_requested, pauses)."""
    pauses = []
    monkeypatch.setattr(js.time, "sleep", pauses.append)

    def scan(reponses, mots=MOTS):
        it = iter(reponses)
        vus = []

        def urlopen(req, timeout=None):
            vus.append(req.full_url)
            x = next(it, 403)
            if isinstance(x, int):
                raise urllib.error.HTTPError("https://www.glassdoor.fr/", x, "refus", {}, None)
            return io.BytesIO(x.encode("utf-8"))

        monkeypatch.setattr(urllib.request, "urlopen", urlopen)
        js.INCIDENTS.clear()
        pauses.clear()
        res = js.scan_glassdoor(mots=mots, pause=12)
        return res, capsys.readouterr().out, vus, list(pauses)

    yield scan
    js.INCIDENTS.clear()


# ── 403 from the first word: immediate stop ────────────────────────────────────
@pytest.fixture
def refus_immediat(glassdoor):
    return glassdoor([403] * 50)


def test_403_une_seule_requete(refus_immediat):
    assert len(refus_immediat[2]) == 1


def test_403_aucun_repos(refus_immediat):
    assert refus_immediat[3] == []


def test_403_annonce_comme_refus(refus_immediat):
    assert "refus d'entree" in refus_immediat[1]


def test_403_compte_dans_incidents(refus_immediat):
    assert js.INCIDENTS["glassdoor"].get("HTTP 403") == 1


def test_403_rien_collecte_sans_exception(refus_immediat):
    assert refus_immediat[0] == []


# ── 403 after successes: the offers read are kept ────────────────────────
@pytest.fixture
def refus_au_troisieme(glassdoor):
    return glassdoor([PAGE.format(n=1), PAGE.format(n=2), 403])


def test_403_au_3e_mot_trois_requetes(refus_au_troisieme):
    assert len(refus_au_troisieme[2]) == 3


def test_403_au_3e_mot_offres_lues_conservees(refus_au_troisieme):
    assert len(refus_au_troisieme[0]) == 2


def test_403_au_3e_mot_pas_de_repos_de_45s(refus_au_troisieme):
    assert js.GD_REPOS not in refus_au_troisieme[3]


# ── a 429 stays a rate limit: pause then second chance ───────────────
def test_429_repos_avant_seconde_chance(glassdoor):
    assert js.GD_REPOS in glassdoor([429, PAGE.format(n=3)], MOTS[:1])[3]


def test_429_seconde_requete_offre_lue(glassdoor):
    res, _, vus, _ = glassdoor([429, PAGE.format(n=3)], MOTS[:1])
    assert (len(vus), len(res)) == (2, 1)


# ── persistent 429: stop after GD_ABANDON refusals in a row ────────────────────
def test_429_persistant_arret(glassdoor):
    assert len(glassdoor([429] * 100)[2]) == 2 * js.GD_ABANDON


def test_429_persistant_compte_dans_incidents(glassdoor):
    glassdoor([429] * 100)
    assert js.INCIDENTS["glassdoor"].get("HTTP 429") == js.GD_ABANDON
