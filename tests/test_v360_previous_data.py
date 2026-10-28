"""3.60: a new download finds the previous folder's data (the user, 2026-10-28: « quand on
retélécharge on repasse par le processus de rentrer le CV »)."""

import os
import time
from pathlib import Path

from jobhunter import previous_data as pd
from jobhunter import welcome


def _dossier(d: Path, profil: str = "profile/profile.json") -> Path:
    (d / profil).parent.mkdir(parents=True, exist_ok=True)
    (d / profil).write_text('{"identite": {}}', encoding="utf-8")
    return d


def test_trouve_l_ancien_telechargement_a_cote(tmp_path):
    ancien = _dossier(tmp_path / "JobHunter-main")
    neuf = tmp_path / "JobHunter-main (1)"
    (neuf / "profile").mkdir(parents=True)
    assert pd.candidats(neuf, lieux=[]) == [ancien.resolve()]


def test_extraire_tout_cree_un_dossier_dans_le_dossier(tmp_path):
    ancien = _dossier(tmp_path / "Downloads" / "JobHunter-main" / "JobHunter-main")
    neuf = tmp_path / "ailleurs" / "JobHunter"
    neuf.mkdir(parents=True)
    assert pd.candidats(neuf, lieux=[tmp_path / "Downloads"]) == [ancien.resolve()]


def test_le_plus_recent_d_abord_et_le_format_2x(tmp_path):
    vieux = _dossier(tmp_path / "JobHunter-3.0", "profil/profil.json")
    recent = _dossier(tmp_path / "JobHunter-3.58.0")
    os.utime(vieux / "profil" / "profil.json", (time.time() - 3600,) * 2)
    ici = tmp_path / "JobHunter-3.59.0"
    ici.mkdir()
    assert pd.candidats(ici, lieux=[]) == [recent.resolve(), vieux.resolve()]


def test_ni_soi_meme_ni_un_dossier_sans_profil_ni_un_autre_nom(tmp_path):
    ici = _dossier(tmp_path / "JobHunter")
    (tmp_path / "JobHunter-vide" / "profile").mkdir(parents=True)
    _dossier(tmp_path / "Autre")
    assert pd.candidats(ici, lieux=[]) == []


def test_reprendre_copie_les_donnees_pas_le_code_ni_les_sauvegardes(tmp_path):
    src = _dossier(tmp_path / "ancien")
    (src / "My_CV").mkdir()
    (src / "My_CV" / "cv.pdf").write_bytes(b"%PDF")
    (src / "data" / "_backups" / "2026-10-27").mkdir(parents=True)
    (src / "data" / "applications.json").write_text("{}")
    (src / "src").mkdir()
    (src / "src" / "x.py").write_text("")
    dest = tmp_path / "neuf"
    (dest / "profile").mkdir(parents=True)
    (dest / "profile" / "LISEZ-MOI.txt").write_text("squelette")
    copies = pd.reprendre(src, dest)
    assert copies == ["data", "profile", "My_CV"]
    assert (dest / "profile" / "profile.json").is_file()
    assert (dest / "profile" / "LISEZ-MOI.txt").read_text() == "squelette"
    assert (dest / "My_CV" / "cv.pdf").read_bytes() == b"%PDF"
    assert (dest / "data" / "applications.json").is_file()
    assert not (dest / "data" / "_backups").exists() and not (dest / "src").exists()
    assert (src / "profile" / "profile.json").is_file()  # the previous folder unchanged


def test_l_accueil_propose_la_reprise_avant_le_cv(monkeypatch, tmp_path):
    from jobhunter import profile, root

    src = _dossier(tmp_path / "JobHunter-main")
    ici = tmp_path / "JobHunter"
    ici.mkdir()
    monkeypatch.setattr(root, "racine", lambda: ici)
    monkeypatch.setattr(pd, "_lieux", lambda: [])
    monkeypatch.setattr(welcome, "proposer_reprise", lambda f, c: c[0])
    monkeypatch.setattr(welcome, "_migrer_si_besoin", lambda: None)
    monkeypatch.setattr(profile, "recharger", lambda f=None: None)
    monkeypatch.setattr(profile, "charger", lambda: {})
    assert welcome._reprise(None)
    assert (ici / "profile" / "profile.json").is_file()
    assert src.is_dir()


def test_sans_ancien_dossier_l_accueil_demande_le_cv(monkeypatch, tmp_path):
    from jobhunter import root

    monkeypatch.setattr(root, "racine", lambda: tmp_path / "JobHunter")
    monkeypatch.setattr(pd, "_lieux", lambda: [])
    vu = []
    monkeypatch.setattr(welcome, "proposer_reprise", lambda f, c: vu.append(c))
    assert not welcome._reprise(None) and vu == []
