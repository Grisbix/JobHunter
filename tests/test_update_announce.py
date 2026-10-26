"""The update announcement: only a signed version, remembered until it is installed.

Offline: VERSION and the signature are served from memory.
"""

import pytest

from jobhunter import signature as sig
from jobhunter.programs import update as maj


@pytest.fixture
def annonce(tmp_path, monkeypatch):
    appels = []

    def faire(distante="1.3.0", signee=True, locale="1.2.0"):
        servis = {maj.VERSION_URL: distante.encode()}
        if signee:
            servis[maj.ASSET_URL.format(distante, sig.FICHIER)] = b"{}"

        def get(url, t):
            appels.append(url)
            if url not in servis:
                raise OSError("404")
            return servis[url]

        monkeypatch.setattr(sig, "CLE_PUBLIQUE", "ab" * 32)
        monkeypatch.setattr(maj, "DERNIERE_VERIF", tmp_path / ".maj_derniere_verif")
        monkeypatch.setattr(maj, "version_locale", lambda: locale)
        monkeypatch.setattr(maj._gele, "est_gele", lambda: True)
        monkeypatch.setattr(maj, "_get", get)
        return appels

    return faire


def test_version_signee_annoncee_puis_retenue(annonce):
    appels = annonce()
    assert maj.nouvelle_version() == "1.3.0"
    n = len(appels)
    # Next start, the same day: shown again, without asking GitHub.
    assert maj.nouvelle_version() == "1.3.0"
    assert len(appels) == n


def test_version_pas_encore_signee_pas_annoncee(annonce):
    annonce(signee=False)
    assert maj.nouvelle_version() is None
    # No date left: the next start asks again.
    assert not maj.DERNIERE_VERIF.exists()


def test_version_retenue_oubliee_une_fois_installee(annonce, monkeypatch):
    annonce()
    assert maj.nouvelle_version() == "1.3.0"
    monkeypatch.setattr(maj, "version_locale", lambda: "1.3.0")
    assert maj.nouvelle_version() is None


def test_deja_a_jour(annonce):
    appels = annonce(distante="1.2.0")
    assert maj.nouvelle_version() is None
    assert appels == [maj.VERSION_URL]
    assert maj.nouvelle_version() is None
    assert appels == [maj.VERSION_URL]


def test_ancienne_date_seule_lue_sans_erreur(annonce):
    annonce()
    maj.DERNIERE_VERIF.write_text("2026-10-26 08:00", encoding="utf-8")
    assert maj.nouvelle_version() is None
