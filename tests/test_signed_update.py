"""Signed update (2.18): a version the author did not sign is never installed.

Offline, like test_update: ZIP, signature and installer served from memory.
"""

import argparse

import pytest
from test_update import V12, V13, installer, lire, zip_de  # noqa: F401 (installer : fixture)

from jobhunter import signature as sig
from jobhunter.programs import update as maj

SECRET = bytes(range(1, 33))
CLE = sig.publique(SECRET).hex()
EXE = b"MZ installateur 1.3.0"


def octets(fichiers):
    return {k: v.encode("utf-8") for k, v in fichiers.items()}


def servis(zip_fichiers=V13, signes=V13, version_signee="1.3.0", setup=EXE, avec_signature=True):
    m = sig.manifeste(version_signee, octets(signes), setup)
    urls = {
        maj.VERSION_URL: b"1.3.0\n",
        maj.TAG_URL.format("1.3.0"): zip_de(zip_fichiers, "JobHunter-1.3.0"),
        maj.TAG_URL.format("1.2.0"): zip_de(V12, "JobHunter-1.2.0"),
        maj.ASSET_URL.format("1.3.0", maj.SETUP): EXE,
    }
    if avec_signature:
        urls[maj.ASSET_URL.format("1.3.0", sig.FICHIER)] = sig.emballer(SECRET, m)
    return urls


@pytest.fixture
def signee(installer, monkeypatch):  # noqa: F811 (imported fixture)
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", CLE)
    return installer


def lancer(capsys):
    rc = maj.par_zip(argparse.Namespace(verifier=False, forcer=False, annuler=False))
    return rc, capsys.readouterr().out


def test_version_signee_installee(signee, capsys):
    d = signee(zips=servis())
    rc, sortie = lancer(capsys)
    assert rc == 0, sortie
    assert "Signature de l'auteur vérifiée" in sortie
    assert lire(d, "Scripts/a.py") == "A = 2\n"


def test_fichier_altere_refuse_rien_ecrit(signee, capsys):
    piege = {**V13, "Scripts/a.py": "import os; os.system('x')\n"}
    d = signee(zips=servis(zip_fichiers=piege))
    rc, sortie = lancer(capsys)
    assert rc == 1
    assert "refusée" in sortie and "Scripts/a.py" in sortie
    assert lire(d, "Scripts/a.py") == "A = 1\n"
    assert not (d / "_sauvegarde_maj").exists()


def test_fichier_ajoute_refuse(signee, capsys):
    d = signee(zips=servis(zip_fichiers={**V13, "Scripts/piege.py": "x = 1\n"}))
    rc, _ = lancer(capsys)
    assert rc == 1
    assert lire(d, "Scripts/piege.py") is None


def test_sans_signature_refuse(signee, capsys):
    d = signee(zips=servis(avec_signature=False))
    rc, _ = lancer(capsys)
    assert rc == 1
    assert lire(d, "Scripts/a.py") == "A = 1\n"


def test_vieille_signature_refusee(signee, capsys):
    d = signee(zips=servis(version_signee="1.2.0"))
    rc, sortie = lancer(capsys)
    assert rc == 1 and "1.2.0" in sortie
    assert lire(d, "Scripts/a.py") == "A = 1\n"


def test_sans_cle_publique_comme_avant(installer, capsys, monkeypatch):  # noqa: F811
    """As long as the author has not published their key: the tag's ZIP, said unsigned."""
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", "")
    d = installer()
    rc, sortie = lancer(capsys)
    assert rc == 0
    assert "1.3.0 non signée" in sortie
    assert lire(d, "Scripts/a.py") == "A = 2\n"


# ── installed application: the installer downloaded, checked, opened ───────


@pytest.fixture
def appli(tmp_path, monkeypatch):
    lances = []

    def faire(urls, cle=CLE):
        monkeypatch.setattr(sig, "CLE_PUBLIQUE", cle)
        monkeypatch.setattr(maj, "nouvelle_version", lambda **kw: "1.3.0")
        monkeypatch.setattr(maj, "version_locale", lambda: "1.2.0")
        monkeypatch.setattr(maj, "_get", lambda url, t: urls[url])
        monkeypatch.setattr(maj.subprocess, "Popen", lambda args, **kw: lances.append(args))
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        monkeypatch.setattr("webbrowser.open", lambda url: lances.append(["navigateur", url]))
        return lances

    return faire


def test_appli_installateur_signe_ouvert(appli, tmp_path, capsys):
    lances = appli(servis())
    assert maj.maj_application(False) == 0
    chemin = tmp_path / "JobHunterSetup-1.3.0.exe"
    assert lances == [[str(chemin)]]
    assert chemin.read_bytes() == EXE


def test_appli_installateur_altere_jamais_ouvert(appli, capsys):
    urls = servis(setup=b"autre chose")  # signed for another executable
    lances = appli(urls)
    assert maj.maj_application(False) == 1
    assert lances == []
    assert "refusée" in capsys.readouterr().out


def test_appli_verifier_ne_telecharge_rien(appli):
    lances = appli({})
    assert maj.maj_application(True) == 0
    assert lances == []


def test_appli_sans_cle_empreinte_publiee(appli, capsys):
    import hashlib

    urls = servis(avec_signature=False)
    urls[maj.ASSET_URL.format("1.3.0", maj.SETUP + ".sha256")] = (
        hashlib.sha256(EXE).hexdigest() + "  JobHunterSetup.exe\n"
    ).encode()
    lances = appli(urls, cle="")
    assert maj.maj_application(False) == 0
    assert len(lances) == 1
    urls[maj.ASSET_URL.format("1.3.0", maj.SETUP + ".sha256")] = b"0" * 64
    lances.clear()
    assert maj.maj_application(False) == 1
    assert lances == []


def test_appli_hors_ligne_ouvre_la_page(appli):
    lances = appli({})  # no download possible
    assert maj.maj_application(False) == 1
    assert lances == [["navigateur", maj.PAGE_VERSIONS]]
