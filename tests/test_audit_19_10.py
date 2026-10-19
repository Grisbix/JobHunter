"""Les défauts de l'audit du 19/10/2026 (dépôt figé en 2.10.1), un test chacun.

Chaque test reproduit le scénario de l'audit sur des fichiers jetables et vérifie que
la donnée survit. Les quatre premiers sont des pertes de données (P1).
"""

import json
import queue

import pytest

from jobhunter import sources as J
from jobhunter.stockage import atomique, verrou
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io

# ── P1 — le contrôle des liens n'écrase plus une collecte concurrente ─────────


def test_controle_des_liens_garde_un_ajout_concurrent(tmp_path):
    from jobhunter.programmes import queue_tools

    f = tmp_path / "q.json"
    atomique.ecrire_json(f, [{"entreprise": "A", "poste": "x", "url": "https://a.test/1"}])

    def controle_pendant_qu_une_collecte_fusionne(urls):
        with queue_io.transaction(f, descriptions=False) as rows:
            rows.append({"entreprise": "B", "poste": "y", "url": "https://b.test/2"})
        return {u: {"live": True, "status": 200} for u in urls}

    queue_tools.mark_dead(f, verbose=False, _checker=controle_pendant_qu_une_collecte_fusionne)
    rows = json.loads(f.read_text(encoding="utf-8"))
    assert [r["entreprise"] for r in rows] == ["A", "B"]
    assert rows[0]["link_status"] == "OK"


def test_purge_des_liens_morts_epargne_le_suivi(tmp_path, suivi_temporaire):
    from jobhunter.programmes import queue_tools

    f = tmp_path / "q.json"
    atomique.ecrire_json(
        f,
        [
            {"entreprise": "A", "poste": "postulée", "link_status": "MORT"},
            {"entreprise": "B", "poste": "oubliée", "link_status": "MORT"},
        ],
    )
    suivi_io.poser("A|postulée", {"s": "postulé"})
    assert queue_tools.prune(f, verbose=False) == 1
    assert [r["entreprise"] for r in json.loads(f.read_text(encoding="utf-8"))] == ["A"]


# ── P1 — un suivi illisible n'est jamais remplacé ─────────────────────────────


@pytest.mark.parametrize("contenu", ['{"A|x": {"s": "postulé"}', "[]"])
def test_suivi_illisible_refuse_l_ecriture(suivi_temporaire, contenu):
    suivi_temporaire.write_text(contenu, encoding="utf-8")
    with pytest.raises(suivi_io.SuiviIllisible):
        suivi_io.poser("B|y", {"s": "postulé"})
    assert suivi_temporaire.read_text(encoding="utf-8") == contenu
    assert suivi_io.charger() == {}  # la lecture seule reste tolérante


def test_suivi_absent_se_cree(suivi_temporaire):
    suivi_io.poser("B|y", {"s": "postulé"})
    assert suivi_io.charger() == {"B|y": {"s": "postulé"}}


# ── P1 — une panne entre deux écritures ne perd aucune description ────────────


def test_panne_pendant_l_ecriture_de_la_file_garde_les_descriptions(file_temporaire, monkeypatch):
    with queue_io.transaction() as rows:
        rows += [
            {"entreprise": "A", "poste": "x", "description": "texte A"},
            {"entreprise": "B", "poste": "y", "description": "texte B"},
        ]
    vrai = atomique.ecrire_json

    def panne_sur_la_file(chemin, obj):
        if str(chemin) == str(file_temporaire):
            raise PermissionError("fichier verrouillé par l'antivirus")
        vrai(chemin, obj)

    monkeypatch.setattr(atomique, "ecrire_json", panne_sur_la_file)
    with pytest.raises(PermissionError), queue_io.transaction() as rows:
        rows[:] = [r for r in rows if r["entreprise"] == "A"]  # B retirée
    monkeypatch.setattr(atomique, "ecrire_json", vrai)
    # La file n'a pas changé : B y est encore, et sa description aussi.
    textes = {o["entreprise"]: o.get("description") for o in queue_io.charger()}
    assert textes == {"A": "texte A", "B": "texte B"}


def test_retrait_reussi_purge_l_orpheline(file_temporaire, tmp_path):
    with queue_io.transaction() as rows:
        rows += [
            {"entreprise": "A", "poste": "x", "description": "texte A"},
            {"entreprise": "B", "poste": "y", "description": "texte B"},
        ]
    with queue_io.transaction() as rows:
        rows[:] = [r for r in rows if r["entreprise"] == "A"]
    annexe = json.loads((tmp_path / "descriptions.json").read_text(encoding="utf-8"))
    assert annexe == {"A|x": "texte A"}


# ── P1 — la fusion ne retire pas une offre du suivi ───────────────────────────


@pytest.fixture
def file_de_fusion(tmp_path, monkeypatch, suivi_temporaire):
    q = tmp_path / "q.json"
    monkeypatch.setattr(J, "QUEUE", q)
    monkeypatch.setattr(J, "REJETS_TRI", tmp_path / "rej.json")
    return q


def test_fusion_garde_une_offre_suivie_que_le_filtre_rejette(file_de_fusion):
    titre = "Brand Design Intern"
    assert not J.title_ok(titre)  # le filtre d'intitulé la rejette bien
    atomique.ecrire_json(
        file_de_fusion,
        [
            {"entreprise": "Acme", "poste": titre, "statut": "Scan 2026-10-01"},
            {"entreprise": "Bruit", "poste": titre, "statut": "Scan 2026-10-01"},
        ],
    )
    suivi_io.poser(f"Acme|{titre}", {"s": "postulé"})
    bilan = J.merge_into_queue([], dry=False)
    rows = json.loads(file_de_fusion.read_text(encoding="utf-8"))
    assert [r["entreprise"] for r in rows] == ["Acme"]
    assert bilan["purged"] == 1


# ── P2 — une transaction imbriquée ne rend pas le verrou de son appelant ──────


def test_transaction_imbriquee_garde_le_verrou(file_temporaire):
    with queue_io.transaction(descriptions=False):
        with queue_io.transaction(descriptions=False):
            pass
        assert verrou.tenu(file_temporaire)
    assert not verrou.tenu(file_temporaire)


# ── P2 — une annonce reconnue par son URL reçoit sa description ───────────────


def test_offre_reconnue_par_url_est_enrichie(file_de_fusion):
    url = "https://www.linkedin.com/jobs/view/42"
    atomique.ecrire_json(
        file_de_fusion,
        [{"entreprise": "Mirova", "poste": "Analyste ESG", "url": url, "statut": "Scan x"}],
    )
    o = J._mk("Analyste ESG (H/F)", url, "Mirova", location="Paris")
    o["description"] = "Analyse ESG, reporting CSRD, SFDR, taxonomie, empreinte carbone. " * 5
    bilan = J.merge_into_queue([o], dry=False)
    rows = queue_io.charger(file_de_fusion)
    assert len(rows) == 1
    assert "CSRD" in (rows[0].get("description") or "")
    assert bilan["updated"] == 1


# ── P2 — « TOUT FAIRE terminé » seulement si tout a réussi ────────────────────


class _FausseApp:
    def __init__(self, reussites):
        self.q = queue.Queue()
        self._reussites = list(reussites)

    def _exec(self, cmd, label, announce=False):
        return self._reussites.pop(0)


@pytest.mark.parametrize(
    ("reussites", "attendu"), [([True, True], None), ([True, False], "Étape 2")]
)
def test_tout_faire_dit_l_etape_en_echec(reussites, attendu):
    from jobhunter.app.execution import ExecutionMixin

    app = _FausseApp(reussites)
    ExecutionMixin._exec_seq(app, [("Étape 1", ["a"]), ("Étape 2", ["b"])])  # type: ignore[arg-type]
    evenements = []
    while not app.q.empty():
        evenements.append(app.q.get())
    assert evenements[-1] == ("done_all", attendu)
