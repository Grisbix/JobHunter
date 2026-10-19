"""Recognition and filling of forms (web_nav, apply_runner), without network,
in a real headless Chromium.

A. login / sign-up (FR/EN/DE/ES/IT, two steps, toggles);
B. offer search (Workday, Greenhouse, Lever, SmartRecruiters, TalentSoft structures);
C. filling of all form patterns (labels, placeholder, aria, autocomplete,
   radio, select, date, number, uploads, terms, shadow DOM, iframe);
D. code received by email: pastes and highlights, NEVER clicks;
E. bugs found (search and newsletter not filled, SuccessFactors, anti-bot, consent,
   right send button highlighted).
Converted from Scripts/test_patterns.py.
"""

import pytest

from jobhunter import navigation as w
from jobhunter.programmes import apply_runner as ar

PROF = {
    "prenom": "Camille",
    "nom": "Exemple",
    "full": "Camille Exemple",
    "email": "g@x.fr",
    "tel": "+33600000000",
    "tel_local": "0600000000",
    "adresse": "1 rue des Tests",
    "cp": "75001",
    "ville": "Paris",
    "pays": "France",
    "nationalite": "Française",
    "date_naissance": "2000-01-15",
    "linkedin": "https://linkedin.com/in/exemple",
    "github": "https://github.com/exemple",
    "site_web": "https://exemple.dev",
    "disponibilite": "Immédiate",
    "salaire_souhaite": "38000",
    "mobilite": "France entière",
    "permis": "B",
    "niveau_etudes": "Master 2",
    "dernier_poste": "Analyste ESG stagiaire",
    "langues": "Français, Anglais C1",
    "competences": "SFDR, ESG, Python",
    "message": "Motivé par la finance durable.",
}


@pytest.fixture
def pieces(tmp_path):
    cv, lettre = tmp_path / "CV_pat.pdf", tmp_path / "LT_pat.pdf"
    cv.touch()
    lettre.touch()
    return str(cv), str(lettre)


def valeur(pg, selecteur):
    return pg.eval_on_selector(selecteur, "e=>e.value")


# ══ A. connexion / inscription ═════════════════════════════════════════════════
@pytest.mark.parametrize(
    ("bouton", "kind"),
    [
        ("Se connecter", "login"),
        ("Sign in", "login"),
        ("Anmelden", "login"),
        ("Iniciar sesión", "login"),
        ("Accedi", "login"),
        ("Sign up", "register"),
        ("Registrieren", "register"),
        ("Konto erstellen", "register"),
    ],
)
def test_connexion_ou_inscription(page, bouton, kind):
    page.set_content(
        f"<form><input type=email><input type=password><button>{bouton}</button></form>"
    )
    assert w.analyze(page).get("kind") == kind


def test_inscription_par_confirmation_du_mot_de_passe(page):
    page.set_content(
        "<form><input type=email><input type=password><input type=password>"
        "<button>Créer un compte</button></form>"
    )
    assert w.analyze(page).get("kind") == "register"


def test_connexion_en_deux_etapes(page):
    page.set_content(
        "<h1>Connexion</h1><form><input type=email placeholder=Email>"
        "<button>Continuer</button></form>"
    )
    assert w.analyze(page).get("kind") == "login"


@pytest.mark.parametrize(
    "texte",
    [
        "Pas encore de compte ?",
        "New user? Register here",
        "Créer mon espace candidat",
        "Je m'inscris",
    ],
)
def test_bascule_vers_l_inscription(page, texte):
    page.set_content(f"<form><input type=email><input type=password></form><a href=#>{texte}</a>")
    assert w.switch_to_register(page).get("switched") is True


@pytest.mark.parametrize(
    ("html", "tache"),
    [
        (
            "<header><a href=/x>Actualités</a><a href=/login class=btn>Mon espace candidat</a></header>",
            "login",
        ),
        (
            "<nav><a>Contact</a></nav><main><button class=cta>Créez votre compte candidat</button></main>",
            "register",
        ),
        ("<div><button>Anmelden</button></div>", "login"),
    ],
    ids=["mon espace candidat", "creez votre compte", "anmelden"],
)
def test_pick_trouve_le_bouton(page, html, tache):
    page.set_content(html)
    assert page.evaluate(w.pick_js(tache)).get("found") is True


# ══ B. offer search ══════════════════════════════════════════════════════
APPLY_FORM = (
    "<form><input type=email placeholder=Email><input type=file><button>Postuler</button></form>"
)


def avec_clic(listing):
    """A click on the offer replaces the page with a form (simulates navigation)."""
    return listing.replace("HREF", f'"#" onclick="document.body.innerHTML=\'{APPLY_FORM}\'"')


@pytest.mark.parametrize(
    "listing",
    [
        "<ul><li><a data-automation-id=jobTitle href=HREF>Analyste ESG H/F</a></li>"
        "<li><a data-automation-id=jobTitle href=HREF>Dev Java</a></li></ul>",
        "<div class=opening><a href=HREF>Analyste ESG</a><span>Paris</span></div>"
        "<div class=opening><a href=HREF>Sales</a></div>",
        "<div class=posting><a class=posting-title href=HREF><h5>ESG Analyst</h5></a></div>"
        "<div class=posting><a class=posting-title href=HREF><h5>Designer</h5></a></div>",
        "<ul><li class=opening-job><a class=link--block href=HREF><h4>Analyste ESG</h4></a></li></ul>",
        "<div class=ts-offer-card><a class=ts-offer-card__title-link href=HREF>Analyste ESG (H/F)</a></div>",
        "<article class=job-card><h3>Analyste ESG</h3><a href=HREF>Voir l'offre</a></article>"
        "<article class=job-card><h3>Comptable</h3><a href=HREF>Voir l'offre</a></article>",
    ],
    ids=["workday", "greenhouse", "lever", "smartrecruiters", "talentsoft", "cartes"],
)
def test_find_offer_structures_ats(page, listing):
    page.set_content(avec_clic(listing))
    fo = w.find_offer(page, "analyste esg", max_tries=1)
    assert fo.get("reached") is True and fo.get("kind") == "apply_form"


def test_find_offer_par_le_champ_de_recherche(page):
    page.set_content(
        """<input type=search placeholder="Rechercher un poste"
        onchange="document.body.insertAdjacentHTML('beforeend','<ul><li><a href=# onclick=&quot;document.body.innerHTML=\\'%s\\'&quot;>Analyste ESG</a></li></ul>')">"""
        % APPLY_FORM.replace("'", "\\'")
    )
    fo = w.find_offer(page, "analyste esg", max_tries=1)
    assert "search" in str(fo.get("via", "")) or fo.get("reached")


def test_drill_evite_pied_de_page_et_mentions(page):
    page.set_content(
        avec_clic(
            "<footer><a href=/mentions>Mentions légales</a><a href=/contact>"
            "Contact</a></footer><main><a href=HREF>Analyste ESG junior</a></main>"
        )
    )
    assert w.find_offer(page, "analyste esg", max_tries=1).get("reached") is True


def test_page_morte(page):
    page.set_content(
        "<h1>404 error</h1><p>The job posting you're looking for might have closed, "
        "or it has been removed.</p>"
    )
    assert w.analyze(page).get("kind") == "dead"


# ══ C. remplissage ═════════════════════════════════════════════════════════════
@pytest.fixture
def anglais(page, pieces):
    page.set_content("""<form>
      <label>First name<input name=fn></label><label>Last name<input name=ln></label>
      <label>Email address<input type=email name=em></label><label>Phone number<input type=tel name=ph></label>
      <label>City<input name=city></label>
      <label>Country<select name=country><option value="">--</option><option>Germany</option><option>France</option></select></label>
      <label>LinkedIn profile<input name=li></label>
      <label>Expected salary<input type=number name=sal></label>
      <label>Date of birth<input type=date name=dob></label>
      <label>Notice period / availability<input name=avail></label>
      <label>Cover letter<textarea name=cl></textarea></label>
      <label>Resume / CV<input type=file name=resume></label>
      <label><input type=checkbox name=terms> I agree to the terms and conditions</label>
      <label><input type=checkbox name=mkt> Send me marketing emails</label></form>""")
    return page, w.fill_application(page, PROF, *pieces)


def test_en_couverture(anglais):
    assert anglais[1]["cover_pct"] >= 80


def test_en_pays(anglais):
    assert valeur(anglais[0], "select[name=country]") == "France"


def test_en_linkedin(anglais):
    assert "linkedin" in valeur(anglais[0], "input[name=li]")


def test_en_salaire(anglais):
    assert valeur(anglais[0], "input[name=sal]") != ""


def test_en_date_de_naissance(anglais):
    assert valeur(anglais[0], "input[name=dob]") != ""


def test_en_conditions_oui_marketing_non(anglais):
    pg = anglais[0]
    assert pg.eval_on_selector("input[name=terms]", "e=>e.checked")
    assert not pg.eval_on_selector("input[name=mkt]", "e=>e.checked")


@pytest.fixture
def allemand(page, pieces):
    page.set_content("""<form>
      <label>Vorname<input name=vn></label><label>Nachname<input name=nn></label>
      <label>E-Mail<input type=email name=em></label><label>Telefon<input name=tel></label>
      <label>PLZ<input name=plz></label><label>Stadt<input name=stadt></label>
      <label>Geburtsdatum<input name=geb></label>
      <label><input type=checkbox name=agb> Ich akzeptiere die AGB und Datenschutzbestimmungen</label></form>""")
    return page, w.fill_application(page, PROF, *pieces)


def test_de_couverture(allemand):
    assert allemand[1]["cover_pct"] >= 70


def test_de_vorname(allemand):
    assert valeur(allemand[0], "input[name=vn]") == "Camille"


def test_de_plz(allemand):
    assert valeur(allemand[0], "input[name=plz]") == "75001"


@pytest.mark.parametrize(
    ("html", "minimum"),
    [
        (
            """<form><input placeholder="Prénom"><input placeholder="Nom">
      <input placeholder="Adresse e-mail"><input placeholder="Téléphone portable">
      <input placeholder="Code postal"><textarea placeholder="Votre message / motivation"></textarea></form>""",
            80,
        ),
        (
            """<form><input aria-label="First name"><input aria-label="Family name">
      <input aria-label="Email" type=email><input aria-label="Mobile phone"></form>""",
            75,
        ),
        (
            """<form><input autocomplete=given-name><input autocomplete=family-name>
      <input autocomplete=email><input autocomplete=tel><input autocomplete=postal-code>
      <input autocomplete=address-level2></form>""",
            80,
        ),
    ],
    ids=["placeholder seul", "aria-label seul", "autocomplete"],
)
def test_couverture_sans_libelle(page, pieces, html, minimum):
    page.set_content(html)
    assert w.fill_application(page, PROF, *pieces)["cover_pct"] >= minimum


@pytest.mark.parametrize(
    ("html", "coche"),
    [
        (
            """<form><fieldset><legend>Civilité</legend>
      <label><input type=radio name=civ value=mme> Madame</label>
      <label><input type=radio name=civ value=m> Monsieur</label></fieldset>
      <label>Nom<input name=nom></label></form>""",
            "input[value=m]",
        ),
        (
            """<form><label><input type=radio name=title value=mrs> Mrs</label>
      <label><input type=radio name=title value=mr> Mr</label><label>Name<input name=n></label></form>""",
            "input[value=mr]",
        ),
    ],
    ids=["civilite FR", "title EN"],
)
def test_radio_civilite(page, pieces, html, coche):
    page.set_content(html)
    w.fill_application(page, PROF, *pieces)
    assert page.eval_on_selector(coche, "e=>e.checked") is True


@pytest.fixture
def selects(page, pieces):
    page.set_content("""<form>
      <label>Niveau d'études<select name=niv><option value="">--</option><option>Bac+3</option><option>Master 2</option><option>Doctorat</option></select></label>
      <label>Langue<select name=lang><option value="">--</option><option>Allemand</option><option>Français</option></select></label></form>""")
    w.fill_application(page, PROF, *pieces)
    return page


def test_select_niveau_d_etudes(selects):
    assert valeur(selects, "select[name=niv]") == "Master 2"


def test_select_langue(selects):
    assert valeur(selects, "select[name=lang]") == "Français"


def test_televersements_multiples(page, pieces, tmp_path):
    extra = tmp_path / "diplome_pat.pdf"
    extra.touch()
    page.set_content("""<form><label>CV *<input type=file name=cv></label>
      <label>Lettre de motivation<input type=file name=lm></label>
      <label>Autres documents (diplômes…)<input type=file name=other></label></form>""")
    assert w.fill_application(page, PROF, *pieces, docs=[str(extra)])["uploaded"] == 3


def test_shadow_dom(page, pieces):
    page.set_content("<div id=host></div>")
    page.evaluate("""() => {
      const r = document.getElementById('host').attachShadow({mode:'open'});
      r.innerHTML = `<form><label>Prénom<input name=p></label><label>Email<input type=email name=e></label></form>`;
    }""")
    assert w.fill_application(page, PROF, *pieces)["filled"] >= 1


def test_formulaire_dans_une_iframe(page, pieces):
    page.set_content(
        '<h1>Offre</h1><iframe srcdoc="'
        "&lt;form&gt;&lt;label&gt;Prénom&lt;input name=p&gt;&lt;/label&gt;"
        "&lt;label&gt;Email&lt;input type=email name=e&gt;&lt;/label&gt;"
        '&lt;label&gt;Ville&lt;input name=c&gt;&lt;/label&gt;&lt;/form&gt;" '
        "width=500 height=300></iframe>"
    )
    page.wait_for_timeout(300)
    w.fill_application(page, PROF, *pieces)
    cadres = [f for f in page.frames if f is not page.main_frame]
    assert cadres and cadres[0].eval_on_selector("input[name=p]", "e=>e.value") == "Camille"


def test_champ_pre_rempli_preserve(page, pieces):
    page.set_content(
        '<form><label>Email<input type=email name=e value="deja@rempli.fr"></label>'
        "<label>Prénom<input name=p></label></form>"
    )
    w.fill_application(page, PROF, *pieces)
    assert valeur(page, "input[name=e]") == "deja@rempli.fr"


# ══ D. code received by email: pastes and highlights, NEVER clicks ════════════════
@pytest.fixture
def otp_unique(page):
    page.set_content(
        "<form><label>Code de vérification<input id=passcode name=passcode "
        "maxlength=6></label><button>Vérifier</button><button>Annuler</button></form>"
    )
    present = w.otp_present(page)
    return page, present, w.otp_flow(page, "482913")


def test_otp_detecte_le_champ(otp_unique):
    assert otp_unique[1]


def test_otp_colle_dans_le_champ_unique(otp_unique):
    assert valeur(otp_unique[0], "#passcode") == "482913" and otp_unique[2]["pasted"] == 1


def test_otp_surligne_verifier_pas_annuler(otp_unique):
    assert otp_unique[2]["verify"] == "Vérifier"


def test_otp_ne_clique_pas(otp_unique):
    texte = otp_unique[0].eval_on_selector("[data-wn-otp=verify]", "e=>e.textContent.trim()")
    assert texte == "Vérifier"


@pytest.fixture
def boites(page):
    page.set_content(
        "<form>"
        + "".join("<input class=d maxlength=1>" for _ in range(6))
        + "<button>Valider</button></form>"
    )
    return page


def test_otp_detecte_les_boites_d_un_chiffre(boites):
    assert w.otp_present(boites)


def test_otp_reparti_sur_six_boites(boites):
    w.paste_otp(boites, "135790")
    assert boites.eval_on_selector_all("input.d", "els=>els.map(e=>e.value).join('')") == "135790"


def test_otp_autocomplete_one_time_code(page):
    page.set_content('<input autocomplete="one-time-code"><button>Confirmer</button>')
    r = w.paste_otp(page, "9988")
    assert valeur(page, "input") == "9988" and r["mode"] == "auto"


@pytest.fixture
def sans_otp(page):
    page.set_content("<form><input type=email><button>Envoyer</button></form>")
    return page


def test_otp_absent(sans_otp):
    assert not w.otp_present(sans_otp)


def test_paste_otp_sans_code(sans_otp):
    assert w.paste_otp(sans_otp, "")["filled"] == 0


# ══ E. bugs releves ════════════════════════════════════════════════════════════
@pytest.fixture
def recherche_et_inscription(page, pieces):
    page.set_content("""<form class=search-form><input type=text name=q placeholder="Rechercher un poste"></form>
      <form id=reg><label>Prénom<input name=firstname></label><label>Email<input type=email name=em></label></form>""")
    w.fill_application(page, PROF, *pieces)
    return page


def test_champ_de_recherche_non_rempli(recherche_et_inscription):
    assert valeur(recherche_et_inscription, "input[name=q]") == ""


def test_champ_d_inscription_rempli(recherche_et_inscription):
    assert valeur(recherche_et_inscription, "input[name=firstname]") == "Camille"


def test_email_de_newsletter_non_rempli(page, pieces):
    page.set_content(
        "<form class=newsletter><input type=email name=news "
        'placeholder="Votre email newsletter"></form>'
    )
    w.fill_application(page, PROF, *pieces)
    assert valeur(page, "input[name=news]") == ""


@pytest.fixture
def successfactors(page, pieces):
    page.set_content(
        "<form><input name=fbclc_fName><input name=fbclc_lName>"
        "<input name=fbclc_userName type=email></form>"
    )
    w.fill_application(page, PROF, *pieces)
    return page


@pytest.mark.parametrize(
    ("champ", "attendu"),
    [("fbclc_fName", "Camille"), ("fbclc_lName", "Exemple"), ("fbclc_userName", "g@x.fr")],
)
def test_successfactors(successfactors, champ, attendu):
    assert valeur(successfactors, f"input[name={champ}]") == attendu


def test_anti_bot_nice_try_bloque(page):
    page.set_content("<h1>Nice try, and congrats for figuring out how to land on this page!</h1>")
    assert w.analyze(page).get("kind") == "blocked"


@pytest.mark.parametrize(
    ("html", "clique"),
    [
        (
            "<div role=dialog><p>Politique de confidentialité et traitement des données</p>"
            "<button>Proceed</button><button>Decline</button></div>",
            "Proceed",
        ),
        ("<div role=dialog><p>Choisir la langue</p><button>English</button></div>", ""),
        (
            "<div role=dialog><p>data privacy consent</p><button>Decline</button>"
            "<button>Accept</button></div>",
            "Accept",
        ),
    ],
    ids=["consentement -> Proceed", "dialogue sans consentement ignore", "jamais Decline"],
)
def test_dialogue_de_consentement(page, html, clique):
    page.set_content(html)
    assert w.accept_consent_dialog(page).get("clicked") == clique


def test_surligne_le_vrai_bouton_d_envoi(page):
    page.set_content(
        "<header><a href=/x>Conseils et actus</a><a href=/y>Nos offres</a></header>"
        "<form><input name=a><input name=b><button type=submit>"
        "Envoyer ma candidature</button></form>"
    )
    assert ar.highlight_submit(page) == "Envoyer ma candidature"


def test_aucun_faux_bouton_d_envoi(page):
    page.set_content("<header><a href=/x>Conseils et actus</a></header><main><p>texte</p></main>")
    assert ar.highlight_submit(page) == ""
