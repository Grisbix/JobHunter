"""Several profiles, one workspace each (jobhunter.profiles, app.profiles_menu).

Fictitious roots in tmp_path: a profile is a complete data folder, two searches never
share a queue, and the keys stay in the main profile.
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from jobhunter import profiles as P
from jobhunter import root
from jobhunter.app import profiles_menu as M
from jobhunter.programs import daily_pipeline, update


def ecrire(f: Path, contenu: object) -> Path:
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(contenu), encoding="utf-8")
    return f


@pytest.fixture
def principale(tmp_path, monkeypatch):
    """A main root in the 3.0 layout, with a profile, a key and a company list."""
    r = tmp_path / "JobHunter"
    ecrire(r / "profile" / "profile.json", {"identite": {"nom": "Camille"}})
    ecrire(r / "data" / "apply_queue.json", [])
    ecrire(r / "data" / "sources_config.json", {"entreprises": ["a"]})
    ecrire(r / "data" / "adzuna.json", {"app_id": "x"})
    monkeypatch.setenv("JOBHUNTER_RACINE", str(r))
    monkeypatch.delenv(P.ENV_PRINCIPALE, raising=False)
    return r


def termine(r: Path, nom: str = "") -> None:
    """What first_launch leaves behind: the profile file."""
    ecrire(r / "profile" / "profile.json", {"identite": {"nom": nom or r.name}})


def test_slug():
    assert P.slug("Chargée RSE (Lyon)") == "chargee-rse-lyon"
    assert P.slug("../..") == "profil"
    assert P.slug("a" * 39 + " b") == "a" * 39  # cut, never a trailing dash


def test_un_seul_profil_au_depart(principale):
    assert [p.slug for p in P.liste()] == [""]
    assert P.actif() == ""
    assert M.profil_affiche() == ""  # nothing in the sidebar


def test_creer_un_espace_complet_sans_les_cles(principale):
    r = P.creer("Chargée RSE à Lyon")
    assert r == principale / "profiles" / "chargee-rse-a-lyon"
    for d in ("data", "profile", "My_CV", "CV", "Letters"):
        assert (r / d).is_dir()
    assert json.loads((r / "data" / "sources_config.json").read_text(encoding="utf-8")) == {
        "entreprises": ["a"]
    }
    assert not (r / "data" / "adzuna.json").exists()
    # Not a profile until first_launch has written profile.json.
    assert [p.slug for p in P.liste()] == [""]
    with pytest.raises(FileExistsError):
        P.creer("chargee rse a lyon")


def test_nommer_puis_liste(principale):
    r = P.creer("Chargée RSE à Lyon")
    termine(r)
    P.nommer(r)
    assert not (r / "profile" / "_nom.txt").exists()
    profils = P.liste()
    assert [(p.slug, p.nom) for p in profils] == [
        ("", "Principal"),
        ("chargee-rse-a-lyon", "Chargée RSE à Lyon"),
    ]
    assert M.profil_affiche() == M.nom_affiche(profils[0])


def test_activer_et_actif(principale):
    r = P.creer("B")
    termine(r)
    P.activer("b")
    assert P.actif() == "b"
    assert P.racine_de("b") == r
    P.activer("")
    assert P.actif() == ""


def test_actif_ignore_un_profil_disparu_ou_un_chemin(principale):
    P.activer("disparu")
    assert P.actif() == ""
    ecrire(principale / "data" / P.FICHIER_ACTIF, {"profil": "../.."})
    assert P.actif() == ""
    with pytest.raises(ValueError):
        P.activer("../autre")


def test_appliquer_pointe_la_racine_vers_le_profil_actif(principale, monkeypatch):
    r = P.creer("B")
    termine(r)
    P.activer("b")
    assert P.appliquer() == r.resolve()
    assert os.environ["JOBHUNTER_RACINE"] == str(r)
    assert os.environ[P.ENV_PRINCIPALE] == str(principale.resolve())
    assert P.appliquer() == r.resolve()  # idempotent: still the same profile
    assert P.principale() == principale.resolve()
    # The keys stay in the main profile.
    assert root.dossier_cles() == principale.resolve() / "data"
    assert root.scripts() == r.resolve() / "data"


def test_cles_d_une_principale_en_ancienne_disposition(tmp_path, monkeypatch):
    p = tmp_path / "ancienne"
    ecrire(p / "profil" / "profil.json", {})
    ecrire(p / "Scripts" / "apply_queue.json", [])
    monkeypatch.setenv(P.ENV_PRINCIPALE, str(p))
    assert root.dossier_cles() == p.resolve() / "Scripts"


def test_pipeline_de_chaque_profil(principale, monkeypatch):
    b = P.creer("B")
    termine(b)
    vus = []

    def lancer(cmd, env, **kw):
        vus.append((env["JOBHUNTER_RACINE"], env[P.ENV_PRINCIPALE], cmd[-1]))
        return subprocess.CompletedProcess(cmd, 4 if "profiles" in env["JOBHUNTER_RACINE"] else 0)

    monkeypatch.setattr(daily_pipeline.subprocess, "run", lancer)
    assert daily_pipeline.tous_les_profils(P.liste()) == 4  # the worst code
    assert vus == [
        (str(principale.resolve()), str(principale.resolve()), "--un-profil"),
        (str(b), str(principale.resolve()), "--un-profil"),
    ]


def test_la_mise_a_jour_protege_les_profils():
    assert update.protege("profiles/b/data/applications.json")
    assert update.protege("profiles/b/profile/example_Facts.json")


class _App(M.ProfilsMixin):
    def __init__(self):
        self.root = _Racine()
        self.journal: list[str] = []

    def _log(self, txt):
        self.journal.append(txt)


class _Racine:
    detruite = False

    def destroy(self):
        self.detruite = True


def test_relancer_sur_la_principale(principale, monkeypatch):
    monkeypatch.setenv(P.ENV_PRINCIPALE, str(principale))
    app = _App()
    with patch.object(M.subprocess, "Popen") as popen:
        app._relancer()
    env = popen.call_args.kwargs["env"]
    assert env["JOBHUNTER_RACINE"] == str(principale.resolve())
    assert P.ENV_PRINCIPALE not in env  # the new process applies the active profile itself
    assert app.root.detruite


def test_questions_non_terminees_aucun_profil(principale):
    r = P.creer("B")
    app = _App()
    with patch.object(M.messagebox, "showwarning") as attention:
        app._profil_cree(r)
    assert attention.called and not r.exists()


def test_profil_cree_puis_ouvert(principale):
    r = P.creer("Bé")
    termine(r)
    app = _App()
    with (
        patch.object(M.messagebox, "askyesno", return_value=True),
        patch.object(M.subprocess, "Popen"),
    ):
        app._profil_cree(r)
    assert P.actif() == "be" and app.root.detruite
    assert [p.nom for p in P.liste()][1] == "Bé"


def test_changer_pour_le_profil_actif_ne_fait_rien(principale):
    app = _App()
    with patch.object(M.messagebox, "askyesno") as question:
        app._changer_profil("")
    assert not question.called
