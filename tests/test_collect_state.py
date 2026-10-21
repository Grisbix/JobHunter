"""The state of the morning collection (jobhunter.collect_state) and the pipeline that
writes it: a collection missed, interrupted or stopped must be visible."""

import sys
import time

import pytest

from jobhunter import collect_state as E
from jobhunter.programs import daily_pipeline as dp

FMT = E.FORMAT
MAINTENANT = time.mktime(time.strptime("2026-10-21 13:00:00", FMT))


def il_y_a(heures):
    return time.strftime(FMT, time.localtime(MAINTENANT - heures * 3600))


def diag(etat, vivant=lambda pid, depuis: False):
    return E.diagnostic(etat, maintenant=MAINTENANT, vivant=vivant)


@pytest.fixture
def fichier(tmp_path, monkeypatch):
    f = tmp_path / E.FICHIER
    monkeypatch.setattr(E, "_chemin", lambda chemin=None: chemin or f)
    return f


# ── what the application says ───────────────────────────────────────────────


def test_rien_enregistre_a_lancer():
    d = diag({})
    assert d.niveau == "retard" and d.a_relancer


def test_collecte_du_matin_fraiche():
    d = diag({"etat": "ok", "dernier_succes": il_y_a(5)})
    assert d.niveau == "ok" and not d.a_relancer
    assert d.texte == "Collecte du matin : aujourd'hui 08:00 ✓"


def test_etapes_en_erreur_ne_font_pas_un_echec():
    """Code 1 = one step failed, eight mornings out of ten: the collection happened."""
    d = diag({"etat": "ok", "code": 1, "dernier_succes": il_y_a(5), "erreurs": ["dossiers"]})
    assert d.niveau == "ok"
    assert d.texte.endswith("· en erreur : dossiers")


def test_matin_manque():
    """21/10/2026: the task did not start; the last success is from the day before."""
    d = diag({"etat": "ok", "dernier_succes": il_y_a(28)})
    assert d.niveau == "retard" and d.a_relancer
    assert d.texte == "Pas de collecte depuis hier 09:00"


def test_en_cours():
    d = diag({"etat": "en_cours", "debut": il_y_a(1), "pid": 4}, vivant=lambda p, s: True)
    assert d.niveau == "en_cours" and not d.a_relancer
    assert "aujourd'hui 12:00" in d.texte


def test_interrompue_processus_mort():
    etat = {"etat": "en_cours", "debut": il_y_a(1), "pid": 4, "dernier_succes": il_y_a(29)}
    d = diag(etat)
    assert d.niveau == "echec" and d.a_relancer
    assert "interrompue" in d.texte and "dernière réussie : hier 08:00" in d.texte


def test_arretee_puis_trop_vieille_devient_retard():
    etat = {"etat": "echec", "fin": il_y_a(2), "erreurs": ["file occupée par un autre programme"]}
    assert diag(etat).niveau == "echec"
    assert "file occupée" in diag(etat).texte
    etat["fin"] = il_y_a(30)
    assert diag(etat).niveau == "retard"


def test_traduit():
    tr = {"Collecte du matin : {a} ✓": "Morning collection: {a} ✓", "aujourd'hui {a}": "today {a}"}
    d = E.diagnostic(
        {"etat": "ok", "dernier_succes": il_y_a(5)},
        maintenant=MAINTENANT,
        tr=lambda s: tr.get(s, s),
    )
    assert d.texte == "Morning collection: today 08:00 ✓"


# ── the file ────────────────────────────────────────────────────────────────


def test_debut_fin_garde_le_dernier_succes(fichier):
    E.debut("20261021-0800-abcd", "journal.log")
    d = E.lire()
    assert d["etat"] == "en_cours" and d["execution"] == "20261021-0800-abcd"
    E.fin(1, ["dossiers"])
    d = E.lire()
    assert d["etat"] == "ok" and d["code"] == 1 and d["erreurs"] == ["dossiers"]
    succes = d["dernier_succes"]
    E.debut("suivante")
    E.plantage("KeyboardInterrupt")
    d = E.lire()
    assert d["etat"] == "echec" and d["dernier_succes"] == succes


def test_fichier_illisible(fichier):
    fichier.write_text("{abîmé", encoding="utf-8")
    assert E.lire() == {}
    E.debut("x")  # and writing still works
    assert E.lire()["etat"] == "en_cours"


# ── the pipeline writes it ──────────────────────────────────────────────────


@pytest.fixture
def pipeline(tmp_path, fichier, monkeypatch):
    monkeypatch.setattr(dp, "SCRIPTS", tmp_path)
    monkeypatch.setattr(sys, "stdout", sys.stdout)  # main() wraps it in its log
    monkeypatch.setenv("JOBHUNTER_JOURNAL", "")
    monkeypatch.setattr(dp._profils, "liste", lambda: [])

    def lancer(executer, *args):
        monkeypatch.setattr(dp, "_executer", executer)
        monkeypatch.setattr(sys, "argv", ["pipeline", "--un-profil", *args])
        return dp.main()

    return lancer


def test_pipeline_termine_avec_erreurs(pipeline):
    assert pipeline(lambda a, j: (1, ["collecte 1"])) == 1
    d = E.lire()
    assert d["etat"] == "ok" and d["erreurs"] == ["collecte 1"] and d["dernier_succes"]


def test_pipeline_file_occupee(pipeline):
    assert pipeline(lambda a, j: (3, ["file occupée par un autre programme"])) == 3
    d = E.lire()
    assert d["etat"] == "echec" and "dernier_succes" not in d


def test_pipeline_plante(pipeline):
    def boum(a, j):
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        pipeline(boum)
    assert E.lire()["etat"] == "echec" and E.lire()["erreurs"] == ["RuntimeError"]


def test_essai_rapide_ne_compte_pas(pipeline):
    assert pipeline(lambda a, j: (0, []), "--rapide") == 0
    assert E.lire() == {}
