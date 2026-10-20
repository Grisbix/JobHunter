"""Restoring the queue from a backup (programmes.restaurer), on throwaway files.

Inspection writes nothing; the tracker is never restored and its offers stay; no
description is lost; the state before is copied, so a restoration can be undone.
"""

import json

from jobhunter.programs import restore as r
from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io


def _offre(e, p, desc=""):
    o = {"entreprise": e, "poste": p, "url": f"https://ex.org/{e}/{p}", "fit": 7}
    if desc:
        o["description"] = desc
    return o


def _ecrire(chemin, obj):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _situation(file_temporaire, suivi_temporaire):
    """Current queue: A, C (tracked), D. Daily backup: A, B with B's text in its annex."""
    with queue_io.transaction() as q:
        q[:] = [_offre("A", "a", "texte A"), _offre("C", "c", "texte C"), _offre("D", "d")]
    suivi_io.poser("C|c", {"s": "postulé", "d": "2026-10-19"})
    jour = file_temporaire.parent / "_sauvegardes" / "2026-10-19"
    _ecrire(jour / "apply_queue.json", [_offre("A", "a"), _offre("B", "b")])
    _ecrire(jour / "descriptions.json", {"B|b": "texte B"})


def test_liste_les_trois_sortes_de_sauvegardes(file_temporaire):
    base = file_temporaire.parent
    _ecrire(base / "_sauvegardes" / "2026-10-18" / "apply_queue.json", [])
    _ecrire(base / "_sauvegardes" / "2026-10-19_avant_audit" / "apply_queue.json", [])
    _ecrire(base / "apply_queue.json.avant_tri_20261019_092812", [])
    (base / "_sauvegardes" / "vide").mkdir()  # no queue: ignored
    noms = [s.nom for s in r.sauvegardes()]
    assert noms[0] == "avant_tri_20261019_092812"
    assert set(noms) == {"2026-10-18", "2026-10-19_avant_audit", "avant_tri_20261019_092812"}
    assert noms[-1] == "2026-10-18"


def test_plan_garde_les_offres_suivies():
    courantes = [_offre("A", "a"), _offre("C", "c"), _offre("D", "d")]
    anciennes = [_offre("A", "a"), _offre("B", "b")]
    resultat, revenues, parties, gardees = r.plan(courantes, anciennes, {"C|c"})
    assert [queue_io.oid(o) for o in resultat] == ["A|a", "B|b", "C|c"]
    assert revenues == ["B|b"] and parties == ["D|d"] and gardees == ["C|c"]


def test_inspection_n_ecrit_rien(file_temporaire, suivi_temporaire, capsys):
    _situation(file_temporaire, suivi_temporaire)
    avant = file_temporaire.read_bytes()
    assert r.main(["2026-10-19"]) == 0
    assert file_temporaire.read_bytes() == avant
    sortie = capsys.readouterr().out
    assert "+ B|b" in sortie and "- D|d" in sortie and "rien n'a été écrit" in sortie
    assert not list((file_temporaire.parent / "_sauvegardes").glob("*_avant_restauration"))


def test_restauration_appliquee(file_temporaire, suivi_temporaire):
    _situation(file_temporaire, suivi_temporaire)
    suivi_avant = suivi_temporaire.read_bytes()
    assert r.main(["2026-10-19", "--appliquer"]) == 0
    offres = {queue_io.oid(o): o for o in queue_io.charger()}
    assert set(offres) == {"A|a", "B|b", "C|c"}
    # descriptions: from the backup's annex, otherwise from the current one
    assert offres["B|b"]["description"] == "texte B"
    assert offres["A|a"]["description"] == "texte A"
    assert offres["C|c"]["description"] == "texte C"
    # the tracker is untouched
    assert suivi_temporaire.read_bytes() == suivi_avant


def test_une_restauration_s_annule(file_temporaire, suivi_temporaire):
    _situation(file_temporaire, suivi_temporaire)
    r.main(["2026-10-19", "--appliquer"])
    copies = list((file_temporaire.parent / "_sauvegardes").glob("*_avant_restauration"))
    assert len(copies) == 1
    assert r.main([copies[0].name, "--appliquer"]) == 0
    assert {queue_io.oid(o) for o in queue_io.charger()} == {"A|a", "C|c", "D|d"}
    assert {queue_io.oid(o): o.get("description") for o in queue_io.charger()}["A|a"] == "texte A"


def test_sauvegarde_inconnue_ou_illisible(file_temporaire, suivi_temporaire, capsys):
    assert r.main(["2026-01-01"]) == 2
    _ecrire(file_temporaire.parent / "_sauvegardes" / "2026-10-19" / "apply_queue.json", {})
    assert r.main(["2026-10-19", "--appliquer"]) == 2
    assert not file_temporaire.exists()


def test_liste_vide(file_temporaire, capsys):
    assert r.main(["--liste"]) == 0
    assert "Aucune sauvegarde" in capsys.readouterr().out
