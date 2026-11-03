"""3.71: collection compliance found by the audit of 2026-10-29.

Retry-After read as seconds or HTTP date; refusals (403/999) stop instead of being
asked again; odd answers no longer crash a source.
"""

import email.utils
import time

from jobhunter import network
from jobhunter.programs import linkedin_desc
from jobhunter.sources import vie


def test_retry_after_secondes_et_date():
    assert network.retry_after("120", 5) == 120
    assert network.retry_after(None, 5) == 5
    assert network.retry_after("n'importe quoi", 7) == 7
    dans_90 = email.utils.formatdate(time.time() + 90, usegmt=True)
    assert 80 <= network.retry_after(dans_90, 5) <= 91
    passee = email.utils.formatdate(time.time() - 90, usegmt=True)
    assert network.retry_after(passee, 5) == 0
    assert network.retry_after("999999", 5, plafond=300) == 300


class _Rep:
    def __init__(self, code, texte="", entetes=None):
        self.status_code, self.text, self.headers = code, texte, entetes or {}


class _Client:
    def __init__(self, *reponses):
        self.reponses, self.appels = list(reponses), 0

    def get(self, *a, **k):
        self.appels += 1
        return self.reponses.pop(0)


def test_linkedin_refus_arrete(monkeypatch):
    linkedin_desc.REFUS.clear()
    c = _Client(_Rep(999))
    assert linkedin_desc.description("1", c) == ""
    assert linkedin_desc.REFUS.is_set()
    # every next offer: no request at all
    c2 = _Client(_Rep(200, "x" * 500))
    assert linkedin_desc.description("2", c2) == "" and c2.appels == 0
    linkedin_desc.REFUS.clear()


def test_linkedin_429_attend_retry_after(monkeypatch):
    linkedin_desc.REFUS.clear()
    attentes = []
    monkeypatch.setattr(linkedin_desc.time, "sleep", attentes.append)
    c = _Client(_Rep(429, entetes={"Retry-After": "42"}), _Rep(404))
    linkedin_desc.description("1", c)
    assert attentes == [42]


def test_vie_indemnite_non_numerique(monkeypatch):
    lot = [
        {"id": 1, "missionTitle": "Analyste ESG", "indemnite": "selon profil"},
        {"id": None, "missionTitle": "Analyste ESG"},
    ]
    pages = iter([{"result": lot}, {"result": []}])

    class _R:
        status_code = 200

        def json(self):
            return next(pages)

    monkeypatch.setattr(vie._commun, "_post_borne", lambda *a, **k: _R())
    monkeypatch.setattr(vie, "_vie_key", lambda: "k")
    monkeypatch.setattr(vie, "title_ok", lambda t: True)
    monkeypatch.setattr(vie.time, "sleep", lambda s: None)
    offres = vie.fetch_vie()
    assert len(offres) == 1 and offres[0]["url"].endswith("/offres/1")


def test_tache_msix_par_l_alias(monkeypatch, tmp_path):
    from jobhunter import frozen, scheduling

    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(frozen, "paquet_msix", lambda: True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    cmd = scheduling.commande()
    assert "WindowsApps" in cmd and "jobhunter-cli.exe" in cmd and cmd.endswith(" pipeline")
    assert str(tmp_path) in cmd
    monkeypatch.setattr(frozen, "paquet_msix", lambda: False)
    assert str(tmp_path) not in scheduling.commande()


def test_mots_du_profil():
    from jobhunter import profile as P

    assert P.motif(["re:"]).search("tout") is None
    assert P.motif(["*"]).search("tout") is None
    assert P.motif(["c++"], entier=True).search("Développeur C++ senior")
    assert P.motif([".net"], entier=True).search("Lead .NET")
    assert not P.motif(["rse"], entier=True).search("RSEau")
    assert not P.motif(["rse"]).search("diverse")
    assert P.motif(["analyste"]).search("analystes")
    assert P.motif(["esg + analyste"]).search("ESG\nanalyste")


def test_elision_d_un_mot_vide():
    from jobhunter.documents.common import _de

    assert _de("") != "d'" and _de("Amundi") == "d'Amundi" and _de("Hollande") == "de Hollande"


def test_caracteres_de_controle():
    from jobhunter.cv_text import _propre
    from jobhunter.sources.common import _ligne

    assert _ligne("Analyste\x0bESG\x00") == "Analyste ESG"
    assert _propre("a\x07b\tc\nd") == "ab\tc\nd"


def test_cible_nulle(monkeypatch):
    from jobhunter.scoring import fit

    monkeypatch.setitem(fit._SC, "cible_score", 0)
    assert fit._cible() == 3.0
