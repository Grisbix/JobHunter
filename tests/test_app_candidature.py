"""Panneau « Candidatures » de l'application (app/candidature.py), sans fenêtre.

Lecture des événements du programme, textes affichés, commandes transmises seulement
quand le programme attend, et déclaration manuelle « déclaré » (ADR 0009).
"""

import io
from unittest.mock import patch

import pytest

from jobhunter.app import actions as _actions
from jobhunter.app import candidature as cand
from jobhunter.app import fenetre as ui


class Etiquette:
    def __init__(self):
        self.vu = {}

    def configure(self, **k):
        # comme un CTkLabel : la couleur du texte est text_color, `fg` leve ValueError
        assert "fg" not in k, "CTkLabel.configure ne connait pas fg"
        self.vu.update(k)


class Bouton(Etiquette):
    def __init__(self):
        super().__init__()
        self.vu["state"] = "disabled"

    def cget(self, cle):
        return self.vu[cle]


class Proc:
    def __init__(self):
        self.stdin = io.StringIO()

    def poll(self):
        return None


@pytest.fixture
def app():
    a = object.__new__(ui.App)
    a._cand_lbl = {z: Etiquette() for z in ("offre", "etat", "resultat")}
    a._cand_boutons = [Bouton() for _ in range(4)]
    a._cand_proc = Proc()
    return a


# ── événements ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("ligne", "attendu"),
    [
        ('@JH {"type": "offre", "i": 1}', {"type": "offre", "i": 1}),
        ("  📝 couverture 80 %", None),  # ligne de journal
        ("@JH {pas du json", None),
        ('@JH {"sans": "type"}', None),
    ],
)
def test_lire_evenement(ligne, attendu):
    assert cand.lire_evenement(ligne) == attendu


def test_texte_offre():
    zone, texte, _ = cand.texte_evenement(
        {"type": "offre", "i": 2, "total": 5, "entreprise": "Acme", "poste": "Analyste"}
    )
    assert zone == "offre" and texte == "2/5 · Acme — Analyste"


def test_texte_pret_dit_que_le_clic_est_a_l_utilisateur():
    zone, texte, _ = cand.texte_evenement(
        {"type": "pret", "couverture": 87, "documents": "cv, lettre", "bouton": "Envoyer"}
    )
    assert zone == "etat" and "87 %" in texte and "clique « Envoyer » toi-même" in texte


def test_texte_incertain_ne_promet_aucun_renvoi():
    _, texte, _ = cand.texte_evenement(
        {"type": "resultat", "etat": "incertain", "texte": "formulaire toujours affiché"}
    )
    assert "Rien ne sera renvoyé" in texte and "formulaire toujours affiché" in texte


def test_evenement_inconnu_n_affiche_rien():
    assert cand.texte_evenement({"type": "attente"}) is None


# ── le panneau ───────────────────────────────────────────────────────────────
def test_boutons_actifs_seulement_quand_le_programme_attend(app):
    app._cand_evenement({"type": "offre", "i": 1, "total": 1, "entreprise": "A", "poste": "P"})
    assert app._cand_boutons[0].vu["state"] == "disabled"
    app._cand_evenement({"type": "attente"})
    assert all(b.vu["state"] == "normal" for b in app._cand_boutons)


def test_commande_ignoree_si_le_programme_travaille(app):
    app._cand_commande("envoye")
    assert app._cand_proc.stdin.getvalue() == ""


def test_commande_transmise_puis_boutons_coupes(app):
    app._cand_evenement({"type": "attente"})
    app._cand_commande("envoye")
    assert app._cand_proc.stdin.getvalue() == "envoye\n"
    assert app._cand_boutons[0].vu["state"] == "disabled"  # pas de double déclaration


def test_resultat_recharge_le_suivi(app):
    with (
        patch.object(cand.suivi_io, "charger", return_value={"x": 1}) as charger,
        patch.object(ui.App, "refresh_table") as rafraichir,
    ):
        app._cand_evenement({"type": "resultat", "etat": "confirmé", "texte": "Merci"})
    charger.assert_called_once()
    rafraichir.assert_called_once()
    assert app.suivi == {"x": 1}


# ── déclaration manuelle et fiche ─────────────────────────────────────────────
def test_confirmation_manuelle_ecrit_declare():
    a = object.__new__(ui.App)
    a.root, a._annuler = None, []
    offre = {"entreprise": "Acme", "poste": "Analyste"}
    with (
        patch.object(_actions.messagebox, "askyesno", return_value=True),
        patch.object(_actions.suivi_io, "charger", return_value={}),
        patch.object(_actions.suivi_io, "declarer_envoi") as declarer,
        patch.object(ui.App, "refresh_table"),
        patch.object(ui.App, "_log"),
    ):
        a._postuler(offre)
    assert declarer.call_args.args == ("Acme|Analyste", "déclaré")


def test_fiche_dit_l_etat_de_la_preuve():
    a = object.__new__(ui.App)
    a.suivi = {
        "Acme|Analyste": {
            "s": "postulé",
            "d": "2026-10-19",
            "envoi": "incertain",
            "preuve": {"texte": "formulaire toujours affiché", "capture": "p.png"},
        }
    }
    lignes = a._etat_candidature({"entreprise": "Acme", "poste": "Analyste"})
    assert (
        lignes[0]
        == "Candidature : postulé le 2026-10-19 · envoi NON confirmé par le site (à vérifier)"
    )
    assert "p.png" in lignes[2]


# ── contrôle du dossier (documents.controle) ──────────────────────────────────
def test_texte_dossier_pret():
    zone, texte, _ = cand.texte_evenement({"type": "dossier", "problemes": []})
    assert zone == "dossier" and texte.startswith("Dossier vérifié")


def test_texte_dossier_a_revoir():
    _, texte, couleur = cand.texte_evenement(
        {"type": "dossier", "problemes": ["lettre n'est pas un PDF : l.docx"]}
    )
    assert "à revoir" in texte and "l.docx" in texte and couleur == cand.BAD


def test_fiche_sans_dossier_ne_dit_rien():
    a = object.__new__(ui.App)
    assert a._etat_dossier({"entreprise": "Acme", "poste": "P"}) == []
