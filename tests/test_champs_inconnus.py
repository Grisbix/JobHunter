"""Fields the engine does not know survive a read followed by a write.

A newer version may add a field that an older one does not know: the older one must
carry it unchanged, never drop it. Offers and applications are plain JSON dicts, and
every write goes through `transaction`, which rewrites what it read.
"""

from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io

INCONNU = {"version": 3, "liste": [1, "deux"], "imbrique": {"cle": None}}


def test_la_file_garde_un_champ_inconnu(file_temporaire):
    with queue_io.transaction() as q:
        q[:] = [{"entreprise": "A", "poste": "a", "champ_futur": INCONNU, "description": "t"}]
    with queue_io.transaction() as q:
        q[0]["fit"] = 9  # an ordinary write by another program
    o = queue_io.charger()[0]
    assert o["champ_futur"] == INCONNU and o["fit"] == 9 and o["description"] == "t"


def test_le_suivi_garde_un_champ_inconnu(suivi_temporaire):
    suivi_io.poser("A|a", {"s": "postulé", "d": "2026-10-19", "champ_futur": INCONNU})
    suivi_io.poser("B|b", {"s": "postulé", "d": "2026-10-20"})
    suivi_io.declarer_envoi("A|a", "déclaré")
    assert suivi_io.charger()["A|a"]["champ_futur"] == INCONNU
