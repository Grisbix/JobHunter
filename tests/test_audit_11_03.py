"""3.76: defects found by the code audit of 2026-11-03, one test per ticket.

Each case was first reproduced on the 3.75 engine (essay or real queue); the test pins
the fixed behaviour.
"""


# --- 01: the Tk app removed applied offers ---------------------------------------------


# --- 05: react_submit sent the page's first form ----------------------------------------

import js_app


def test_react_submit_ne_touche_que_le_bon_formulaire():
    import pytest

    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    from jobhunter.navigation.account import react_submit

    candidature = (
        '<form id="cand" onsubmit="window.envoi=\'candidature\';return false">'
        '<input name="nom"><input type="file" name="cv"></form>'
    )
    recherche = (
        '<form id="rech" onsubmit="window.envoi=\'recherche\';return false">'
        '<input data-wn-search="1" name="q"></form>'
    )
    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True)
        try:
            page = navigateur.new_page()
            # No filled email, no marked field: nothing leaves (3.75 sent « cand »).
            page.set_content(candidature)
            assert react_submit(page) is False
            assert page.evaluate("window.envoi || ''") == ""
            # The search fallback submits the search form, never the application.
            page.set_content(candidature + recherche)
            assert react_submit(page, '[data-wn-search="1"]') is True
            assert page.evaluate("window.envoi") == "recherche"
            # A search box inside an application form: refused.
            page.set_content(
                "<form onsubmit=\"window.envoi='x';return false\">"
                '<input data-wn-search="1"><textarea></textarea></form>'
            )
            page.evaluate("window.envoi = ''")
            assert react_submit(page, '[data-wn-search="1"]') is False
            assert page.evaluate("window.envoi || ''") == ""
        finally:
            navigateur.close()


# --- 06: « Ajouter une offre » overwrote another offer's documents -----------------------


def test_ajout_manuel_nomme_sans_collision(file_temporaire, monkeypatch):
    import jobhunter.documents as documents
    from jobhunter.programs import add_offer
    from jobhunter.storage import queue as queue_io

    poste = "Auditeur junior analyste financier et extra-financier ESG"
    queue_io.sauver(
        [
            {"entreprise": "Deloitte", "poste": poste + " - Bordeaux", "url": "https://a/1"},
            {"entreprise": "Deloitte", "poste": poste + " - Toulouse", "url": "https://a/2"},
        ],
        file_temporaire,
    )
    monkeypatch.setattr(add_offer, "QUEUE", file_temporaire)
    vus = {}
    monkeypatch.setattr(
        documents, "cv_une_page", lambda offer, nom=None, **k: (vus.setdefault("cv", nom), None)
    )
    monkeypatch.setattr(
        documents, "tailor_letter", lambda offer, nom=None, **k: vus.setdefault("lt", nom)
    )
    monkeypatch.setattr(documents, "to_pdf", lambda lt: None)
    assert add_offer.make_docs("https://a/2") == "docs générés"
    # same truncated name for both offers: the second one is numbered
    assert vus["cv"].endswith("_2") and vus["lt"].endswith("_2")
    lien = next(o for o in queue_io.charger(file_temporaire) if o["url"] == "https://a/2")
    assert lien["cv"] and lien["lettre"]
    # the queue file does not carry the descriptions back
    assert not any("description" in o for o in queue_io.charger(descriptions=False))


# --- 10: two programs both broke the same orphan lock -----------------------------------


def test_verrou_change_de_main_pas_casse(tmp_path):
    from jobhunter.storage import lock

    f = tmp_path / "file.json"
    v = lock._fverrou(f)
    v.write_text("999999 1", encoding="utf-8")
    vus = v.read_text(encoding="utf-8").split()
    # Meanwhile another program broke it and set its own (live) lock.
    v.write_text(f"{__import__('os').getpid()} 2", encoding="utf-8")
    assert lock._casser_si_inchange(v, vus) is False
    assert v.exists()
    # Unchanged: broken, and the breaker's file is gone.
    assert lock._casser_si_inchange(v, v.read_text(encoding="utf-8").split()) is True
    assert not v.exists() and not (tmp_path / "file.json.lock.casse").exists()


def test_cassage_en_cours_attend(tmp_path):
    from jobhunter.storage import lock

    v = lock._fverrou(tmp_path / "file.json")
    v.write_text("999999 1", encoding="utf-8")
    (tmp_path / "file.json.lock.casse").write_text("", encoding="utf-8")
    assert lock._casser_si_inchange(v, ["999999", "1"]) is False
    assert v.exists()


# --- 11: linkedin_closed read a truncated tracker as « no application » -----------------


def test_linkedin_closed_suivi_illisible(tmp_path, monkeypatch):
    from jobhunter.programs import linkedin_closed

    suivi = tmp_path / "applications.json"
    suivi.write_text('{"A|B": {"s": "post', encoding="utf-8")
    monkeypatch.setattr(linkedin_closed, "SUIVI", suivi)
    assert linkedin_closed._oids_suivis() is None
    suivi.write_text('{"A|B": {"s": "postulé"}}', encoding="utf-8")
    assert linkedin_closed._oids_suivis() == {"A|B"}


# --- 12: the toast promised « Annuler », nothing called annulerGeste --------------------


def test_annuler_est_branche():
    import re

    js = js_app.source()
    appels = [m.start() for m in re.finditer(r"annulerGeste\b", js)]
    definition = js.index("async function annulerGeste")
    assert [a for a in appels if a != definition + len("async function ")], "jamais appelé"
    assert '["Annuler", annulerGeste]' in js and 'e.key === "z"' in js


# --- 15: application forms: wrong fields filled, third-party consent ticked -------------

_PROFIL_15 = {
    "email": "g@x.fr", "prenom": "Camille", "nom": "EXEMPLE", "tel": "0600000000",
    "ville": "Paris", "pays": "France", "site_web": "https://site.fr",
    "message": "Lettre…", "niveau_etudes": "Bac+5 (Master)", "date_naissance": "01/01/2000",
    "adresse": "1 rue X",
}  # fmt: skip

_FORM_15 = """<form>
<div class=form-group><label for=a>Numéro de sécurité sociale</label><input id=a></div>
<div class=form-group><label for=b>Numéro de passeport</label><input id=b></div>
<div class=form-group><label for=c>Profil Facebook</label><input id=c></div>
<div class=form-group><label for=d>Comment avez-vous connu notre entreprise ?</label><input id=d></div>
<div class=form-group><label for=e>Nom de votre employeur actuel</label><input id=e></div>
<div class=form-group><label for=f>Mot de passe (identifiant)</label><input id=f type=password></div>
<div class=form-group><label for=g>Nom du référent / manager</label><input id=g></div>
<div class=form-group><label for=h>Niveau d'études</label><select id=h><option value="">--</option>
  <option value="ba">Bachelor</option><option value="ma">Master</option></select></div>
<div class=form-group><label for=i>Numéro de rue</label><input id=i></div>
<div class=form-group><label for=j>Ville de naissance</label><input id=j></div>
<div class=form-group><label for=m>IBAN</label><input id=m></div>
<div class=form-group><label for=n>Handicap / RQTH (commentaire)</label><input id=n></div>
<div class=form-group><label for=t>Téléphone</label><input id=t></div>
<div class=form-group><label for=v>Ville</label><input id=v></div>
<label><input type=checkbox id=o> J'accepte que mes données soient transmises à des tiers</label>
<label><input type=checkbox id=q> J'accepte les CGU</label>
</form>"""


def test_formulaire_ne_remplit_que_les_bons_champs():
    import pytest

    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    from jobhunter.navigation import forms

    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True)
        try:
            page = navigateur.new_page()
            page.set_content(_FORM_15)
            forms.fill_application(page, _PROFIL_15)
            valeur = {
                i: page.evaluate(f"document.getElementById('{i}').value") for i in "abcdefgijmntv"
            }
            assert {k: v for k, v in valeur.items() if v} == {"t": "0600000000", "v": "Paris"}
            assert page.evaluate("document.getElementById('h').value") == "ma"
            assert not page.evaluate("document.getElementById('o').checked")
            assert page.evaluate("document.getElementById('q').checked")
            # the separate consent pass follows the same rule
            page.set_content(_FORM_15)
            assert forms.accept_consent(page) == 1
            assert not page.evaluate("document.getElementById('o').checked")
        finally:
            navigateur.close()


def test_consentement_regle():
    from jobhunter.navigation.forms import consentement_a_cocher as c

    assert c("j'accepte les conditions generales d'utilisation", False)
    assert c("j'accepte le traitement de mes donnees pour ma candidature", True)
    assert not c("j'accepte le traitement de mes donnees pour ma candidature", False)
    assert not c("j'accepte que mes donnees soient transmises a des tiers", True)
    assert not c("i agree to share my data with partners", True)
    assert not c("j'accepte de recevoir la newsletter", True)
    assert c("j'ai lu la procedure de recrutement et j'accepte", False)


# --- 16: required experience read from the firm, the team or a preference --------------


def test_experience_exigee():
    from jobhunter.scoring.fit import experience_detail, experience_years

    cas = {
        "Cabinet de conseil fort de 12 ans d'expérience, nous recrutons. "
        "Profil : première expérience bienvenue.": 0,
        "Une équipe de 15 consultants cumulant 10 ans d'expérience en moyenne.": 0,
        "You will join a team with an average of 8 years of experience.": 0,
        "Minimum 2 years of experience required, ideally 5 years of experience.": 2,
        "Expérience souhaitée : 2 ans (5 ans d'expérience appréciés).": 2,
        "Depuis 10 ans, notre expérience au service des investisseurs fait référence.": 0,
        "Accompagner nos clients ayant plus de 10 ans d'expérience. Profil : 1 an d'expérience.": 1,
        # still read
        "What we are looking for 4+ years of experience in AI engineering": 4,
        "Vous avez au moins 5 ans d'expérience en gestion d'actifs.": 5,
        "Au sein de notre équipe, vous justifiez de 7 ans d'expérience.": 7,
        "Highly preferred work experience 3+ years of experience in equity research": 3,
    }
    for texte, attendu in cas.items():
        assert experience_years(texte) == attendu, texte
    n, extrait = experience_detail("Vous avez au moins 5 ans d'expérience en gestion d'actifs.")
    assert n == 5 and "5 ans" in extrait


def test_rejet_garde_l_extrait(tmp_path):
    import datetime

    from jobhunter.programs import sort_rejections

    f = tmp_path / "rejets.json"
    sort_rejections.ajouter(
        {"A|B": "experience", "C|D": "seniorite"},
        f,
        datetime.date(2026, 11, 3),
        extraits={"A|B": "au moins 5 ans d'expérience"},
    )
    d = sort_rejections.charger(f, datetime.date(2026, 11, 3))
    assert d["A|B"]["x"] == "au moins 5 ans d'expérience" and "x" not in d["C|D"]


# --- 17: seniority read in « Business Partner », « junior ou confirmé »… -----------------


def test_seniorite_mots_neutres():
    from jobhunter.scoring import sorting

    def m(titre):
        return sorting.motif(
            {"poste": titre, "entreprise": "X", "url": "https://x/" + titre}, set()
        )

    for titre in (
        "Finance Business Partner",
        "V.I.E - Finance Business Partner",
        "Analyste ESG junior ou confirmé (H/F)",
        "Kreditanalyst Junior & Senior (m/w/d)",
        "Chargé de mission auprès du Directeur Financier",
        "Executive Assistant to the Chief Investment Officer",
        "ESG Analyst - Principal Investments team",
    ):
        assert m(titre) != "seniorite", titre
    for titre in ("Senior ESG Analyst", "Director, Sustainable Finance", "Partner - Deal Advisory"):
        assert m(titre) == "seniorite", titre


# --- 18: an unknown place was « France, prioritaire » ------------------------------------


def test_lieux_etrangers_reconnus():
    from jobhunter.scoring import zones

    for lieu in (
        "Bratislava, SK",
        "Gelang Patah, Johor Darul Ta'zim, my",
        "港区, 東京都",
        "US-Tennessee-Piney Flats",
        "CAN, ON, Mississauga",
        "Carapicuíba, SP, Brasil",
        "Pohnpei, Micronesia, Federated States of",
        "Dortmund",
        "Gurugram",
        "Ebene",
        "Monaco",
    ):
        assert zones.zone_france(lieu) == zones.INTERNATIONAL, lieu
    assert zones.pays_lieu("Bruxelles") == "Belgique"
    for lieu in ("Puteaux", "Maisons-Alfort", "Valence, Drôme", "Paris, FR", "Lyon"):
        assert zones.pays_lieu(lieu) == "France", lieu


def test_outils_gardes_sur_l_offre(monkeypatch):
    """19 : les outils d'une description inchangée ne sont pas recherchés deux fois."""
    from jobhunter.scoring import sorting as S

    o = {"description": "Python, SQL and Tableau daily."}
    attendu = S.outils_techniques(o["description"])
    assert S._outils_offre(o) == attendu
    assert o["outils_vus"]["o"] == sorted(attendu)
    appels = []
    monkeypatch.setattr(S, "outils_techniques", lambda t: appels.append(t) or set())
    assert S._outils_offre(o) == attendu and not appels
    o["description"] = "Excel only."
    S._outils_offre(o)
    assert appels == ["Excel only."]
    vide = {"description": ""}
    S._outils_offre(vide)
    assert "outils_vus" not in vide


def test_dossier_donnees_suit_documents_connu(tmp_path, monkeypatch):
    """13 : sans ancien dossier, l'appli installée suit le Documents de Windows."""
    from jobhunter import frozen

    monkeypatch.delenv("JOBHUNTER_RACINE", raising=False)
    monkeypatch.setattr(frozen.Path, "home", lambda: tmp_path / "maison")
    monkeypatch.setattr(frozen, "documents", lambda: tmp_path / "OneDrive" / "Documents")
    assert frozen.dossier_donnees() == tmp_path / "OneDrive" / "Documents" / "JobHunter"
    (tmp_path / "maison" / "Documents" / "JobHunter").mkdir(parents=True)
    assert frozen.dossier_donnees() == tmp_path / "maison" / "Documents" / "JobHunter"


def test_sync_docs_charge_fix_dashes_du_dossier(tmp_path, monkeypatch, capsys):
    """07 : le script perso des tirets se charge depuis le dossier de données."""
    from jobhunter.programs import sync_docs

    monkeypatch.setattr(sync_docs._racine, "scripts", lambda: tmp_path)
    assert sync_docs._fix_dashes() is None
    assert "skipped" in capsys.readouterr().out
    (tmp_path / "fix_dashes.py").write_text(
        "def fix_doc(f, dry=False):\n    return 1\n", encoding="utf-8"
    )
    assert sync_docs._fix_dashes().fix_doc("x") == 1
