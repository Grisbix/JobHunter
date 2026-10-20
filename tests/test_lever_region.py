"""Lever: feeds hosted in the European region (api.eu.lever.co)."""


def test_lever_repli_sur_la_region_europeenne(monkeypatch):
    """A Lever feed missing from api.lever.co (404) is looked for on api.eu.lever.co."""
    from jobhunter.sources import ats
    from jobhunter.sources import commun as _commun

    class R:
        def __init__(self, code, donnees=None):
            self.status_code, self._d = code, donnees or []

        def json(self):
            return self._d

    vues = []

    def faux_get(envoi, url, **kw):
        vues.append(url)
        if "api.eu.lever.co" in url:
            return R(200, [{"text": "Analyste ESG", "hostedUrl": "https://jobs.eu.lever.co/x/1"}])
        return R(404)

    monkeypatch.setattr(_commun, "_get_borne", faux_get)
    monkeypatch.setattr(ats, "title_ok", lambda *a, **k: True, raising=False)
    offres = ats.fetch_ats("lever", "x")
    assert [u.split("/v0")[0] for u in vues] == ["https://api.lever.co", "https://api.eu.lever.co"]
    assert offres and offres[0]["url"] == "https://jobs.eu.lever.co/x/1"
