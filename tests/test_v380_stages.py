"""3.80: an internship said in the posting's text is an internship.

Crédit Agricole writes « Vous recherchez un stage en finance durable ? » and labels the
job CDD: four such internships were first of the queue at fit 10 (2026-11-03), while
the user excludes Stage and Alternance.
"""

import pytest

from jobhunter.scoring import sorting
from jobhunter.sources import common as C

CA = "Vous recherchez un stage en Finance Durable ? Alors postulez ! " + "Missions. " * 10


@pytest.mark.parametrize(
    "texte",
    [
        CA,
        "Profil : vous recherchez un stage de 6 mois à partir de janvier.",
        "La Direction Financière recherche un stagiaire motivé et autonome.",
        "Inclusive business (H/F) Stage de 6 mois à débuter en janvier 2027.",
        "Join us for a 6-month internship in our ESG team.",
        "This internship is based in Paris.",
    ],
)
def test_offre_de_stage(texte):
    assert C.offre_de_stage(texte)


@pytest.mark.parametrize(
    "texte",
    [
        "Ce poste ne s'adresse pas aux personnes recherchant une alternance avec une école.",
        "CDD de 12 mois. Le poste est également ouvert à un stage de 6 mois.",
        "Après un premier stage en banque, vous maîtrisez Excel.",
        "Analyste ESG en CDI, deux ans d'expérience.",
    ],
)
def test_pas_une_offre_de_stage(texte):
    assert not C.offre_de_stage(texte)


def test_le_contrat_lu_dans_le_texte_est_stage():
    assert C.contrat_de_la_description(CA + "Contrat : CDD") == "Stage"


def _offre(**kw):
    return {
        "poste": "Analyste Sustainable Investment Banking H/F",
        "entreprise": "CA",
        "url": "https://x/1",
        **kw,
    }


def test_le_tri_retire_un_stage_exclu(monkeypatch):
    monkeypatch.setattr(sorting, "_CONTRATS_EXCLUS", {"Stage", "Alternance"})
    assert sorting.motif(_offre(description=CA, contrat="CDD"), set()) == "contrat_exclu"
    assert sorting.motif(_offre(contrat="Stage"), set()) == "contrat_exclu"


def test_le_tri_garde_le_stage_si_rien_n_est_exclu(monkeypatch):
    monkeypatch.setattr(sorting, "_CONTRATS_EXCLUS", set())
    assert sorting.motif(_offre(description=CA, contrat="CDD"), set()) is None


def test_une_candidature_n_est_jamais_retiree(monkeypatch):
    from jobhunter.storage.queue import oid

    monkeypatch.setattr(sorting, "_CONTRATS_EXCLUS", {"Stage"})
    o = _offre(description=CA)
    assert sorting.motif(o, {oid(o)}) is None


def test_le_contrat_se_lit_dans_une_description_arrivee_apres():
    o = {"contrat": "non precise", "description": "Poste en CDI basé à Paris. " * 5}
    C.completer_contrat(o)
    assert o["contrat"] == "CDI"
    o = {"contrat": "V.I.E", "description": "Poste en CDI basé à Paris. " * 5}
    C.completer_contrat(o)
    assert o["contrat"] == "V.I.E"  # an announced contract is never overwritten


def test_doublon_meme_ville_ecrite_avec_ou_sans_trait_d_union():
    """3.80: « Le-Relecq-Kerhuon » and « Le Relecq-Kerhuon » are one place."""
    from jobhunter.programs import duplicates

    titre = "Consolideur - reporting extra-financier H/F"
    file = [
        {
            "entreprise": "Crédit Mutuel Arkea",
            "poste": titre,
            "localisation": "Le Relecq-Kerhuon, Bretagne",
            "fit": 7,
            "url": "https://a.fr/1",
        },
        {
            "entreprise": "CREDIT MUTUEL ARKEA",
            "poste": titre.replace("H/F", "F/H"),
            "localisation": "Le-Relecq-Kerhuon",
            "fit": 10,
            "url": "https://a.fr/2",
        },
    ]
    assert len(duplicates.doublons(file)) == 1


def test_maj_attend_le_pipeline_entre_ses_etapes(tmp_path, monkeypatch):
    """3.80: the pipeline gives the queue back between its steps; its own lock
    (_pipeline) keeps the update out until it ends."""
    import subprocess
    import sys
    import time
    from types import SimpleNamespace

    from jobhunter.programs import update

    donnees = tmp_path / "data"
    donnees.mkdir()
    monkeypatch.setattr(update._profils, "liste", lambda r: [SimpleNamespace(racine=tmp_path)])
    # Another process holds the pipeline's lock, as daily_pipeline does for its run.
    code = (
        "import sys, time; from jobhunter.storage import lock; "
        f"lock.prendre_verrou(r'{donnees / '_pipeline'}'); print('pris', flush=True); time.sleep(60)"
    )
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == "pris"
        monkeypatch.setattr(
            update._verrou, "prendre_verrou", _sans_attente(update._verrou.prendre_verrou)
        )
        assert update.file_libre(garder=False) is False
    finally:
        p.kill()
        p.wait()
    time.sleep(0.2)
    assert update.file_libre(garder=False) is True  # its owner dead: free again


def _sans_attente(prendre):
    return lambda chemin, attente=0, **k: prendre(chemin, attente=0, **k)


@pytest.fixture
def maj_pip(tmp_path, monkeypatch):
    """The pip package's update with the network, pip and the lock replaced."""
    from jobhunter.programs import update

    etat = {"installee": "3.78.0", "charge": True, "installs": []}
    monkeypatch.setattr(update, "PAQUET_AVANT", tmp_path / ".maj_paquet_avant")
    monkeypatch.setattr(update, "version_paquet", lambda: etat["installee"])
    monkeypatch.setattr(update, "version_proposee", lambda t: "3.79.0")
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(
        update, "paquet_charge", lambda: etat["charge"] or etat["installee"] == "3.78.0"
    )

    def installer(version, locale):
        etat["installs"].append(version)
        etat["installee"] = version
        return 0

    monkeypatch.setattr(update, "installer_paquet", installer)
    return update, etat


def test_maj_pip_installe_et_note_la_version_d_avant(maj_pip):
    update, etat = maj_pip
    assert update.maj_paquet(False) == 0
    assert etat["installs"] == ["3.79.0"]
    assert update.PAQUET_AVANT.read_text(encoding="utf-8") == "3.78.0"


def test_maj_pip_qui_ne_se_charge_pas_revient_a_l_ancienne(maj_pip):
    update, etat = maj_pip
    etat["charge"] = False
    assert update.maj_paquet(False) == 1
    assert etat["installs"] == ["3.79.0", "3.78.0"] and etat["installee"] == "3.78.0"


def test_annuler_pip_remet_la_version_d_avant(maj_pip):
    update, etat = maj_pip
    assert update.annuler_paquet() == 1  # nothing to undo yet
    update.maj_paquet(False)
    assert update.annuler_paquet() == 0
    assert etat["installee"] == "3.78.0" and not update.PAQUET_AVANT.exists()


def test_main_annuler_va_au_paquet_pip(monkeypatch):
    from jobhunter.programs import update

    monkeypatch.setattr(update, "paquet_pip", lambda: True)
    monkeypatch.setattr(update, "annuler_paquet", lambda: 42)
    assert update.main(["--annuler"]) == 42
