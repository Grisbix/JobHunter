"""One follow-up threshold everywhere; `collect --fusion-seule` on a folder never scanned."""

import inspect

from jobhunter.programs import follow_ups, weekly_metrics
from jobhunter.storage import applications
from jobhunter.web import api


def test_un_seul_seuil_de_relance():
    # The app said 7 days, `jobhunter relances` and the weekly metrics 10 (2026-11-11).
    assert applications.JOURS_RELANCE == 7  # the first draft is the J+7 template
    assert api.JOURS_RELANCE == applications.JOURS_RELANCE
    assert weekly_metrics.RELANCE_JOURS == applications.JOURS_RELANCE
    defaut = inspect.signature(follow_ups.a_relancer).parameters["days"].default
    assert defaut == applications.JOURS_RELANCE


def test_fusion_seule_sans_scan_ne_plante_pas(tmp_path, monkeypatch, capsys):
    from jobhunter.sources import cli

    monkeypatch.setattr(cli, "FRESH", tmp_path / "scanned_offers.json")
    assert cli.main(["--fusion-seule"]) == 0
    assert "Aucun scan à fusionner" in capsys.readouterr().out
