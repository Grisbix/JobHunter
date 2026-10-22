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


# ── 3.5: names in a registry, rename, archive, the `profiles` command ──────────


def test_nommer_ne_reecrit_pas_le_profil(principale):
    r = P.creer("Chargée RSE")
    termine(r)
    avant = (r / "profile" / "profile.json").read_bytes()
    P.nommer(r)
    assert (r / "profile" / "profile.json").read_bytes() == avant
    assert P.trouver("chargée rse").slug == "chargee-rse"


def test_renommer_garde_le_dossier(principale):
    r = P.creer("B")
    termine(r)
    P.renommer("b", "  Analyste   Lyon ")
    P.renommer("", "Moi")
    assert [(p.slug, p.nom) for p in P.liste()] == [("", "Moi"), ("b", "Analyste Lyon")]
    assert r.is_dir()
    with pytest.raises(ValueError):
        P.renommer("inconnu", "x")
    with pytest.raises(ValueError):
        P.renommer("b", "   ")


def test_archiver_deplace_sans_supprimer(principale):
    r = P.creer("B")
    termine(r)
    (r / "data" / "apply_queue.json").write_text("[1]", encoding="utf-8")
    P.renommer("b", "Second")
    P.activer("b")
    dest = P.archiver("b")
    assert not r.exists() and (dest / "data" / "apply_queue.json").read_text() == "[1]"
    assert dest.parent.name == P.ARCHIVES
    assert [p.slug for p in P.liste()] == [""]  # archives are not profiles
    assert P.actif() == ""
    with pytest.raises(ValueError):
        P.archiver("")  # the main profile


def test_archiver_refuse_pendant_une_collecte(principale, monkeypatch):
    r = P.creer("B")
    termine(r)
    from jobhunter.storage import lock

    monkeypatch.setattr(lock, "prendre_verrou", lambda *a, **k: False)
    with pytest.raises(RuntimeError):
        P.archiver("b")
    assert r.is_dir()


def test_commande_profiles(principale, monkeypatch, capsys):
    from jobhunter.programs import profiles_cli as C

    r = P.creer("B")
    termine(r)

    def lancer(*args):
        monkeypatch.setattr("sys.argv", ["jobhunter profiles", *args])
        return C.main()

    assert lancer() == 0 and "(principal)" in capsys.readouterr().out
    assert lancer("use", "b") == 0 and P.actif() == "b"
    assert lancer("rename", "b", "Second") == 0 and P.trouver("Second").slug == "b"
    assert lancer("archive", "Principal") == 1
    assert lancer("archive", "second") == 0 and P.actif() == ""
    with pytest.raises(SystemExit):
        lancer("use", "inconnu")


def test_commande_new_sans_reponses_ne_laisse_rien(principale, monkeypatch, tmp_path, capsys):
    from jobhunter.programs import profiles_cli as C

    cv = tmp_path / "cv.docx"
    cv.write_bytes(b"PK")
    monkeypatch.setattr(C.subprocess, "run", lambda *a, **k: None)  # questions abandoned
    monkeypatch.setattr("sys.argv", ["jobhunter profiles", "new", str(cv), "--name", "C"])
    assert C.main() == 1
    assert not (principale / "profiles" / "c").exists()


def test_nom_actif_meme_seul(principale):
    """The sidebar names the active profile even when it is the only one (3.18.1)."""
    assert M.nom_actif() == M.nom_affiche(P.liste()[0])
    r = P.creer("Chargée RSE à Lyon")
    termine(r)
    P.nommer(r)
    P.activer("chargee-rse-a-lyon")
    assert M.nom_actif() == "Chargée RSE à Lyon"


def test_lanceur_sans_profil_actif_relance(principale):
    """An old launcher that skips appliquer() opened the main profile whatever was chosen.

    The app now notices it and relaunches itself through `python -m jobhunter.app`.
    """
    from jobhunter.app import window

    with patch.object(subprocess, "Popen") as lancer:
        assert window._hors_profil_actif() is False  # main profile active: nothing to do
        r = P.creer("B")
        termine(r)
        P.activer("b")
        assert window._hors_profil_actif() is True
        cmd = lancer.call_args.args[0]
        assert cmd[1:] == ["-m", "jobhunter.app"]
        assert lancer.call_args.kwargs["env"]["JOBHUNTER_RACINE"] == str(principale)
        lancer.reset_mock()
        os.environ[P.ENV_PRINCIPALE] = str(principale)  # applied by the launcher
        try:
            assert window._hors_profil_actif() is False
        finally:
            del os.environ[P.ENV_PRINCIPALE]
        lancer.assert_not_called()


def test_changer_de_profil_relance_tout_de_suite(principale):
    """Choosing a profile opens it at once (no question), except while a task runs."""
    r = P.creer("B")
    termine(r)
    app = object.__new__(M.ProfilsMixin)
    app._profil_ouvert = ""
    app.root = None
    app.proc = None
    with patch.object(M.ProfilsMixin, "_relancer") as relancer:
        app._changer_profil("")  # the open one: nothing
        relancer.assert_not_called()
        app.proc = type("Proc", (), {"poll": lambda self: None})()  # a task running
        with patch.object(M.messagebox, "showinfo") as dire:
            app._changer_profil("b")
        dire.assert_called_once()
        relancer.assert_not_called()
        assert P.actif() == ""
        app.proc = None
        app._changer_profil("b")
        relancer.assert_called_once()
        assert P.actif() == "b"
