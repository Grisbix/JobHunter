"""Every status change is kept (storage.applications.historiser) and read back (funnel)."""

import datetime

from jobhunter import funnel
from jobhunter.storage import applications as suivi_io

JOUR = datetime.date.today().isoformat()


def test_historique_ecrit_par_toute_transaction(tmp_path):
    p = tmp_path / "suivi.json"
    suivi_io.poser("A|X", {"s": "postulé", "d": "2026-10-01"}, p)
    assert suivi_io.charger(p)["A|X"]["h"] == [["2026-10-01", "postulé"]]

    def refus(s):
        s["A|X"]["s"] = "refus"  # a writer that changes the status but not the date

    suivi_io.modifier(refus, p)
    assert suivi_io.charger(p)["A|X"]["h"] == [["2026-10-01", "postulé"], [JOUR, "refus"]]


def test_note_seule_n_ajoute_rien(tmp_path):
    p = tmp_path / "suivi.json"
    suivi_io.poser("A|X", {"s": "postulé", "d": "2026-10-01"}, p)

    def note(s):
        s["A|X"]["n"] = "relancé par téléphone"

    suivi_io.modifier(note, p)
    assert len(suivi_io.charger(p)["A|X"]["h"]) == 1


def test_entree_d_avant_l_historique_garde_son_premier_statut(tmp_path):
    p = tmp_path / "suivi.json"
    p.write_text('{"A|X": {"s": "postulé", "d": "2026-09-03"}}', encoding="utf-8")

    def entretien(s):
        s["A|X"].update(s="entretien", d="2026-09-20")  # date of the email

    suivi_io.modifier(entretien, p)
    assert suivi_io.charger(p)["A|X"]["h"] == [
        ["2026-09-03", "postulé"],
        ["2026-09-20", "entretien"],
    ]


def test_annuler_ne_double_pas(tmp_path):
    p = tmp_path / "suivi.json"
    suivi_io.poser("A|X", {"s": "postulé", "d": "2026-10-01"}, p)
    avant = suivi_io.charger(p)["A|X"]
    suivi_io.poser("A|X", {**avant, "s": "pas intéressé"}, p)
    suivi_io.poser("A|X", avant, p)  # Ctrl+Z: the entry as it was, its history with it
    assert suivi_io.charger(p)["A|X"]["h"] == [["2026-10-01", "postulé"]]


def test_entonnoir():
    jour = datetime.date(2026, 11, 30)
    suivi = {
        "A|1": {"s": "entretien", "h": [["2026-10-01", "postulé"], ["2026-10-08", "entretien"]]},
        "B|2": {"s": "refus", "h": [["2026-10-01", "postulé"], ["2026-10-21", "refus"]]},
        "C|3": {"s": "postulé", "d": "2026-10-02"},  # silent for two months
        "D|4": {"s": "postulé", "d": "2026-11-25"},  # recent: waiting, not silent
        "E|5": {"s": "refus", "d": "2026-09-15"},  # before the history: no delay
        "F|6": {"s": "pas intéressé", "d": "2026-10-01"},  # never sent
    }
    offres = {"A|1": {"contrat": "V.I.E"}, "B|2": {"contrat": "V.I.E"}, "C|3": {"contrat": "CDI"}}
    e = funnel.entonnoir(suivi, offres, jour)
    assert (e["envoyees"], e["reponses"], e["entretiens"], e["refus"]) == (5, 3, 1, 2)
    assert e["delais"] == [7, 20] and e["delai_median"] == 13.5
    assert e["silence"] == 1
    assert sorted(e["par"]["contrat"]) == [("CDI", 1, 0, 0), ("V.I.E", 2, 2, 1), ("—", 2, 1, 0)]
