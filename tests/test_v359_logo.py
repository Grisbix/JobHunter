"""3.59: one logo everywhere (the user, 2026-10-28: « pas un logo Python »).

The window's icon from its creation, the Start menu shortcut with the window's
identity, the toasts under JobHunter's name, the installer's own icon, the README.
"""

import subprocess
from pathlib import Path

from jobhunter import cli
from jobhunter.programs import notify_matches, shortcut

RACINE = Path(__file__).resolve().parent.parent


def test_la_fenetre_a_son_icone_des_sa_creation():
    source = (RACINE / "src" / "jobhunter" / "web" / "__main__.py").read_text(encoding="utf-8")
    assert "webview.start(icon=" in source
    assert "shortcut.assurer" in source


def test_l_installateur_porte_l_icone_et_l_identite():
    iss = (RACINE / "tools" / "installer" / "JobHunter.iss").read_text(encoding="utf-8")
    assert r"SetupIconFile=..\..\src\jobhunter\assets\jobhunter.ico" in iss
    assert iss.count('AppUserModelID: "Grisbix.JobHunter"') == 2
    assert (RACINE / "src" / "jobhunter" / "assets" / "jobhunter.ico").is_file()


def test_install_bat_fait_le_raccourci():
    assert "JobHunter.pyw shortcut" in (RACINE / "launchers" / "install.bat").read_text()
    assert cli.module_de("shortcut") == "jobhunter.programs.shortcut"


def test_le_readme_montre_le_logo():
    # Since 3.66, the logo with its name, light or dark with GitHub's theme.
    for nom in ("README.md", "README.fr.md"):
        texte = (RACINE / nom).read_text(encoding="utf-8")
        assert "docs/brand/jobhunter-stacked-light.svg" in texte
        assert "docs/brand/jobhunter-stacked-dark.svg" in texte


def test_la_cible_lance_jobhunter_pyw_sans_console(monkeypatch, tmp_path):
    from jobhunter import root

    (tmp_path / "JobHunter.pyw").write_text("")
    monkeypatch.setattr(root, "racine", lambda: tmp_path)
    exe, args, dossier = shortcut.cible()
    assert args == f'"{tmp_path / "JobHunter.pyw"}"' and dossier == tmp_path
    (tmp_path / "JobHunter.pyw").unlink()
    assert shortcut.cible()[1] == "-m jobhunter app"


def test_le_raccourci_passe_les_valeurs_par_l_environnement(monkeypatch, tmp_path):
    vu = {}

    def run(cmd, env, **k):
        vu.update(cmd=cmd, env=env)

    monkeypatch.setattr(shortcut.subprocess, "run", run)
    lien = tmp_path / "Job'$(x).lnk"
    shortcut.creer(lien, Path("pythonw.exe"), '"a b"', tmp_path)
    assert str(lien) not in vu["cmd"][-1] and vu["env"]["JH_LIEN"] == str(lien)
    assert vu["env"]["JH_AUMID"] == "Grisbix.JobHunter"


def test_assurer_ne_refait_pas_un_raccourci_present(monkeypatch, tmp_path):
    monkeypatch.setattr(shortcut, "dossiers", lambda bureau: [tmp_path])
    monkeypatch.setattr(shortcut, "_temoin", lambda: tmp_path / "_raccourci_icone.txt")
    monkeypatch.setattr(shortcut.sys, "platform", "win32")
    faits = []
    monkeypatch.setattr(shortcut, "creer", lambda *a: faits.append(a))
    monkeypatch.setattr(shortcut, "cible", lambda: (Path("p"), "", tmp_path))
    shortcut.assurer()
    assert len(faits) == 1
    (tmp_path / "JobHunter.lnk").write_bytes(b"")
    shortcut.assurer()
    assert len(faits) == 1


def test_le_toast_prend_l_identite_de_jobhunter_avec_le_raccourci(monkeypatch, tmp_path):
    monkeypatch.setattr(notify_matches.sys, "platform", "win32")
    monkeypatch.setattr(shortcut, "dossiers", lambda bureau: [tmp_path])
    assert notify_matches.appid() == notify_matches._APPID  # no shortcut: the Terminal's
    (tmp_path / "JobHunter.lnk").write_bytes(b"")
    assert notify_matches.appid() == "Grisbix.JobHunter"


def test_l_echec_du_raccourci_est_silencieux(monkeypatch, tmp_path):
    monkeypatch.setattr(shortcut, "dossiers", lambda bureau: [tmp_path])
    monkeypatch.setattr(shortcut, "_temoin", lambda: tmp_path / "_raccourci_icone.txt")
    monkeypatch.setattr(shortcut.sys, "platform", "win32")
    monkeypatch.setattr(shortcut, "cible", lambda: (Path("p"), "", tmp_path))

    def echec(*a):
        raise subprocess.CalledProcessError(1, "powershell")

    monkeypatch.setattr(shortcut, "creer", echec)
    shortcut.assurer()  # no exception


def test_un_raccourci_a_l_icone_disparue_est_refait_bureau_compris(monkeypatch, tmp_path):
    """3.78 moved the icon: the old shortcuts showed Python's logo (2026-11-04)."""
    menu, bureau, temoin = tmp_path / "menu", tmp_path / "bureau", tmp_path / "t.txt"
    for d in (menu, bureau):
        d.mkdir()
        (d / "JobHunter.lnk").write_bytes(b"")
    monkeypatch.setattr(shortcut, "dossiers", lambda b: [menu, bureau] if b else [menu])
    monkeypatch.setattr(shortcut, "_temoin", lambda: temoin)
    monkeypatch.setattr(shortcut.sys, "platform", "win32")
    monkeypatch.setattr(shortcut, "cible", lambda: (Path("p"), "", tmp_path))
    faits = []
    monkeypatch.setattr(shortcut, "creer", lambda lien, *a: faits.append(lien.parent))
    temoin.write_text("C:/ailleurs/app/assets/jobhunter.ico", encoding="utf-8")
    shortcut.assurer()
    assert faits == [menu, bureau]
    assert temoin.read_text(encoding="utf-8") == str(shortcut.ICONE)
    shortcut.assurer()  # noted: nothing more
    assert faits == [menu, bureau]


def test_la_reparation_n_ajoute_rien_a_un_bureau_sans_raccourci(monkeypatch, tmp_path):
    menu, bureau = tmp_path / "menu", tmp_path / "bureau"
    menu.mkdir()
    bureau.mkdir()
    monkeypatch.setattr(shortcut, "dossiers", lambda b: [menu, bureau] if b else [menu])
    monkeypatch.setattr(shortcut, "_temoin", lambda: tmp_path / "t.txt")
    monkeypatch.setattr(shortcut.sys, "platform", "win32")
    monkeypatch.setattr(shortcut, "cible", lambda: (Path("p"), "", tmp_path))
    faits = []
    monkeypatch.setattr(shortcut, "creer", lambda lien, *a: faits.append(lien.parent))
    shortcut.assurer()
    assert faits == [menu]
