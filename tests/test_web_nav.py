"""web_nav sur pages HTML synthetiques (sans reseau), dans un vrai Chromium headless.

Cookies, typologie des pages, choix des boutons, detection d'ATS, segmentation,
plan d'action, assistant multi-ecrans (arret sur l'envoi final), remplissage et
televersement. Converti depuis Scripts/test_web_nav.py, qui ajoutait une fonction
`pg_pick` au module web_nav et laissait ses fichiers dans le dossier temporaire.
"""

import pytest

import web_nav as w


def pick(pg, tache):
    return pg.evaluate(w.pick_js(tache)).get("found") is True


# ── cookies : refus prioritaire ────────────────────────────────────────────────
def test_cookies_refus_prioritaire(page):
    page.set_content(
        "<div class=cookie-banner><button>Tout accepter</button><button>Tout refuser</button></div>"
    )
    assert w.dismiss_cookies(page).get("done") in ("reject", "cmp-reject")


def test_cookies_cmp_onetrust(page):
    page.set_content("<button id=onetrust-reject-all-handler>Refuser</button>")
    assert w.dismiss_cookies(page).get("done") == "cmp-reject"


# ── analyze : nature de la page ────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("html", "kind"),
    [
        (
            "<form><input type=email><input type=password><button>Se connecter</button></form>",
            "login",
        ),
        (
            "<form><input type=email><input type=password><input type=password placeholder=confirm>"
            "<button>Créer un compte</button></form>",
            "register",
        ),
        ("<form><input type=email><input type=file><button>Postuler</button></form>", "apply_form"),
        (
            "<h1>Sorry, we couldn't find anything here</h1><p>The job posting you're looking for "
            "might have closed, or it has been removed. (404 error).</p>",
            "dead",
        ),
    ],
    ids=["login", "register", "apply_form", "dead"],
)
def test_analyze_kind(page, html, kind):
    page.set_content(html)
    assert w.analyze(page).get("kind") == kind


def test_analyze_captcha(page):
    page.set_content('<iframe src="https://www.google.com/recaptcha/x"></iframe>')
    assert w.analyze(page).get("captcha") is True


def test_analyze_offre_avec_alerte_n_est_pas_une_newsletter(page):
    page.set_content(
        "<h1>Analyste ESG</h1><button>Postuler</button><form><input type=email "
        'placeholder="email"><p>Recevoir des alertes emploi</p></form>'
    )
    assert w.analyze(page).get("kind") != "newsletter_form"


# ── pick_js : roles, accents, pied de page evite ───────────────────────────────
def test_pick_register_synonyme(page):
    page.set_content("<button>Rejoignez-nous</button>")
    assert pick(page, "register")


def test_pick_apply_evite_le_pied_de_page(page):
    page.set_content(
        '<header><a>Accueil</a></header><main><a class="btn-primary" href=/a>'
        "Déposer ma candidature</a></main><footer><a>Postuler mentions</a></footer>"
    )
    assert "andidature" in page.evaluate(w.pick_js("apply")).get("label", "")


def test_pick_apply_en(page):
    page.set_content("<button class=cta>Apply for this job</button>")
    assert pick(page, "apply")


# ── detect_ats ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("hote", "ats"),
    [
        ("careers-fr-axa.icims.com", "icims"),
        ("x.talent-soft.com", "talentsoft"),
        ("boards.greenhouse.io", "greenhouse"),
        ("x.myworkdayjobs.com", "workday"),
    ],
)
def test_detect_ats(page, hote, ats):
    page.set_content(
        f'<a href="https://{hote}/jobs">x</a><script src="https://{hote}/app.js"></script>'
    )
    assert w.detect_ats(page).get("name") == ats


# ── segment_page ───────────────────────────────────────────────────────────────
@pytest.fixture
def segments(page):
    page.set_content("""<header><nav><a>Carrières</a><button>Menu</button></nav></header>
      <div class=cookie-banner><button>Tout refuser</button></div>
      <main><input type=search placeholder="Rechercher un poste">
      <ul><li><a href=/jobs/1-analyste>Analyste ESG</a></li><li><a href=/jobs/2>Dev</a></li></ul>
      <a class=btn-primary href=/apply>Déposer ma candidature</a>
      <form><input type=email><input type=password><button>Se connecter</button></form></main>
      <footer><a>LinkedIn</a></footer>""")
    return w.segment_page(page)


def test_segment_regions(segments):
    assert all(segments["regions"].get(k) for k in ("header", "nav", "main", "footer"))


def test_segment_overlay_cookie(segments):
    assert segments["overlays"].get("cookie") is True


def test_segment_roles(segments):
    assert all(segments["byRole"].get(r) for r in ("careers", "apply", "login", "cookie"))


def test_segment_formulaire_de_connexion(segments):
    assert any(f["purpose"] == "login" for f in segments["forms"])


def test_segment_deux_offres(segments):
    assert segments.get("offers") == 2


# ── plan_action ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("html", "action"),
    [
        ("<div class=cookie-banner><button>Tout refuser</button></div><a>Carrières</a>", "cookies"),
        ("<a>Carrières</a>", "careers"),
        (
            "<ul><li><a href=/jobs/1-analyste>Analyste</a></li><li><a href=/jobs/2>X</a></li></ul>",
            "drill",
        ),
        ("<form><input type=email><input type=file></form>", "ready"),
        ('<iframe src="https://hcaptcha.com/x"></iframe>', "stop"),  # captcha : on s'arrete
    ],
    ids=["cookies d'abord", "carrieres", "offres", "formulaire pret", "captcha"],
)
def test_plan_action(page, html, action):
    page.set_content(html)
    assert w.plan_action(page)["action"] == action


def test_find_offer_par_recherche_puis_offre(page):
    page.set_content(
        "<input type=search placeholder=Poste><ul><li><a href=/jobs/1-analyste-esg>"
        "Analyste ESG</a></li><li><a href=/jobs/2-dev>Dev</a></li></ul>"
    )
    fo = w.find_offer(page, "analyste esg", max_tries=1)
    assert "drill" in fo.get("via", "") or fo.get("reached")


@pytest.mark.parametrize(
    "texte",
    ["Créez un compte", "Je me crée un espace candidat", "Inscrivez-vous", "Espace candidat"],
)
def test_switch_to_register(page, texte):
    page.set_content(f"<form><input type=email><input type=password></form><a role=tab>{texte}</a>")
    assert w.switch_to_register(page).get("switched") is True


# ── attentes, soumission, clic ─────────────────────────────────────────────────
def test_wait_for_form_input_tardif(page):
    page.set_content("<div id=r></div>")
    page.evaluate(
        'setTimeout(()=>{document.getElementById("r").innerHTML="<input placeholder=Nom>";},800)'
    )
    assert w.wait_for_form(page, 1, 4000) >= 1


def test_react_submit_declenche_submit(page):
    page.set_content(
        "<form id=f><input type=email value=a@b.fr><button type=submit>Go</button></form>"
    )
    page.evaluate(
        'document.getElementById("f").addEventListener("submit",e=>{e.preventDefault();window.__ok=1;})'
    )
    w.react_submit(page)
    assert page.evaluate("window.__ok") == 1


def test_human_click_clique(page):
    page.set_content(
        '<button id=b style="position:absolute;left:200px;top:150px;width:120px;'
        'height:40px">Go</button>'
    )
    page.evaluate('document.getElementById("b").addEventListener("click",()=>window.__hc=1)')
    w.human_click(page, "#b")
    assert page.evaluate("window.__hc") == 1


def test_run_wizard_s_arrete_sur_l_envoi_final(page):
    page.set_content("""<form><input placeholder=Nom></form>
      <button id=n onclick="document.body.innerHTML='<form><input placeholder=Tel></form><button>Envoyer ma candidature</button>'">Suivant</button>""")
    assert w.run_wizard(page, fill_fn=lambda p: 0, max_screens=4).get("stopped") == "final_submit"


def test_retry_reussit_au_deuxieme_essai(page):
    n = {"essais": 0}

    def fn():
        n["essais"] += 1
        return {"ok": n["essais"] >= 2}

    assert w.retry(page, fn, lambda x: x.get("ok"), 3).get("ok") and n["essais"] == 2


# ── fill_application : remplissage universel ───────────────────────────────────
PROFIL = {
    "prenom": "Camille",
    "nom": "Exemple",
    "email": "g@x.fr",
    "tel": "0600000000",
    "ville": "Bordeaux",
    "pays": "France",
    "nationalite": "Française",
    "message": "Motivé.",
    "cp": "33000",
}


@pytest.fixture
def pieces(tmp_path):
    cv, lettre = tmp_path / "CV_fa.pdf", tmp_path / "LT_fa.pdf"
    cv.touch()
    lettre.touch()
    return str(cv), str(lettre)


@pytest.fixture
def rempli(page, pieces):
    page.set_content("""<form>
      <label>Prénom<input name=firstname></label><label>Nom<input name=lastname></label>
      <label>Email<input type=email></label><label>Ville<input name=city></label>
      <label>Pays<select name=pays><option value="">--</option><option>France</option><option>Belgique</option></select></label>
      <label>CV<input type=file name=cv></label><label>Lettre de motivation<input type=file name=cover></label>
      <label>Message<textarea name=motiv></textarea></label>
      <label><input type=checkbox name=cgu> J accepte les CGU</label>
      <label><input type=checkbox name=news> Newsletter</label></form>""")
    return page, w.fill_application(page, PROFIL, *pieces)


def test_fill_application_couverture(rempli):
    assert rempli[1]["cover_pct"] >= 70


def test_fill_application_televerse_cv_et_lettre(rempli):
    assert rempli[1]["uploaded"] == 2


def test_fill_application_cgu_cochees_pas_la_newsletter(rempli):
    pg = rempli[0]
    assert pg.eval_on_selector("input[name=cgu]", "e=>e.checked")
    assert not pg.eval_on_selector("input[name=news]", "e=>e.checked")


def test_fill_application_pays(rempli):
    assert rempli[0].eval_on_selector("select[name=pays]", "e=>e.value") == "France"


# ── dismiss_overlays : ferme widget de chat et modale, garde cookies ───────────
@pytest.fixture
def overlays(page):
    page.set_content(
        '<div id=intercom-container style="width:60px;height:60px">chat</div>'
        '<div class=cookie-banner style="width:300px;height:80px">'
        "<button>Tout refuser</button></div>"
    )
    w.dismiss_overlays(page)
    return page


def test_overlay_masque_le_widget_de_chat(overlays):
    assert (
        overlays.eval_on_selector("#intercom-container", "e=>getComputedStyle(e).display") == "none"
    )


def test_overlay_garde_la_banniere_cookie(overlays):
    assert overlays.eval_on_selector(".cookie-banner", "e=>getComputedStyle(e).display") != "none"


def test_overlay_modale_fermee_sans_erreur(page):
    # l'ancienne suite verifiait `True` ; on verifie au moins que l'appel aboutit
    page.set_content(
        '<div role=dialog style="width:300px;height:200px"><p>Abonne-toi</p>'
        "<button>Non merci</button></div>"
    )
    w.dismiss_overlays(page)


# ── _pick_option et smart_upload ───────────────────────────────────────────────
def _options(pg):
    return pg.eval_on_selector("select", "s=>[...s.options].map(o=>({t:o.text,v:o.value}))")


def test_pick_option_pays_par_code_iso(page):
    page.set_content(
        '<select><option value="">--</option><option value="FR">France</option>'
        '<option value="BE">Belgique</option></select>'
    )
    assert w._pick_option(page.locator("select").first, _options(page), "France")
    assert page.eval_on_selector("select", "s=>s.value") == "FR"


def test_pick_option_accent(page):
    page.set_content(
        '<select><option value="">--</option><option>Française</option>'
        "<option>Belge</option></select>"
    )
    assert w._pick_option(page.locator("select").first, _options(page), "francaise")


def test_smart_upload_par_libelle(page, pieces):
    page.set_content(
        "<label>CV<input type=file></label><label>Lettre de motivation<input type=file></label>"
    )
    assert len(w.smart_upload(page, *pieces)) == 2
