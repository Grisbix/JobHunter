"""3.83: the installer's copy updates in the background (the user, 2026-11-05: « la mise
à jour doit se faire en background »): downloaded and checked at start-up, installed
silently once the window closes, then JobHunter opens again."""

import sys
from pathlib import Path

import js_app
import pytest

from jobhunter import frozen, setup_update, signature
from jobhunter.programs import update
from jobhunter.web import api

RACINE = Path(__file__).resolve().parent.parent
ISS = (RACINE / "tools" / "installer" / "JobHunter.iss").read_text(encoding="utf-8-sig")
JS = js_app.source()


def test_seulement_la_copie_de_l_installateur(monkeypatch, tmp_path):
    exe = tmp_path / "JobHunter.exe"
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr(frozen, "est_gele", lambda: False)
    assert not setup_update.concerne()
    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(frozen, "paquet_msix", lambda: False)
    assert not setup_update.concerne()  # no unins000.exe: not the installer's
    (tmp_path / "unins000.exe").write_bytes(b"")
    assert setup_update.concerne()
    monkeypatch.setattr(frozen, "paquet_msix", lambda: True)
    assert not setup_update.concerne()  # the Store's package: store_update


@pytest.fixture
def telechargement(monkeypatch, tmp_path):
    monkeypatch.setattr(setup_update, "chemin", lambda v: tmp_path / f"JobHunterSetup-{v}.exe")
    monkeypatch.setattr(update, "_signature", lambda v: {"bon": b"SETUP"})
    appels = []

    def get(url, timeout):
        appels.append(url)
        return b"SETUP"

    def controler(m, setup):
        if setup != m["bon"]:
            raise signature.SignatureInvalide("pas le bon")

    monkeypatch.setattr(update, "_get", get)
    monkeypatch.setattr(signature, "controler_setup", controler)
    return appels, tmp_path


def test_preparer_telecharge_et_verifie(telechargement):
    appels, dossier = telechargement
    f = setup_update.preparer("9.9.9")
    assert f.read_bytes() == b"SETUP" and len(appels) == 1
    assert setup_update.preparer("9.9.9") == f and len(appels) == 1  # checked again, kept
    f.write_bytes(b"PIEGE")
    assert setup_update.preparer("9.9.9").read_bytes() == b"SETUP" and len(appels) == 2


def test_preparer_refuse_un_installateur_non_signe(telechargement, monkeypatch):
    _, dossier = telechargement
    monkeypatch.setattr(update, "_get", lambda url, timeout: b"PIEGE")
    with pytest.raises(signature.SignatureInvalide):
        setup_update.preparer("9.9.9")
    assert not list(dossier.iterdir())  # nothing written


def test_appliquer_attend_puis_installe_sans_fenetre(monkeypatch, tmp_path):
    vu = {}
    monkeypatch.setattr(update, "ATTENDUE", tmp_path / ".maj_attendue.json")
    monkeypatch.setattr(update, "version_locale", lambda: "3.82.0")
    monkeypatch.setattr(
        setup_update.subprocess, "Popen", lambda cmd, **k: vu.update(cmd=cmd, env=k["env"])
    )
    setup_update.appliquer(tmp_path / "s.exe", "3.83.0", relancer=True)
    assert vu["env"]["JH_SETUP"].endswith("s.exe") and vu["env"]["JH_RELANCER"] == "1"
    assert '"version": "3.83.0"' in (tmp_path / ".maj_attendue.json").read_text(encoding="utf-8")
    setup_update.appliquer(tmp_path / "s.exe", "3.83.0", relancer=False)
    assert vu["env"]["JH_RELANCER"] == ""


def test_lanceur_sans_detached_process(monkeypatch):
    vu = {}
    monkeypatch.setattr(setup_update.subprocess, "Popen", lambda cmd, **k: vu.update(k))
    setup_update.apres_fermeture("exit", {"JH_X": "1"})
    assert vu["creationflags"] == getattr(setup_update.subprocess, "CREATE_NO_WINDOW", 0)
    assert vu["env"]["JH_X"] == "1" and vu["cwd"] == setup_update.tempfile.gettempdir()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell")
def test_le_script_tourne_vraiment(tmp_path):
    """3.84.1: with DETACHED_PROCESS, PowerShell 5.1 exited 0 and ran nothing."""
    marque = tmp_path / "fait.txt"
    p = setup_update.apres_fermeture(
        "Set-Content -LiteralPath $env:JH_MARQUE -Value $env:JH_PID", {"JH_MARQUE": str(marque)}
    )
    assert p.wait(timeout=60) == 0
    assert marque.read_text(encoding="utf-8-sig").strip() == str(__import__("os").getpid())


def test_script_silencieux():
    s = setup_update.SCRIPT
    assert "Wait-Process" in s and "'/VERYSILENT'" in s and "'/SUPPRESSMSGBOXES'" in s
    assert "/RELANCER" in s


def test_installateur_relance_jobhunter():
    assert 'Filename: "{app}\\JobHunter.exe"; Flags: nowait; Check: Relancer' in ISS
    assert "function Relancer: Boolean;" in ISS and "WizardSilent" in ISS
    assert "PrivilegesRequired=lowest" in ISS  # per user: no UAC prompt in silent mode


class _Fenetre:
    def __init__(self):
        self.fermee = False

    def destroy(self):
        self.fermee = True


@pytest.fixture
def appli(monkeypatch):
    a = api.Api()
    a._fenetre = _Fenetre()
    lances = []
    monkeypatch.setattr(
        a,
        "mise_a_jour",
        lambda: {
            "signee": True,
            "store": False,
            "nouvelle": True,
            "derniere": "3.83.0",
            "installee": "3.82.0",
            "silencieux": True,
        },
    )
    monkeypatch.setattr(setup_update, "preparer", lambda v: Path(f"S-{v}.exe"))
    monkeypatch.setattr(setup_update, "appliquer", lambda c, v, r: lances.append((c, v, r)))
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    return a, lances


def test_annonce_une_fois_prete(appli):
    a, _ = appli
    v = a.annonce_maj()
    assert v["pret"] and a._setup_pret == (Path("S-3.83.0.exe"), "3.83.0")


def test_pas_de_bouton_si_le_telechargement_echoue(appli, monkeypatch):
    a, _ = appli

    def echec(v):
        raise OSError("hors ligne")

    monkeypatch.setattr(setup_update, "preparer", echec)
    assert a.annonce_maj() is None


def test_redemarrer_installe_et_ferme(appli):
    a, lances = appli
    assert a.installer_maj() == {"ok": True}
    assert lances == [(Path("S-3.83.0.exe"), "3.83.0", True)] and a._fenetre.fermee


def test_file_occupee_rien(appli, monkeypatch):
    a, lances = appli
    monkeypatch.setattr(update, "file_libre", lambda garder=True: False)
    assert not a.installer_maj()["ok"] and not lances


def test_fermer_la_fenetre_installe_sans_relancer(appli):
    a, lances = appli
    a.annonce_maj()
    a.fenetre("fermer")
    assert lances == [(Path("S-3.83.0.exe"), "3.83.0", False)] and a._fenetre.fermee


def test_fermer_sans_mise_a_jour_prete(appli):
    a, lances = appli
    a.fenetre("fermer")
    assert not lances and a._fenetre.fermee


def test_interface():
    assert "Redémarrer pour mettre à jour" in JS and 'appel("installer_maj")' in JS
    from jobhunter.web.texts import TEXTES

    for cle in (
        "Redémarrer pour mettre à jour ({v})",
        "Vérification de la mise à jour…",
        "Installée : {v}. Elle est vérifiée (signature), installée sans fenêtre, puis JobHunter se rouvre.{x}",
    ):
        assert cle in TEXTES
