"""A recorded application never disappears (queue_io, suivi_io, linkedin_closed).

Origin: linkedin_closed removed an offer the user had applied to,
because LinkedIn no longer accepted applications. Yet a posting closes almost
always AFTER one has applied to it. Converted from Scripts/test_applications.py.
"""

import pytest

from jobhunter.programs import linkedin_closed as L
from jobhunter.programs import util as jutil
from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io

# ── A. the tracker's key is the same everywhere ─────────────────────────────────────
OFFRE = {"entreprise": " Amundi ", "poste": " Analyste ESG "}


def test_cle_identique_linkedin_closed_et_queue_io():
    assert L._oid_offre(OFFRE) == queue_io.oid(OFFRE)


def test_cle_sans_espaces():
    assert queue_io.oid(OFFRE) == "Amundi|Analyste ESG"


# ── B. the tracker survives a rewrite of the queue ─────────────────────────────
@pytest.fixture
def file_reecrite(file_temporaire):
    with queue_io.transaction() as q:
        q.append(
            {"entreprise": "Amundi", "poste": "Analyste ESG", "fit": 9, "description": "z" * 500}
        )
    with queue_io.transaction() as q:  # scan, re-scoring, regeneration…
        q[0]["fit"] = 10
        q[0]["url"] = "https://autre-source.example/offre"
    return queue_io.charger()


SUIVI = {"Amundi|Analyste ESG": {"s": "postulé", "d": "2026-09-03"}}


def test_offre_garde_sa_cle(file_reecrite):
    assert queue_io.oid(file_reecrite[0]) in SUIVI


def test_suivi_pointe_toujours_dessus(file_reecrite):
    assert SUIVI[queue_io.oid(file_reecrite[0])]["s"] == "postulé"


def test_description_survit(file_reecrite):
    assert len(file_reecrite[0]["description"]) == 500


# ── C. automatic deletion: a tracked offer is SPARED ─────────────────
@pytest.fixture
def fermes():
    """linkedin_closed's sort: among the closed offers, the tracked ones do not go."""
    q = [
        {"entreprise": "Volkswagen", "poste": "Analyste Data"},  # suivie
        {"entreprise": "Zzz", "poste": "Analyste Quelconque"},
    ]  # non suivie
    res = {0: L.FERME, 1: L.FERME}
    suivis = {"Volkswagen|Analyste Data"}
    return [i for i, v in res.items() if v == L.FERME and L._oid_offre(q[i]) not in suivis]


def test_offre_suivie_epargnee(fermes):
    assert 0 not in fermes


def test_offre_non_suivie_supprimee(fermes):
    assert 1 in fermes


def test_une_seule_suppression(fermes):
    assert len(fermes) == 1


# ── C bis. two writers, no loss (suivi_io) ─────────────────────────────
# The app wrote its memory snapshot: one "postulé" click rewrote the WHOLE
# file and erased what relances.py had just put there (two follow-ups lost).
@pytest.fixture
def deux_ecrivains(tmp_path):
    f = tmp_path / "suivi.json"
    jutil.jwrite(
        f,
        {
            "Amundi|Analyste ESG": {"s": "postulé", "d": "2026-09-05"},
            "BNP Paribas|Analyste": {"s": "postulé", "d": "2026-09-06"},
        },
    )
    instantane = suivi_io.charger(f)  # what the app holds in memory
    suivi_io.modifier(  # relances.py records two follow-ups
        lambda s: [
            s.__setitem__(k, dict(s[k], s="relancé", relance="2026-09-17")) for k in list(s)
        ],
        f,
    )
    # then the app sets a NEW application from its stale snapshot
    suivi_io.poser("Sweep|ESG Analyst", {"s": "postulé", "d": "2026-09-17"}, f)
    return f, instantane, suivi_io.charger(f)


def test_les_deux_relances_survivent(deux_ecrivains):
    final = deux_ecrivains[2]
    assert sum(1 for v in final.values() if v.get("relance") == "2026-09-17") == 2


def test_nouvelle_candidature_presente(deux_ecrivains):
    assert "Sweep|ESG Analyst" in deux_ecrivains[2]


def test_trois_candidatures(deux_ecrivains):
    assert len(deux_ecrivains[2]) == 3


def test_instantane_de_l_app_perime(deux_ecrivains):
    assert len(deux_ecrivains[1]) == 2


def test_exception_au_milieu_n_ecrit_rien(deux_ecrivains):
    f = deux_ecrivains[0]
    avant = f.read_text(encoding="utf-8")
    with pytest.raises(RuntimeError), suivi_io.transaction(f) as s:
        s["Zzz|Casse"] = {"s": "ne doit pas survivre"}
        raise RuntimeError("panne au milieu")
    assert f.read_text(encoding="utf-8") == avant


# ── D. on REAL data: only on demand, in a user's repo ──
@pytest.mark.donnees_reelles
def test_aucune_candidature_orpheline():
    """Each application of the tracker points to an offer of the queue, or is marked
    `retiree` (row removed from the queue on purpose).  pytest -m donnees_reelles"""
    reel = suivi_io.charger()  # never a direct json.load (AGENTS.md)
    ids = {queue_io.oid(o) for o in queue_io.charger(descriptions=False)}
    assert [k for k in reel if k not in ids and not reel[k].get("retiree")] == []
