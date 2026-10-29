"""3.70: data safety found by the audit of 2026-10-29.

Per-thread lock ownership, strict tracker reads in deletion guards, applied offers
kept by the web window, a cleared status keeping the note, complete daily backups,
the descriptions annex never rewritten from an empty read.
"""

import json
import threading
import time
from pathlib import Path

import pytest

from jobhunter.programs import daily_pipeline
from jobhunter.storage import applications, lock
from jobhunter.storage import queue as queue_io
from jobhunter.web import api

RACINE = Path(__file__).resolve().parent.parent
JS = (RACINE / "src" / "jobhunter" / "web" / "static" / "app.js").read_text(encoding="utf-8")


# --- lock: one owner per thread ---------------------------------------------------------


def test_un_autre_fil_attend_le_verrou(tmp_path):
    f = tmp_path / "file.json"
    assert lock.prendre_verrou(f, attente=1)
    vu = {}

    def autre():
        vu["pris"] = lock.prendre_verrou(f, attente=0.3)
        vu["tenu"] = lock.tenu(f)
        lock.rendre_verrou(f)  # not its own: must not release the first thread's lock

    t = threading.Thread(target=autre)
    t.start()
    t.join()
    assert vu == {"pris": False, "tenu": False}
    assert lock.tenu(f) and lock._fverrou(f).exists()
    # reentrant in the owning thread
    assert lock.prendre_verrou(f, attente=0)
    lock.rendre_verrou(f)
    assert not lock._fverrou(f).exists()


def test_le_second_fil_l_obtient_une_fois_rendu(tmp_path):
    f = tmp_path / "file.json"
    assert lock.prendre_verrou(f, attente=1)
    vu = {}

    def autre():
        debut = time.time()
        vu["pris"] = lock.prendre_verrou(f, attente=5)
        vu["attendu"] = time.time() - debut
        lock.rendre_verrou(f)

    t = threading.Thread(target=autre)
    t.start()
    time.sleep(0.3)
    lock.rendre_verrou(f)
    t.join()
    assert vu["pris"] and vu["attendu"] >= 0.2
    assert not lock._fverrou(f).exists()


def test_deux_ecritures_concurrentes_gardent_les_deux(tmp_path):
    f = tmp_path / "file.json"
    f.write_text("[]", encoding="utf-8")

    def ajouter(n):
        for i in range(10):
            with queue_io.transaction(f, attente=10) as q:
                q.append({"entreprise": f"E{n}", "poste": str(i)})

    fils = [threading.Thread(target=ajouter, args=(n,)) for n in range(3)]
    for t in fils:
        t.start()
    for t in fils:
        t.join()
    assert len(json.loads(f.read_text(encoding="utf-8"))) == 30


# --- strict tracker read ---------------------------------------------------------------


def test_lecture_stricte(tmp_path):
    s = tmp_path / "applications.json"
    s.write_text("{pas du json", encoding="utf-8")
    assert applications.charger(s) == {}
    with pytest.raises(applications.SuiviIllisible):
        applications.charger(s, strict=True)
    assert applications.charger(tmp_path / "absent.json", strict=True) == {}


def test_prune_refuse_un_suivi_illisible(monkeypatch, tmp_path):
    from jobhunter.programs import queue_tools

    q = tmp_path / "q.json"
    q.write_text(json.dumps([{"entreprise": "A", "poste": "B", "link_status": "MORT"}]), "utf-8")
    monkeypatch.setattr(
        applications,
        "charger",
        lambda *a, **k: (_ for _ in ()).throw(applications.SuiviIllisible("illisible")),
    )
    with pytest.raises(applications.SuiviIllisible):
        queue_tools.prune(q, verbose=False)
    assert len(json.loads(q.read_text("utf-8"))) == 1


# --- web window: applied offers stay, a cleared status keeps the note ------------------


def test_hors_suivi(monkeypatch):
    monkeypatch.setattr(applications, "charger", lambda *a, **k: {"A|B": {"s": "postulé"}})
    assert api._hors_suivi({"A|B", "C|D"}) == ({"C|D"}, 1)


def test_supprimer_garde_les_candidatures(monkeypatch):
    monkeypatch.setattr(applications, "charger", lambda *a, **k: {"A|B": {"s": "postulé"}})
    r = api.Api().supprimer(["A|B"])
    assert not r["ok"] and "candidature" in r["erreur"]
    r = api.Api().ecarter(["A|B"], "trop loin")
    assert not r["ok"] and "candidature" in r["erreur"]


def test_supprimer_refuse_un_suivi_illisible(monkeypatch):
    def boom(*a, **k):
        raise applications.SuiviIllisible("applications.json illisible")

    monkeypatch.setattr(applications, "charger", boom)
    r = api.Api().supprimer(["A|B"])
    assert not r["ok"] and "illisible" in r["erreur"]


def test_vider_le_statut_garde_la_note(monkeypatch):
    a = api.Api()
    vu = {}
    monkeypatch.setattr(a, "_connue", lambda i: True)
    monkeypatch.setattr(a, "_ecrire_suivi", lambda ch: vu.update(ch) or {"ok": True})
    a.marquer("A|B", "")
    rec = vu["A|B"]({"s": "postulé", "d": "2026-10-01", "n": "relancer lundi", "envoi": "x"})
    assert rec == {"n": "relancer lundi", "envoi": "x"}
    assert vu["A|B"]({"s": "postulé", "d": "2026-10-01"}) == {}


def test_js_attrape_les_erreurs():
    assert "try { r = await window.pywebview.api[nom](...args); }" in JS
    assert "try { r = await enregistrer(); }" in JS
    assert "finally { if (b) b.disabled = false; }" in JS


# --- daily backup ----------------------------------------------------------------------


def _pipeline(monkeypatch, tmp_path):
    scripts = tmp_path / "data"
    scripts.mkdir()
    for nom in daily_pipeline._A_SAUVER:
        (scripts / nom).write_text("[]", encoding="utf-8")
    monkeypatch.setattr(daily_pipeline, "SCRIPTS", scripts)
    monkeypatch.setattr(daily_pipeline._racine, "dans", lambda base, nom: base / nom)
    return scripts / "_sauvegardes"


def test_sauvegarde_partielle_completee(monkeypatch, tmp_path):
    from jobhunter.storage import backups

    base = _pipeline(monkeypatch, tmp_path)
    jour = base / time.strftime("%Y-%m-%d")
    jour.mkdir(parents=True)
    (jour / "apply_queue.json").write_text("ancienne", encoding="utf-8")
    daily_pipeline.sauvegarder()
    for nom in daily_pipeline._A_SAUVER:
        assert backups.fichier(jour, nom), nom
    # the one already there is never replaced: the first of the day wins
    assert backups.lire_texte(backups.fichier(jour, "apply_queue.json")) == "ancienne"


def test_rotation_par_jours_seulement(monkeypatch, tmp_path):
    base = _pipeline(monkeypatch, tmp_path)
    for j in range(1, 10):
        (base / f"2026-01-{j:02d}").mkdir(parents=True)
    (base / "2026-01-01_avant_audit").mkdir()
    (base / "2026-01-09_avant_audit").mkdir()
    daily_pipeline.sauvegarder(garder=7)
    noms = sorted(p.name for p in base.iterdir())
    jours = [n for n in noms if len(n) == 10]
    assert len(jours) == 7 and time.strftime("%Y-%m-%d") in jours
    assert "2026-01-09_avant_audit" in noms and "2026-01-01_avant_audit" not in noms


# --- descriptions annex ------------------------------------------------------------------


def test_texte_ajoute_sans_lire_l_annexe(monkeypatch, tmp_path):
    q = tmp_path / "apply_queue.json"
    d = tmp_path / "descriptions.json"
    q.write_text(json.dumps([{"entreprise": "A", "poste": "B"}, {"entreprise": "C", "poste": "D"}]))
    d.write_text(json.dumps({"A|B": "texte de A"}))
    monkeypatch.setattr(queue_io, "CHEMIN", q)
    monkeypatch.setattr(queue_io, "DESCRIPTIONS", d)
    monkeypatch.setattr(queue_io, "_est_la_file", lambda p: Path(p) == q)
    with queue_io.transaction(q, descriptions=False) as offres:
        offres[1]["description"] = "texte de C"
    assert json.loads(d.read_text()) == {"A|B": "texte de A", "C|D": "texte de C"}
