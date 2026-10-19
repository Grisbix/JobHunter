"""Engine logs (jobhunter.journal)."""

import logging

from jobhunter import journal


def test_la_console_affiche_le_message_seul_sur_la_sortie_du_moment(capsys):
    journal.journal("jobhunter.essai").info("LinkedIn : %d offres", 3)
    assert capsys.readouterr().out == "LinkedIn : 3 offres\n"


def test_un_nom_hors_paquet_est_range_sous_jobhunter():
    assert journal.journal("essai").name == "jobhunter.essai"


def test_configurer_ajoute_un_fichier_horodate(tmp_path, capsys):
    fichier = tmp_path / "moteur.log"
    racine = logging.getLogger(journal.RACINE)
    avant = list(racine.handlers)
    try:
        journal.configurer(fichier=fichier)
        journal.configurer(fichier=fichier)  # only once
        assert len(racine.handlers) == len(avant) + 1
        journal.journal("jobhunter.essai").warning("refus 403")
        for h in racine.handlers:
            h.flush()
        ligne = fichier.read_text(encoding="utf-8")
        assert "WARNING" in ligne and "jobhunter.essai : refus 403" in ligne
    finally:
        for h in racine.handlers[len(avant) :]:
            h.close()
            racine.removeHandler(h)
    capsys.readouterr()
