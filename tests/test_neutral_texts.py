"""3.49: the first launch speaks the interface's language; nothing assumes finance or France."""

from jobhunter.programs import first_launch as fl


def test_questions_en_anglais_hors_interface_francaise(monkeypatch):
    from jobhunter.web import i18n

    monkeypatch.setattr(i18n, "langue", lambda: "en")
    assert fl._t("Prénom") == "First name"
    assert fl._t("Villes ou secteurs de préférence (séparés par des virgules)").startswith(
        "Preferred"
    )
    # A text without translation stays as it is.
    assert fl._t("texte inconnu") == "texte inconnu"


def test_questions_en_francais_pour_une_interface_francaise(monkeypatch):
    from jobhunter.web import i18n

    monkeypatch.setattr(i18n, "langue", lambda: "fr")
    assert fl._t("Prénom") == "Prénom"


def test_chaque_texte_traduit_est_bien_affiche():
    """Every key of _EN is a text first_launch really shows (no stale translation)."""
    import inspect

    src = inspect.getsource(fl.main) + inspect.getsource(fl.demander_prive)
    for fr in fl._EN:
        debut = fr.strip("\n ")[:25]  # long texts are split over source lines
        assert debut in src, fr


def test_oui_accepte_o_et_y():
    assert fl._oui("o") and fl._oui("Oui") and fl._oui("y") and fl._oui(" Yes")
    assert not fl._oui("n") and not fl._oui("no") and not fl._oui("")


def test_filtre_efc_esg_seulement_pour_un_profil_esg(monkeypatch):
    from jobhunter import profile as _P
    from jobhunter.sources import cli

    monkeypatch.setattr(
        _P,
        "get",
        lambda cle, d=None: ["re:\\b(esg|csr)\\b"] if cle == "scoring.intitules_coeur" else d,
    )
    assert cli._vise_esg()
    monkeypatch.setattr(
        _P,
        "get",
        lambda cle, d=None: ["financial analyst"] if cle == "scoring.intitules_coeur" else d,
    )
    assert not cli._vise_esg()
    monkeypatch.setattr(_P, "get", lambda cle, d=None: d)
    assert not cli._vise_esg()


def test_bilan_de_fusion_sans_france():
    import inspect

    from jobhunter.programs import scrape_jobs
    from jobhunter.sources import cli

    for m in (cli, scrape_jobs):
        assert "hors de France" not in inspect.getsource(m)
