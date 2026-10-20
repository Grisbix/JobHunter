"""Application installed without Python (jobhunter.gele) and browser fallback."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobhunter import gele
from jobhunter.navigation.navigateur import lancer


def test_interpreteur_sous_python():
    with patch.object(sys, "executable", r"C:\Python314\pythonw.exe"):
        assert gele.interpreteur() == str(Path(r"C:\Python314\python.exe"))
    with patch.object(sys, "executable", r"C:\Python314\python.exe"):
        assert gele.interpreteur() == str(Path(r"C:\Python314\python.exe"))


def test_interpreteur_compile():
    with (
        patch.object(sys, "executable", r"C:\Prog\JobHunter\JobHunter.exe"),
        patch.object(sys, "frozen", True, create=True),
    ):
        assert gele.est_gele()
        assert gele.interpreteur() == str(Path(r"C:\Prog\JobHunter\jobhunter-cli.exe"))


def test_dossier_donnees(monkeypatch, tmp_path):
    monkeypatch.setenv("JOBHUNTER_RACINE", str(tmp_path))
    assert gele.dossier_donnees() == tmp_path
    monkeypatch.delenv("JOBHUNTER_RACINE")
    assert gele.dossier_donnees() == Path.home() / "Documents" / "JobHunter"


def test_preparer_donnees_ne_remplace_jamais(tmp_path):
    sq = tmp_path / "squelette"
    (sq / "profil").mkdir(parents=True)
    (sq / "profil" / "exemple_finance_esg.json").write_text("{}", encoding="utf-8")
    (sq / "Scripts").mkdir()
    (sq / "Scripts" / "sources_config.json").write_text('{"livre": 1}', encoding="utf-8")
    dest = tmp_path / "donnees"
    (dest / "Scripts").mkdir(parents=True)
    (dest / "Scripts" / "sources_config.json").write_text('{"mien": 1}', encoding="utf-8")
    copies = gele.preparer_donnees(dest, sq)
    assert copies == [dest / "profil" / "exemple_finance_esg.json"]
    assert (dest / "Scripts" / "sources_config.json").read_text(encoding="utf-8") == '{"mien": 1}'
    for d in ("Scripts", "profil", "Mon_CV", "CV", "Lettres"):
        assert (dest / d).is_dir()
    assert gele.preparer_donnees(dest, sq) == []


def test_aiguiller_module(monkeypatch):
    vu = {}

    def faux(module, run_name, alter_sys):
        vu["module"], vu["argv"] = module, list(sys.argv)
        raise SystemExit(3)

    monkeypatch.setattr(gele.runpy, "run_module", faux)
    assert gele.aiguiller(["-m", "jobhunter.programmes.x", "--a", "1"]) == 3
    assert vu == {
        "module": "jobhunter.programmes.x",
        "argv": ["jobhunter.programmes.x", "--a", "1"],
    }


def test_aiguiller_code(capsys):
    assert gele.aiguiller(["-c", "print('ok-c')"]) == 0
    assert "ok-c" in capsys.readouterr().out


def test_aiguiller_commande(monkeypatch):
    import jobhunter.cli

    monkeypatch.setattr(jobhunter.cli, "main", lambda args: len(args))
    assert gele.aiguiller(["dispo", "--rapport"]) == 2


def _absent():
    return Exception("BrowserType.launch: Executable doesn't exist at C:\\ms-playwright\\chromium")


def test_lancer_repli_sur_le_navigateur_du_systeme():
    ch = MagicMock()
    ch.launch.side_effect = [_absent(), Exception("pas de chrome"), "edge"]
    assert lancer(ch, headless=True) == "edge"
    assert ch.launch.call_args_list[1].kwargs == {"channel": "chrome", "headless": True}
    assert ch.launch.call_args_list[2].kwargs == {"channel": "msedge", "headless": True}


def test_lancer_ne_masque_pas_une_autre_erreur():
    ch = MagicMock()
    ch.launch.side_effect = TimeoutError("lent")
    with pytest.raises(TimeoutError):
        lancer(ch, headless=True)
    assert ch.launch.call_count == 1


def test_lancer_sans_aucun_navigateur():
    ch = MagicMock()
    ch.launch.side_effect = [_absent(), Exception("x"), Exception("y")]
    with pytest.raises(Exception, match="Executable doesn't exist"):
        lancer(ch, headless=True)
