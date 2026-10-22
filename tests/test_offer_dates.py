"""The offers table's dates: published, found, last seen alive (app.table)."""

import datetime

from jobhunter.app.table import _jj_mm, _verifiee

ANNEE = datetime.date.today().year


def test_jj_mm():
    assert _jj_mm(f"{ANNEE}-10-08") == "08/10"
    assert _jj_mm("2025-12-31") == ("31/12/25" if ANNEE != 2025 else "31/12")
    assert _jj_mm("") == "" and _jj_mm(None) == ""
    assert _jj_mm(f"{ANNEE}-10-08T09:30") == "08/10"


def test_verifiee_la_plus_recente_des_deux():
    assert _verifiee({"ls_check": "2026-10-21", "vu_le": "2026-10-22"}) == "2026-10-22"
    assert _verifiee({"ls_check": "2026-10-21T08:00"}) == "2026-10-21"
    assert _verifiee({}) == ""
