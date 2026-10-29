"""3.69: uninstalling asks whether to remove the data (« No » by default, Recycle Bin),
and the installed application can send its own data to the Recycle Bin."""

from pathlib import Path

from jobhunter import frozen, profiles, scheduling
from jobhunter.programs import update
from jobhunter.web import api

RACINE = Path(__file__).resolve().parent.parent
ISS = (RACINE / "tools" / "installer" / "JobHunter.iss").read_text(encoding="utf-8-sig")
JS = (RACINE / "src" / "jobhunter" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _installee(monkeypatch, tmp_path):
    maison = tmp_path / "maison"
    donnees = maison / "Documents" / "JobHunter"
    donnees.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: maison)
    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(profiles, "principale", lambda: donnees)
    return donnees


def test_seul_le_dossier_de_l_application_installee(monkeypatch, tmp_path):
    donnees = _installee(monkeypatch, tmp_path)
    assert api._dossier_effacable() == donnees.resolve()
    # a folder named by JOBHUNTER_RACINE, a source checkout: never
    autre = tmp_path / "Recherche_emploi"
    autre.mkdir()
    monkeypatch.setattr(profiles, "principale", lambda: autre)
    assert api._dossier_effacable() is None
    monkeypatch.setattr(profiles, "principale", lambda: donnees)
    monkeypatch.setattr(frozen, "est_gele", lambda: False)
    assert api._dossier_effacable() is None


class _Fenetre:
    fermee = False

    def destroy(self):
        self.fermee = True


def _api():
    a = api.Api.__new__(api.Api)
    a._fenetre = _Fenetre()
    return a


def test_effacer_envoie_a_la_corbeille_et_ferme(monkeypatch, tmp_path):
    donnees = _installee(monkeypatch, tmp_path)
    lances, retiree = [], []
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(scheduling, "disponible", lambda: True)
    monkeypatch.setattr(scheduling, "planifiee", lambda: True)
    monkeypatch.setattr(scheduling, "supprimer", lambda: retiree.append(1) or (True, ""))
    monkeypatch.setattr(api.subprocess, "Popen", lambda cmd, **kw: lances.append((cmd, kw)))
    a = _api()
    r = a.effacer_donnees()
    assert r["ok"] and a._fenetre.fermee and retiree
    cmd, kw = lances[0]
    assert cmd[0] == "powershell" and "SendToRecycleBin" in cmd[-1]
    assert kw["env"]["JH_DOSSIER"] == str(donnees.resolve())
    assert donnees.is_dir()  # removed by PowerShell once the window is closed


def test_effacer_refuse(monkeypatch, tmp_path):
    _installee(monkeypatch, tmp_path)
    monkeypatch.setattr(update, "file_libre", lambda garder=True: False)
    monkeypatch.setattr(
        api.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError)
    )
    a = _api()
    assert not a.effacer_donnees()["ok"] and not a._fenetre.fermee
    monkeypatch.setattr(frozen, "est_gele", lambda: False)
    assert not a.effacer_donnees()["ok"]


def test_bouton_seulement_quand_effacable():
    assert 'm.effacable ? bouton("Effacer mes données…"' in JS
    assert 'appel("effacer_donnees")' in JS


def test_la_desinstallation_demande_non_par_defaut():
    assert "MB_YESNO or MB_DEFBUTTON2" in ISS
    assert "UninstallSilent" in ISS  # never asked in a silent uninstall
    assert "SendToRecycleBin" in ISS and "{userdocs}\\JobHunter" in ISS
    assert "fr.EffacerDonnees=" in ISS and "en.EffacerDonnees=" in ISS
    # the daily task is removed only when it runs this installation
    assert "JobHunter - collecte quotidienne" in ISS and "ExpandConstant('{app}')" in ISS
