#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_patterns.py — Suite exhaustive PATTERNS (sans réseau) :
A) reconnaissance signin/signup (FR/EN/DE/ES/IT, 2-étapes, toggles, modals)
B) recherche d'offres (structures Workday/Greenhouse/Lever/SmartRecruiters/TalentSoft/cartes)
C) remplissage TOUS les patterns de formulaire postuler (labels/placeholder/aria/autocomplete,
   radio/select/date/number, uploads multiples, CGU multi-langues, shadow DOM)
Run : python test_patterns.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys, os, tempfile

sys.stdout.reconfigure(encoding="utf-8")
import web_nav as w

from playwright.sync_api import sync_playwright

PASS = FAIL = 0


def check(name, cond, got=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  (got: {got})")


PROF = {
    "prenom": "l'utilisateur",
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


def _files():
    cv = os.path.join(tempfile.gettempdir(), "CV_pat.pdf")
    open(cv, "w").close()
    lt = os.path.join(tempfile.gettempdir(), "LT_pat.pdf")
    open(lt, "w").close()
    return cv, lt


# ══════════════ A. SIGNIN / SIGNUP ══════════════
def test_auth(pg):
    print("\n── A. Reconnaissance signin/signup ──")
    # login FR / EN / DE / ES / IT
    for lang, htmlp in [
        ("FR", "<form><input type=email><input type=password><button>Se connecter</button></form>"),
        ("EN", "<form><input type=email><input type=password><button>Sign in</button></form>"),
        ("DE", "<form><input type=email><input type=password><button>Anmelden</button></form>"),
        (
            "ES",
            "<form><input type=email><input type=password><button>Iniciar sesión</button></form>",
        ),
        ("IT", "<form><input type=email><input type=password><button>Accedi</button></form>"),
    ]:
        pg.set_content(htmlp)
        check(f"login {lang}", w.analyze(pg).get("kind") == "login", w.analyze(pg).get("kind"))
    # register FR / EN / DE (confirm pwd ou wording)
    for lang, htmlp in [
        (
            "FR",
            "<form><input type=email><input type=password><input type=password><button>Créer un compte</button></form>",
        ),
        ("EN", "<form><input type=email><input type=password><button>Sign up</button></form>"),
        ("DE", "<form><input type=email><input type=password><button>Registrieren</button></form>"),
        (
            "DE2",
            "<form><input type=email><input type=password><button>Konto erstellen</button></form>",
        ),
    ]:
        pg.set_content(htmlp)
        check(
            f"register {lang}", w.analyze(pg).get("kind") == "register", w.analyze(pg).get("kind")
        )
    # login 2-étapes (email seul + Continuer, style Workday/Google)
    pg.set_content(
        "<h1>Connexion</h1><form><input type=email placeholder=Email><button>Continuer</button></form>"
    )
    check(
        "login 2-étapes (email seul)",
        w.analyze(pg).get("kind") == "login",
        w.analyze(pg).get("kind"),
    )
    # switch login→register : toggles supplémentaires
    for txt in [
        "Pas encore de compte ?",
        "New user? Register here",
        "Créer mon espace candidat",
        "Je m'inscris",
    ]:
        pg.set_content(f"<form><input type=email><input type=password></form><a href=#>{txt}</a>")
        r = w.switch_to_register(pg)
        check(f"switch→register '{txt[:24]}'", r.get("switched") is True, r)
    # pick_js trouve les boutons login/register dans une page chargée
    pg.set_content(
        "<header><a href=/x>Actualités</a><a href=/login class=btn>Mon espace candidat</a></header>"
    )
    check("pick login 'Mon espace candidat'", pg.evaluate(w.pick_js("login")).get("found") is True)
    pg.set_content(
        "<nav><a>Contact</a></nav><main><button class=cta>Créez votre compte candidat</button></main>"
    )
    check(
        "pick register 'Créez votre compte'",
        pg.evaluate(w.pick_js("register")).get("found") is True,
    )
    pg.set_content("<div><button>Anmelden</button></div>")
    check("pick login DE 'Anmelden'", pg.evaluate(w.pick_js("login")).get("found") is True)


# ══════════════ B. RECHERCHE D'OFFRES ══════════════
APPLY_FORM = (
    "<form><input type=email placeholder=Email><input type=file><button>Postuler</button></form>"
)


def _mk(listing):
    # clic sur l'offre → remplace la page par un form apply (simule la navigation)
    return listing.replace("HREF", f'"#" onclick="document.body.innerHTML=\'{APPLY_FORM}\'"')


def test_offers(pg):
    print("\n── B. Recherche d'offres (structures ATS) ──")
    cases = [
        (
            "workday",
            "<ul><li><a data-automation-id=jobTitle href=HREF>Analyste ESG H/F</a></li><li><a data-automation-id=jobTitle href=HREF>Dev Java</a></li></ul>",
        ),
        (
            "greenhouse",
            "<div class=opening><a href=HREF>Analyste ESG</a><span>Paris</span></div><div class=opening><a href=HREF>Sales</a></div>",
        ),
        (
            "lever",
            "<div class=posting><a class=posting-title href=HREF><h5>ESG Analyst</h5></a></div><div class=posting><a class=posting-title href=HREF><h5>Designer</h5></a></div>",
        ),
        (
            "smartrecruiters",
            "<ul><li class=opening-job><a class=link--block href=HREF><h4>Analyste ESG</h4></a></li></ul>",
        ),
        (
            "talentsoft",
            "<div class=ts-offer-card><a class=ts-offer-card__title-link href=HREF>Analyste ESG (H/F)</a></div>",
        ),
        (
            "cartes custom",
            "<article class=job-card><h3>Analyste ESG</h3><a href=HREF>Voir l'offre</a></article><article class=job-card><h3>Comptable</h3><a href=HREF>Voir l'offre</a></article>",
        ),
    ]
    for name, listing in cases:
        pg.set_content(_mk(listing))
        fo = w.find_offer(pg, "analyste esg", max_tries=1)
        check(
            f"find_offer {name}",
            fo.get("reached") is True and fo.get("kind") == "apply_form",
            f"{fo.get('kind')} via {fo.get('via')}",
        )
    # recherche par champ (tape le rôle puis liste apparaît)
    pg.set_content(
        """<input type=search placeholder="Rechercher un poste"
        onchange="document.body.insertAdjacentHTML('beforeend','<ul><li><a href=# onclick=&quot;document.body.innerHTML=\\'%s\\'&quot;>Analyste ESG</a></li></ul>')">"""
        % APPLY_FORM.replace("'", "\\'")
    )
    fo = w.find_offer(pg, "analyste esg", max_tries=1)
    check(
        "find_offer via search input", "search" in str(fo.get("via", "")) or fo.get("reached"), fo
    )
    # évite les mauvais liens (footer/legal) et choisit l'offre
    pg.set_content(
        _mk(
            "<footer><a href=/mentions>Mentions légales</a><a href=/contact>Contact</a></footer><main><a href=HREF>Analyste ESG junior</a></main>"
        )
    )
    fo = w.find_offer(pg, "analyste esg", max_tries=1)
    check("drill évite footer/legal", fo.get("reached") is True, fo)
    # page morte → kind=dead (pas de faux drill)
    pg.set_content(
        "<h1>404 error</h1><p>The job posting you're looking for might have closed, or it has been removed.</p>"
    )
    check("page morte → dead", w.analyze(pg).get("kind") == "dead", w.analyze(pg).get("kind"))


# ══════════════ C. REMPLISSAGE TOUS PATTERNS ══════════════
def test_fill(pg):
    print("\n── C. Remplissage — tous les patterns postuler ──")
    cv, lt = _files()

    # C1. EN complet : labels + selects + number + date + LinkedIn + notice
    pg.set_content("""<form>
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
    fa = w.fill_application(pg, PROF, cv, lt)
    check("EN cover ≥80%", fa["cover_pct"] >= 80, fa["cover_pct"])
    check(
        "EN select country=France",
        pg.eval_on_selector("select[name=country]", "e=>e.value") == "France",
    )
    check("EN linkedin rempli", "linkedin" in pg.eval_on_selector("input[name=li]", "e=>e.value"))
    check("EN salaire rempli", pg.eval_on_selector("input[name=sal]", "e=>e.value") != "")
    check("EN date naissance", pg.eval_on_selector("input[name=dob]", "e=>e.value") != "")
    check(
        "EN terms oui / marketing non",
        pg.eval_on_selector("input[name=terms]", "e=>e.checked")
        and not pg.eval_on_selector("input[name=mkt]", "e=>e.checked"),
    )

    # C2. DE : Vorname/Nachname/PLZ/Geburtsdatum + AGB
    pg.set_content("""<form>
      <label>Vorname<input name=vn></label><label>Nachname<input name=nn></label>
      <label>E-Mail<input type=email name=em></label><label>Telefon<input name=tel></label>
      <label>PLZ<input name=plz></label><label>Stadt<input name=stadt></label>
      <label>Geburtsdatum<input name=geb></label>
      <label><input type=checkbox name=agb> Ich akzeptiere die AGB und Datenschutzbestimmungen</label></form>""")
    fa = w.fill_application(pg, PROF, cv, lt)
    check("DE cover ≥70%", fa["cover_pct"] >= 70, fa["cover_pct"])
    check(
        "DE Vorname=l'utilisateur",
        pg.eval_on_selector("input[name=vn]", "e=>e.value") == "l'utilisateur",
    )
    check("DE PLZ rempli", pg.eval_on_selector("input[name=plz]", "e=>e.value") == "75001")

    # C3. placeholder-only (aucun label)
    pg.set_content("""<form><input placeholder="Prénom"><input placeholder="Nom">
      <input placeholder="Adresse e-mail"><input placeholder="Téléphone portable">
      <input placeholder="Code postal"><textarea placeholder="Votre message / motivation"></textarea></form>""")
    fa = w.fill_application(pg, PROF, cv, lt)
    check("placeholder-only cover ≥80%", fa["cover_pct"] >= 80, fa["cover_pct"])

    # C4. aria-label only
    pg.set_content("""<form><input aria-label="First name"><input aria-label="Family name">
      <input aria-label="Email" type=email><input aria-label="Mobile phone"></form>""")
    fa = w.fill_application(pg, PROF, cv, lt)
    check("aria-label cover ≥75%", fa["cover_pct"] >= 75, fa["cover_pct"])

    # C5. autocomplete attributes (standard HTML)
    pg.set_content("""<form><input autocomplete=given-name><input autocomplete=family-name>
      <input autocomplete=email><input autocomplete=tel><input autocomplete=postal-code>
      <input autocomplete=address-level2></form>""")
    fa = w.fill_application(pg, PROF, cv, lt)
    check("autocomplete attrs cover ≥80%", fa["cover_pct"] >= 80, fa["cover_pct"])

    # C6. radio civilité FR + EN
    pg.set_content("""<form><fieldset><legend>Civilité</legend>
      <label><input type=radio name=civ value=mme> Madame</label>
      <label><input type=radio name=civ value=m> Monsieur</label></fieldset>
      <label>Nom<input name=nom></label></form>""")
    w.fill_application(pg, PROF, cv, lt)
    check(
        "radio civilité → Monsieur", pg.eval_on_selector("input[value=m]", "e=>e.checked") is True
    )
    pg.set_content("""<form><label><input type=radio name=title value=mrs> Mrs</label>
      <label><input type=radio name=title value=mr> Mr</label><label>Name<input name=n></label></form>""")
    w.fill_application(pg, PROF, cv, lt)
    check("radio title → Mr", pg.eval_on_selector("input[value=mr]", "e=>e.checked") is True)

    # C7. selects métier : niveau d'études / disponibilité / langue
    pg.set_content("""<form>
      <label>Niveau d'études<select name=niv><option value="">--</option><option>Bac+3</option><option>Master 2</option><option>Doctorat</option></select></label>
      <label>Langue<select name=lang><option value="">--</option><option>Allemand</option><option>Français</option></select></label></form>""")
    w.fill_application(pg, PROF, cv, lt)
    check(
        "select niveau=Master 2",
        pg.eval_on_selector("select[name=niv]", "e=>e.value") == "Master 2",
    )
    check(
        "select langue=Français",
        pg.eval_on_selector("select[name=lang]", "e=>e.value") == "Français",
    )

    # C8. uploads multiples : CV + lettre + docs extra
    extra = os.path.join(tempfile.gettempdir(), "diplome_pat.pdf")
    open(extra, "w").close()
    pg.set_content("""<form><label>CV *<input type=file name=cv></label>
      <label>Lettre de motivation<input type=file name=lm></label>
      <label>Autres documents (diplômes…)<input type=file name=other></label></form>""")
    fa = w.fill_application(pg, PROF, cv, lt, docs=[extra])
    check("upload CV+lettre+extra = 3", fa["uploaded"] == 3, fa["uploaded"])

    # C9. shadow DOM
    pg.set_content("<div id=host></div>")
    pg.evaluate("""() => {
      const r = document.getElementById('host').attachShadow({mode:'open'});
      r.innerHTML = `<form><label>Prénom<input name=p></label><label>Email<input type=email name=e></label></form>`;
    }""")
    fa = w.fill_application(pg, PROF, cv, lt)
    check("shadow DOM ≥1 champ rempli", fa["filled"] >= 1, fa)

    # C9b. formulaire DANS une iframe (SmartRecruiters/Taleo) → bascule auto
    pg.set_content(
        '<h1>Offre</h1><iframe srcdoc="'
        "&lt;form&gt;&lt;label&gt;Prénom&lt;input name=p&gt;&lt;/label&gt;"
        "&lt;label&gt;Email&lt;input type=email name=e&gt;&lt;/label&gt;"
        '&lt;label&gt;Ville&lt;input name=c&gt;&lt;/label&gt;&lt;/form&gt;" '
        "width=500 height=300></iframe>"
    )
    pg.wait_for_timeout(300)
    fa = w.fill_application(pg, PROF, cv, lt)
    fr = [f for f in pg.frames if f is not pg.main_frame]
    got = fr[0].eval_on_selector("input[name=p]", "e=>e.value") if fr else ""
    check("form dans iframe rempli (Prénom)", got == "l'utilisateur", got)

    # C10. ne touche PAS aux champs déjà remplis
    pg.set_content(
        '<form><label>Email<input type=email name=e value="deja@rempli.fr"></label><label>Prénom<input name=p></label></form>'
    )
    w.fill_application(pg, PROF, cv, lt)
    check(
        "champ pré-rempli préservé",
        pg.eval_on_selector("input[name=e]", "e=>e.value") == "deja@rempli.fr",
    )


# ══════════════ D. OTP / CODE EMAIL (semi-auto) ══════════════
def test_otp(pg):
    print("\n── D. OTP / code email (colle + surligne, PAS de clic) ──")
    # D1. champ unique nommé 'passcode'
    pg.set_content(
        "<form><label>Code de vérification<input id=passcode name=passcode maxlength=6></label>"
        "<button>Vérifier</button><button>Annuler</button></form>"
    )
    check("otp_present détecte champ passcode", w.otp_present(pg))
    fl = w.otp_flow(pg, "482913")
    check(
        "otp collé dans champ unique",
        pg.eval_on_selector("#passcode", "e=>e.value") == "482913" and fl["pasted"] == 1,
        fl,
    )
    check("otp surligne Vérifier (pas Annuler)", fl["verify"] == "Vérifier", fl["verify"])
    check(
        "otp NE clique PAS (bouton juste surligné)",
        pg.eval_on_selector("[data-wn-otp=verify]", "e=>e.textContent.trim()") == "Vérifier",
    )
    # D2. boîtes 1 chiffre
    pg.set_content(
        "<form>"
        + "".join(f"<input class=d maxlength=1>" for _ in range(6))
        + "<button>Valider</button></form>"
    )
    check("otp_present détecte boîtes 1-chiffre", w.otp_present(pg))
    w.paste_otp(pg, "135790")
    got = pg.eval_on_selector_all("input.d", "els=>els.map(e=>e.value).join('')")
    check("otp réparti sur 6 boîtes", got == "135790", got)
    # D3. autocomplete=one-time-code
    pg.set_content('<input autocomplete="one-time-code"><button>Confirmer</button>')
    r = w.paste_otp(pg, "9988")
    check(
        "otp autocomplete one-time-code",
        pg.eval_on_selector("input", "e=>e.value") == "9988" and r["mode"] == "auto",
    )
    # D4. page sans OTP → rien
    pg.set_content("<form><input type=email><button>Envoyer</button></form>")
    check("otp_present false hors OTP", not w.otp_present(pg))
    check("paste_otp sans code → filled 0", w.paste_otp(pg, "")["filled"] == 0)


# ══════════════ E. BUGS Obsidian (5,9,6,7,3) ══════════════
def test_bugs(pg):
    print("\n── E. Bugs à fixer (Obsidian) ──")
    cv, lt = _files()
    # bug5 : page carrière avec champ RECHERCHE + form register → ne remplit PAS le search
    pg.set_content("""<form class=search-form><input type=text name=q placeholder="Rechercher un poste"></form>
      <form id=reg><label>Prénom<input name=firstname></label><label>Email<input type=email name=em></label></form>""")
    w.fill_application(pg, PROF, cv, lt)
    check(
        "bug5 champ recherche NON rempli",
        pg.eval_on_selector("input[name=q]", "e=>e.value") == "",
        pg.eval_on_selector("input[name=q]", "e=>e.value"),
    )
    check(
        "bug5 champ register rempli",
        pg.eval_on_selector("input[name=firstname]", "e=>e.value") == "l'utilisateur",
    )
    # bug5b : champ newsletter email non rempli
    pg.set_content(
        '<form class=newsletter><input type=email name=news placeholder="Votre email newsletter"></form>'
    )
    w.fill_application(pg, PROF, cv, lt)
    check(
        "bug5 email newsletter NON rempli",
        pg.eval_on_selector("input[name=news]", "e=>e.value") == "",
    )

    # bug9 : champs SuccessFactors fbclc_fName / fbclc_lName
    pg.set_content(
        "<form><input name=fbclc_fName><input name=fbclc_lName><input name=fbclc_userName type=email></form>"
    )
    w.fill_application(pg, PROF, cv, lt)
    check(
        "bug9 SF fbclc_fName→prénom",
        pg.eval_on_selector("input[name=fbclc_fName]", "e=>e.value") == "l'utilisateur",
    )
    check(
        "bug9 SF fbclc_lName→nom",
        pg.eval_on_selector("input[name=fbclc_lName]", "e=>e.value") == "Exemple",
    )
    check(
        "bug9 SF fbclc_userName→email",
        pg.eval_on_selector("input[name=fbclc_userName]", "e=>e.value") == "g@x.fr",
    )

    # bug6 : anti-bot "Nice try" détecté comme blocked
    pg.set_content("<h1>Nice try, and congrats for figuring out how to land on this page!</h1>")
    check(
        "bug6 anti-bot 'nice try' → blocked",
        w.analyze(pg).get("kind") == "blocked",
        w.analyze(pg).get("kind"),
    )

    # bug7 : dialogue consent → clique Proceed (PAS Decline)
    pg.set_content("""<div role=dialog><p>Politique de confidentialité et traitement des données</p>
      <button>Proceed</button><button>Decline</button></div>""")
    r7 = w.accept_consent_dialog(pg)
    check("bug7 dialogue consent → Proceed", r7.get("clicked") == "Proceed", r7)
    # dialogue sans contexte consent → ne clique rien (pas un dialogue de CGU)
    pg.set_content("<div role=dialog><p>Choisir la langue</p><button>English</button></div>")
    check("bug7 dialogue non-consent ignoré", w.accept_consent_dialog(pg).get("clicked") == "")
    # Decline jamais choisi même seul-à-seul avec Proceed
    pg.set_content(
        "<div role=dialog><p>data privacy consent</p><button>Decline</button><button>Accept</button></div>"
    )
    check("bug7 jamais Decline", w.accept_consent_dialog(pg).get("clicked") == "Accept")

    # bug3 : highlight_submit ignore les mauvais boutons (liens de nav)
    import apply_runner as ar

    pg.set_content(
        "<header><a href=/x>Conseils et actus</a><a href=/y>Nos offres</a></header>"
        "<form><input name=a><input name=b><button type=submit>Envoyer ma candidature</button></form>"
    )
    lbl = ar.highlight_submit(pg)
    check(
        "bug3 highlight = bon submit (pas 'Conseils et actus')",
        lbl == "Envoyer ma candidature",
        lbl,
    )
    # page SANS vrai submit, juste des liens nav → ne surligne rien de faux
    pg.set_content("<header><a href=/x>Conseils et actus</a></header><main><p>texte</p></main>")
    lbl2 = ar.highlight_submit(pg)
    check("bug3 aucun faux submit sur page nav", lbl2 == "", lbl2)


if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        print("=== TESTS PATTERNS (auth / offres / remplissage / otp) ===")
        test_auth(pg)
        test_offers(pg)
        test_fill(pg)
        test_otp(pg)
        test_bugs(pg)
        b.close()
    print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
    sys.exit(1 if FAIL else 0)
