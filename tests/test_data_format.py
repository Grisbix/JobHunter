"""An older JobHunter never writes over data of a newer format (storage.data_format)."""

import json

import pytest

from jobhunter.storage import applications as suivi_io
from jobhunter.storage import data_format as F
from jobhunter.storage import queue as queue_io


def test_premiere_ecriture_note_le_format(tmp_path):
    q = tmp_path / "q.json"
    queue_io.sauver([{"entreprise": "A", "poste": "B"}], q)
    assert F.lire(tmp_path) == F.FORMAT


def test_format_plus_recent_rien_n_est_ecrit(tmp_path):
    q = tmp_path / "q.json"
    q.write_text("[]", encoding="utf-8")
    (tmp_path / F.FICHIER).write_text(json.dumps({"format": F.FORMAT + 1}))
    with pytest.raises(F.FormatPlusRecent):
        queue_io.sauver([{"entreprise": "A", "poste": "B"}], q)
    assert q.read_text(encoding="utf-8") == "[]"
    assert queue_io.charger(q) == []  # reading stays allowed


def test_suivi_protege_aussi(tmp_path):
    s = tmp_path / "suivi.json"
    s.write_text("{}", encoding="utf-8")
    (tmp_path / F.FICHIER).write_text(json.dumps({"format": F.FORMAT + 1}))
    with pytest.raises(F.FormatPlusRecent):
        with suivi_io.transaction(s) as suivi:
            suivi["A|B"] = {"s": "postulé"}
    assert s.read_text(encoding="utf-8") == "{}"


def test_format_illisible_ignore(tmp_path):
    (tmp_path / F.FICHIER).write_text("{abîmé")
    F.verifier_ecriture(tmp_path)  # no exception
