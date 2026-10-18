"""Acces concurrent a la file (queue_io).

Le module existe pour rendre impossible l'oubli du verrou : on verifie surtout
ce qui doit ARRIVER quand deux programmes se marchent dessus. Converti depuis
Scripts/test_queue_io.py.
"""

import json
import subprocess
import sys

import pytest
from conftest import SCRIPTS

import jutil
import queue_io


@pytest.fixture
def q(tmp_path):
    f = tmp_path / "q.json"
    f.write_text(json.dumps([{"entreprise": "A", "fit": 1}]), encoding="utf-8")
    return f


def autre_processus(chemin):
    """Un AUTRE processus tente de prendre le verrou ; rend « True » ou « False »."""
    sonde = (
        f"import sys, pathlib; sys.path.insert(0, r'{SCRIPTS}'); import jutil;"
        f"print(jutil.prendre_verrou(pathlib.Path(r'{chemin}'), attente=2, bavard=False))"
    )
    r = subprocess.run([sys.executable, "-c", sonde], capture_output=True, text=True)
    jutil_rendu = r.stdout.strip()
    if jutil_rendu == "True":
        jutil.rendre_verrou(chemin)  # la sonde laisse le verrou derriere elle
    return jutil_rendu


# ── A. lecture et ecriture ─────────────────────────────────────────────────────
def test_charger(q):
    assert queue_io.charger(q) == [{"entreprise": "A", "fit": 1}]


def test_fichier_absent_liste_vide(tmp_path):
    assert queue_io.charger(tmp_path / "rien.json") == []


def test_transaction_ecrit(q):
    with queue_io.transaction(q) as offres:
        offres[0]["fit"] = 9
    assert queue_io.charger(q)[0]["fit"] == 9


# ── B. le verrou est pris pendant le bloc ──────────────────────────────────────
def test_autre_processus_bloque_pendant(q):
    with queue_io.transaction(q):
        assert autre_processus(q) == "False"


def test_autre_processus_passe_apres(q):
    with queue_io.transaction(q):
        pass
    assert autre_processus(q) == "True"


# ── C. une exception n'ecrit rien ──────────────────────────────────────────────
def _transaction_qui_casse(q):
    with pytest.raises(ValueError), queue_io.transaction(q) as offres:
        offres.append({"entreprise": "NE DOIT PAS ETRE ECRIT"})
        raise ValueError("boum")


def test_file_inchangee_apres_exception(q):
    avant = queue_io.charger(q)
    _transaction_qui_casse(q)
    assert queue_io.charger(q) == avant


def test_verrou_relache_malgre_exception(q):
    _transaction_qui_casse(q)
    assert autre_processus(q) == "True"


# ── D. relecture fraiche DANS le verrou ────────────────────────────────────────
@pytest.fixture
def ecrit_par_un_autre(q):
    """Un autre programme ecrit pendant qu'on ne tient pas encore le verrou."""
    queue_io.charger(q)  # copie perimee, qui ne doit pas servir
    q.write_text(json.dumps([{"entreprise": "ECRIT_PAR_UN_AUTRE", "fit": 5}]), encoding="utf-8")
    vu = {}
    with queue_io.transaction(q) as offres:
        vu["entreprise"] = offres[0]["entreprise"]
        offres[0]["fit"] = 7
    return q, vu


def test_transaction_voit_l_etat_frais(ecrit_par_un_autre):
    assert ecrit_par_un_autre[1]["entreprise"] == "ECRIT_PAR_UN_AUTRE"


def test_travail_de_l_autre_conserve(ecrit_par_un_autre):
    assert queue_io.charger(ecrit_par_un_autre[0])[0]["entreprise"] == "ECRIT_PAR_UN_AUTRE"


def test_notre_modification_ecrite(ecrit_par_un_autre):
    assert queue_io.charger(ecrit_par_un_autre[0])[0]["fit"] == 7


# ── E, F ───────────────────────────────────────────────────────────────────────
def test_modifier_renvoie_la_valeur(q):
    assert queue_io.modifier(lambda offres: len(offres), chemin=q) == 1


def test_le_nom_du_module_ne_masque_pas_la_stdlib():
    import queue as stdlib_queue

    assert hasattr(stdlib_queue, "Queue")


# ── G. descriptions dans un fichier annexe (vrais chemins du module, rediriges) ─
@pytest.fixture
def deux_offres(file_temporaire):
    with queue_io.transaction() as offres:
        offres.extend(
            [
                {
                    "entreprise": "Amundi",
                    "poste": "Analyste ESG",
                    "fit": 9,
                    "description": "x" * 4000,
                },
                {"entreprise": "BNP", "poste": "Analyste Risque", "fit": 7, "description": ""},
            ]
        )
    return file_temporaire


def _annexe():
    return json.loads(queue_io.DESCRIPTIONS.read_text(encoding="utf-8"))


def test_file_sans_descriptions(deux_offres):
    brut = json.loads(queue_io.CHEMIN.read_text(encoding="utf-8"))
    assert not any("description" in o for o in brut)


def test_annexe_contient_les_descriptions(deux_offres):
    assert len(_annexe()) == 1


def test_file_pese_moins_que_l_annexe(deux_offres):
    assert queue_io.CHEMIN.stat().st_size < queue_io.DESCRIPTIONS.stat().st_size


def test_charger_reinjecte(deux_offres):
    assert len(queue_io.charger()[0]["description"]) == 4000


def test_chemin_relatif_vers_la_file_reinjecte(deux_offres, monkeypatch):
    # Path("apply_queue.json") lance depuis le dossier de la file : meme fichier que
    # CHEMIN, ecrit autrement. Compare tel quel, les descriptions disparaissaient.
    monkeypatch.chdir(deux_offres.parent)
    assert len(queue_io.charger(queue_io.Path("apply_queue.json"))[0]["description"]) == 4000


def test_chemin_relatif_garde_la_file_sans_descriptions(deux_offres, monkeypatch):
    monkeypatch.chdir(deux_offres.parent)
    queue_io.sauver(queue_io.charger(), queue_io.Path("apply_queue.json"))
    brut = json.loads(queue_io.CHEMIN.read_text(encoding="utf-8"))
    assert not any("description" in o for o in brut)


def test_description_vide_non_stockee(deux_offres):
    assert queue_io.charger()[1].get("description", "") == ""


@pytest.fixture
def aller_retour(deux_offres):
    with queue_io.transaction() as offres:
        offres[0]["fit"] = 10
    return queue_io.charger()


def test_aller_retour_conserve_la_description(aller_retour):
    assert len(aller_retour[0]["description"]) == 4000


def test_aller_retour_conserve_la_modification(aller_retour):
    assert aller_retour[0]["fit"] == 10


@pytest.fixture
def amundi_supprimee(deux_offres):
    with queue_io.transaction() as offres:
        del offres[0]
    return deux_offres


def test_description_orpheline_purgee(amundi_supprimee):
    assert _annexe() == {}


def test_descriptions_false_n_injecte_rien(amundi_supprimee):
    assert "description" not in queue_io.charger(descriptions=False)[0]


@pytest.fixture
def ecriture_sans_descriptions(amundi_supprimee):
    """LE CHEMIN DANGEREUX : ecrire sans avoir lu l'annexe. Si la purge des
    orphelines s'appliquait la, elle ne verrait aucune description vivante et
    effacerait tout. BNP (sans description) puis Mirova (avec) pour le prouver."""
    with queue_io.transaction() as offres:
        offres.append(
            {"entreprise": "Mirova", "poste": "Analyste", "fit": 8, "description": "y" * 3000}
        )
    avant = _annexe()
    with queue_io.transaction(descriptions=False) as offres:
        offres[0]["fit"] = 3  # on ne touche a aucune description
    return avant


def test_une_description_en_place(ecriture_sans_descriptions):
    assert len(ecriture_sans_descriptions) == 1


def test_ecriture_sans_descriptions_n_efface_rien(ecriture_sans_descriptions):
    assert _annexe() == ecriture_sans_descriptions


def test_champ_modifie_ecrit(ecriture_sans_descriptions):
    assert queue_io.charger()[0]["fit"] == 3


def test_description_de_mirova_survit(ecriture_sans_descriptions):
    assert len(queue_io.charger()[1]["description"]) == 3000
