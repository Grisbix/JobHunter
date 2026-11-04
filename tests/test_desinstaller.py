"""« Désinstaller JobHunter » removes the application and its data at once.

The user, 2026-11-04: uninstalled then reinstalled on another computer, the offers and
CVs were still there (the installer asks with « No » by default, the Store cannot ask).
"""

from pathlib import Path

import pytest

from jobhunter import frozen, profiles, scheduling
from jobhunter.programs import shortcut, update
from jobhunter.web import api

RACINE = Path(__file__).resolve().parent.parent
JS = (RACINE / "src" / "jobhunter" / "web" / "static" / "app.js").read_text(encoding="utf-8")


class _Fenetre:
    fermee = False

    def destroy(self):
        self.fermee = True


@pytest.fixture
def installee(monkeypatch, tmp_path):
    """An installed application: data in Documents/JobHunter, no task running."""
    maison = tmp_path / "maison"
    donnees = maison / "Documents" / "JobHunter"
    donnees.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: maison)
    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(frozen, "famille_msix", lambda: "")
    monkeypatch.setattr(profiles, "principale", lambda: donnees)
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(scheduling, "disponible", lambda: False)
    lances = []
    monkeypatch.setattr(api.subprocess, "Popen", lambda cmd, **kw: lances.append((cmd, kw)))
    a = api.Api.__new__(api.Api)
    a._fenetre = _Fenetre()
    return a, donnees, lances


def _installateur(monkeypatch, tmp_path):
    app = tmp_path / "Programs" / "JobHunter"
    app.mkdir(parents=True)
    (app / "unins000.exe").write_bytes(b"")
    monkeypatch.setattr(api.sys, "executable", str(app / "JobHunter.exe"))
    return app / "unins000.exe"


def test_l_installateur_desinstalle_en_silence_apres_la_corbeille(installee, monkeypatch, tmp_path):
    a, donnees, lances = installee
    desinstalleur = _installateur(monkeypatch, tmp_path)
    r = a.desinstaller()
    assert r["ok"] and a._fenetre.fermee
    cmd, kw = lances[0]
    assert cmd[0] == "powershell" and "SendToRecycleBin" in cmd[-1] and "/VERYSILENT" in cmd[-1]
    assert kw["env"]["JH_DOSSIER"] == str(donnees.resolve())
    assert kw["env"]["JH_DESINSTALLEUR"] == str(desinstalleur)
    # data first, then the application: the silent uninstaller asks nothing
    assert cmd[-1].index("SendToRecycleBin") < cmd[-1].index("JH_DESINSTALLEUR")


def test_le_paquet_du_store_est_retire_avec_son_icone(installee, monkeypatch, tmp_path):
    a, _, lances = installee
    bureau = tmp_path / "Bureau"
    bureau.mkdir()
    (bureau / "JobHunter.lnk").write_bytes(b"")
    monkeypatch.setattr(frozen, "famille_msix", lambda: "Grisbix.JobHunter_abc123")
    monkeypatch.setattr(shortcut, "dossier_bureau", lambda: bureau)
    assert a.desinstaller()["ok"]
    cmd, kw = lances[0]
    assert "Remove-AppxPackage" in cmd[-1]
    assert kw["env"]["JH_FAMILLE"] == "Grisbix.JobHunter_abc123"
    assert kw["env"]["JH_LIEN"] == str(bureau / "JobHunter.lnk")


def test_un_dossier_choisi_reste_en_place(installee, monkeypatch, tmp_path):
    a, _, lances = installee
    _installateur(monkeypatch, tmp_path)
    autre = tmp_path / "Recherche_emploi"
    autre.mkdir()
    monkeypatch.setattr(profiles, "principale", lambda: autre)
    assert a.desinstaller()["ok"]
    assert lances[0][1]["env"]["JH_DOSSIER"] == ""


def test_refus_hors_application_installee_ou_tache_en_cours(installee, monkeypatch, tmp_path):
    a, _, lances = installee
    assert not a.desinstaller()["ok"]  # frozen, but no uninstaller nor package
    _installateur(monkeypatch, tmp_path)
    monkeypatch.setattr(update, "file_libre", lambda garder=True: False)
    assert not a.desinstaller()["ok"]
    monkeypatch.setattr(frozen, "est_gele", lambda: False)
    assert not a.desinstaller()["ok"]
    assert not lances and not a._fenetre.fermee


def test_bouton_dans_la_maintenance():
    assert 'bouton("Désinstaller JobHunter…", "corbeille", () => desinstaller(m))' in JS
    assert "m.desinstallable ? h(" in JS
    assert 'appel("desinstaller")' in JS


def test_maintenance_est_dans_les_reglages():
    """The user, 2026-11-04: maintenance and settings in one panel."""
    html = (RACINE / "src" / "jobhunter" / "web" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'data-ecran="maintenance"' not in html and 'data-ecran="reglages"' in html
    assert "ECRANS.maintenance" not in JS
    reglages = JS[JS.index("ECRANS.reglages = {") :][:6000]
    assert "...(await cartesMaintenance())" in reglages
    # a screen saved as "maintenance" opens Réglages, not the home page
    assert 'if (nom === "maintenance") nom = "reglages";' in JS
