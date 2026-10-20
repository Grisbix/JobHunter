"""Network failure matrix of the ATS and career-feed readers, without network.

Every reader of `fetch_ats` and `fetch_autre` meets each failure: refusal (403), rate
limit (429), server error (500), timeout, and, for the JSON readers, an empty or
unreadable body. For each one: no exception escapes, no offer is invented, and the
failure is COUNTED in INCIDENTS — an unavailable source must never look like a calm
day with nothing to take (ADR 0004). A 404 stays silent: the account no longer exists.
"""

import httpx
import pytest
from conftest import Reponse

from jobhunter import sources as J
from jobhunter.sources import ats as _ats

ATS = ["greenhouse", "lever", "ashby", "recruitee", "teamtailor", "smartrecruiters"]
AUTRES = {
    "workable": "x",
    "pinpoint": "x",
    "sitemap": "https://x.org/sitemap.xml",
    "peoplesoft": "x/psc/hr/X/CAREERS",
    "gogenerali": "x",
    "adb": "x",
    "icims": "x.icims.com",
    "eightfold": "x.eightfold.ai|x.com",
    "sfrss": "x",
    "talentsoft": "x",
    "phenom": "x",
    "jibe": "x",
    "talentbrew": "x|1",
    "avature": "x",
    "csod": "x",
    "oracle": "x|y",
}
# Readers whose answer is JSON: an empty or HTML body is a failure, not an empty list.
JSON = [
    "greenhouse",
    "lever",
    "ashby",
    "recruitee",
    "smartrecruiters",
    "workable",
    "pinpoint",
    "gogenerali",
    "eightfold",
    "jibe",
    "csod",
    "oracle",
]
PANNES = {"403": ("", 403), "429": ("", 429), "500": ("", 500), "delai": None}


@pytest.fixture
def lire(monkeypatch):
    monkeypatch.setattr(J, "WORKDAY_MOTS", ["esg"])
    monkeypatch.setattr(J, "WORKDAY_PAUSE", 0)
    monkeypatch.setattr(_ats.time, "sleep", lambda _s: None)

    def faire(kind, reponse):
        def envoi(_httpx, url, **_kw):
            if reponse is None:
                raise httpx.ReadTimeout("délai dépassé")
            return Reponse(*reponse)

        monkeypatch.setattr(J, "_get_borne", envoi)
        monkeypatch.setattr(J, "_post_borne", envoi)
        J.INCIDENTS.clear()
        if kind in ATS:
            offres = J.fetch_ats(kind, "x")
        else:
            offres = J.fetch_autre(kind, AUTRES[kind], "Societe")
        return offres, sum(sum(d.values()) for d in J.INCIDENTS.values())

    yield faire
    J.INCIDENTS.clear()


@pytest.mark.parametrize("panne", PANNES)
@pytest.mark.parametrize("kind", ATS + list(AUTRES))
def test_une_panne_est_comptee(lire, kind, panne):
    offres, incidents = lire(kind, PANNES[panne])
    assert offres == []
    assert incidents >= 1


@pytest.mark.parametrize("corps", ["", "<html>pas du json</html>"])
@pytest.mark.parametrize("kind", JSON)
def test_un_json_vide_ou_illisible_est_compte(lire, kind, corps):
    offres, incidents = lire(kind, (corps, 200))
    assert offres == []
    assert incidents >= 1


@pytest.mark.parametrize("kind", ["greenhouse", "workable", "peoplesoft"])
def test_un_404_reste_silencieux(lire, kind):
    assert lire(kind, ("", 404)) == ([], 0)
