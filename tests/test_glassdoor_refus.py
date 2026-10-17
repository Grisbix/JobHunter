"""Glassdoor face a un refus d'entree, sans reseau (job_sources.scan_glassdoor).

Arret au premier 403, sans repos ni seconde requete ; refus compte dans
INCIDENTS ; offres deja lues conservees ; un 429 garde sa pause et sa seconde
chance. Converti depuis Scripts/test_glassdoor_refus.py, qui remplacait
time.sleep et urlopen pour tout le processus sans les remettre en place.
"""

import io
import urllib.error
import urllib.request

import pytest

import job_sources as js

PAGE = (
    '<a class="x" data-test="job-title" href="https://www.glassdoor.fr/job/{n}">'
    'Analyste ESG junior</a><div data-test="emp-location">Paris</div>'
)
MOTS = [f"mot {i}" for i in range(10)]


@pytest.fixture
def glassdoor(monkeypatch, capsys):
    """Rejoue une suite de reponses : un code HTTP leve l'erreur, un texte est la page.
    Rend une fonction scan(reponses, mots) -> (offres, sortie, urls_demandees, pauses)."""
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


# ── 403 des le premier mot : arret immediat ────────────────────────────────────
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


# ── 403 apres des succes : les offres lues sont gardees ────────────────────────
@pytest.fixture
def refus_au_troisieme(glassdoor):
    return glassdoor([PAGE.format(n=1), PAGE.format(n=2), 403])


def test_403_au_3e_mot_trois_requetes(refus_au_troisieme):
    assert len(refus_au_troisieme[2]) == 3


def test_403_au_3e_mot_offres_lues_conservees(refus_au_troisieme):
    assert len(refus_au_troisieme[0]) == 2


def test_403_au_3e_mot_pas_de_repos_de_45s(refus_au_troisieme):
    assert js.GD_REPOS not in refus_au_troisieme[3]


# ── un 429 reste une limite de debit : pause puis seconde chance ───────────────
def test_429_repos_avant_seconde_chance(glassdoor):
    assert js.GD_REPOS in glassdoor([429, PAGE.format(n=3)], MOTS[:1])[3]


def test_429_seconde_requete_offre_lue(glassdoor):
    res, _, vus, _ = glassdoor([429, PAGE.format(n=3)], MOTS[:1])
    assert (len(vus), len(res)) == (2, 1)


# ── 429 persistant : arret apres GD_ABANDON refus d'affilee ────────────────────
def test_429_persistant_arret(glassdoor):
    assert len(glassdoor([429] * 100)[2]) == 2 * js.GD_ABANDON


def test_429_persistant_compte_dans_incidents(glassdoor):
    glassdoor([429] * 100)
    assert js.INCIDENTS["glassdoor"].get("HTTP 429") == js.GD_ABANDON
