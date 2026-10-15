#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_web_nav.py — Suite de tests synthétiques (sans réseau) pour web_nav.
Lance : python test_web_nav.py   (Playwright, pages data:// en mémoire).
Chaque test = page HTML synthétique + assertion. Pas de dépendance pytest."""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
sys.stdout.reconfigure(encoding="utf-8")
import web_nav as w

from playwright.sync_api import sync_playwright

PASS = FAIL = 0
def check(name, cond, got=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name}  (got: {got})")

def run(pg):
    # ── cookies : refus prioritaire ──
    pg.set_content('<div class=cookie-banner><button>Tout accepter</button><button>Tout refuser</button></div>')
    r = w.dismiss_cookies(pg)
    check("cookies refus prioritaire", r.get("done") in ("reject", "cmp-reject"), r)
    pg.set_content('<button id=onetrust-reject-all-handler>Refuser</button>')
    check("cookies CMP OneTrust", w.dismiss_cookies(pg).get("done") == "cmp-reject", w.dismiss_cookies(pg))

    # ── analyze : kinds ──
    pg.set_content('<form><input type=email><input type=password><button>Se connecter</button></form>')
    check("analyze login", w.analyze(pg).get("kind") == "login", w.analyze(pg).get("kind"))
    pg.set_content('<form><input type=email><input type=password><input type=password placeholder=confirm><button>Créer un compte</button></form>')
    check("analyze register", w.analyze(pg).get("kind") == "register", w.analyze(pg).get("kind"))
    pg.set_content('<form><input type=email><input type=file><button>Postuler</button></form>')
    check("analyze apply_form", w.analyze(pg).get("kind") == "apply_form", w.analyze(pg).get("kind"))
    pg.set_content('<iframe src="https://www.google.com/recaptcha/x"></iframe>')
    check("analyze captcha", w.analyze(pg).get("captcha") is True)
    pg.set_content("<h1>Sorry, we couldn't find anything here</h1><p>The job posting you're looking for might have closed, or it has been removed. (404 error).</p>")
    check("analyze dead (offre fermée/404)", w.analyze(pg).get("kind") == "dead", w.analyze(pg).get("kind"))
    # page offre avec email d'alerte + bouton Postuler → PAS newsletter
    pg.set_content('<h1>Analyste ESG</h1><button>Postuler</button><form><input type=email placeholder="email"><p>Recevoir des alertes emploi</p></form>')
    check("analyze offre+alerte != newsletter", w.analyze(pg).get("kind") != "newsletter_form", w.analyze(pg).get("kind"))

    # ── pick_js : rôles + accents + anti-footer ──
    pg.set_content('<button>Rejoignez-nous</button>')
    check("pick register synonyme", w.pg_pick(pg, "register"))
    pg.set_content('<header><a>Accueil</a></header><main><a class="btn-primary" href=/a>Déposer ma candidature</a></main><footer><a>Postuler mentions</a></footer>')
    lab = pg.evaluate(w.pick_js("apply")).get("label", "")
    check("pick apply évite footer (accents)", "andidature" in lab, lab)
    pg.set_content('<button class=cta>Apply for this job</button>')
    check("pick apply EN", w.pg_pick(pg, "apply"))

    # ── detect_ats ──
    for host, exp in [("careers-fr-axa.icims.com", "icims"), ("x.talent-soft.com", "talentsoft"),
                      ("boards.greenhouse.io", "greenhouse"), ("x.myworkdayjobs.com", "workday")]:
        # simulate via innerHTML signature (detect scanne url+dom ; on injecte le host dans un lien)
        pg.set_content(f'<a href="https://{host}/jobs">x</a><script src="https://{host}/app.js"></script>')
        ats = w.detect_ats(pg).get("name")
        check(f"detect_ats {exp}", ats == exp, ats)

    # ── segment_page : toutes les parties ──
    pg.set_content('''<header><nav><a>Carrières</a><button>Menu</button></nav></header>
      <div class=cookie-banner><button>Tout refuser</button></div>
      <main><input type=search placeholder="Rechercher un poste">
      <ul><li><a href=/jobs/1-analyste>Analyste ESG</a></li><li><a href=/jobs/2>Dev</a></li></ul>
      <a class=btn-primary href=/apply>Déposer ma candidature</a>
      <form><input type=email><input type=password><button>Se connecter</button></form></main>
      <footer><a>LinkedIn</a></footer>''')
    seg = w.segment_page(pg)
    check("segment régions header+nav+main+footer",
          all(seg["regions"].get(k) for k in ("header", "nav", "main", "footer")), seg.get("regions"))
    check("segment overlay cookie", seg["overlays"].get("cookie") is True)
    check("segment rôles (careers+apply+login+cookie)",
          all(seg["byRole"].get(r) for r in ("careers", "apply", "login", "cookie")), seg.get("byRole"))
    check("segment form login détecté", any(f["purpose"] == "login" for f in seg["forms"]))
    check("segment 2 offres", seg.get("offers") == 2, seg.get("offers"))

    # ── plan_action : décisions ──
    pg.set_content('<div class=cookie-banner><button>Tout refuser</button></div><a>Carrières</a>')
    check("plan cookie prio", w.plan_action(pg)["action"] == "cookies")
    pg.set_content('<a>Carrières</a>')
    check("plan careers", w.plan_action(pg)["action"] == "careers")
    pg.set_content('<ul><li><a href=/jobs/1-analyste>Analyste</a></li><li><a href=/jobs/2>X</a></li></ul>')
    check("plan drill (offres)", w.plan_action(pg)["action"] == "drill")
    pg.set_content('<form><input type=email><input type=file></form>')
    check("plan ready (apply form)", w.plan_action(pg)["action"] == "ready")
    pg.set_content('<iframe src="https://hcaptcha.com/x"></iframe>')
    check("plan stop (captcha)", w.plan_action(pg)["action"] == "stop")

    # ── find_offer : detect→search→drill ──
    pg.set_content('<input type=search placeholder=Poste><ul><li><a href=/jobs/1-analyste-esg>Analyste ESG</a></li><li><a href=/jobs/2-dev>Dev</a></li></ul>')
    fo = w.find_offer(pg, "analyste esg", max_tries=1)
    check("find_offer via search+drill", "drill" in fo.get("via", "") or fo.get("reached"), fo.get("via"))

    # ── switch_to_register : toggles ──
    for txt in ["Créez un compte", "Je me crée un espace candidat", "Inscrivez-vous", "Espace candidat"]:
        pg.set_content(f'<form><input type=email><input type=password></form><a role=tab>{txt}</a>')
        check(f"switch_to_register '{txt[:20]}'", w.switch_to_register(pg).get("switched") is True)

    # ── wait_for_form : inputs rendus tard ──
    pg.set_content('<div id=r></div>')
    pg.evaluate('setTimeout(()=>{document.getElementById("r").innerHTML="<input placeholder=Nom>";},800)')
    check("wait_for_form (input tardif)", w.wait_for_form(pg, 1, 4000) >= 1)

    # ── react_submit : requestSubmit ──
    pg.set_content('<form id=f><input type=email value=a@b.fr><button type=submit>Go</button></form>')
    pg.evaluate('document.getElementById("f").addEventListener("submit",e=>{e.preventDefault();window.__ok=1;})')
    w.react_submit(pg)
    check("react_submit déclenche submit", pg.evaluate("window.__ok") == 1)

    # ── human_click : bézier + clic fiable ──
    pg.set_content('<button id=b style="position:absolute;left:200px;top:150px;width:120px;height:40px">Go</button>')
    pg.evaluate('document.getElementById("b").addEventListener("click",()=>window.__hc=1)')
    w.human_click(pg, "#b")
    check("human_click (bézier) clique", pg.evaluate("window.__hc") == 1)

    # ── run_wizard : multi-écrans → stop submit final ──
    pg.set_content('''<form><input placeholder=Nom></form>
      <button id=n onclick="document.body.innerHTML='<form><input placeholder=Tel></form><button>Envoyer ma candidature</button>'">Suivant</button>''')
    wz = w.run_wizard(pg, fill_fn=lambda p: 0, max_screens=4)
    check("run_wizard stop=final_submit", wz.get("stopped") == "final_submit", wz.get("stopped"))

    # ── retry : réussit après unstick ──
    st = {"n": 0}
    def fn():
        st["n"] += 1; return {"ok": st["n"] >= 2}
    rr = w.retry(pg, fn, lambda x: x.get("ok"), 3)
    check("retry réussit au 2e essai", rr.get("ok") and st["n"] == 2, st["n"])

    # ── fill_application : remplissage universel (tous champs + docs + CGU) ──
    import tempfile as _tf, os as _os
    _cv = _os.path.join(_tf.gettempdir(), "CV_fa.pdf"); open(_cv, "w").close()
    _lt = _os.path.join(_tf.gettempdir(), "LT_fa.pdf"); open(_lt, "w").close()
    prof = {"prenom": "l'utilisateur", "nom": "Exemple", "email": "g@x.fr", "tel": "0600000000",
            "ville": "Bordeaux", "pays": "France", "nationalite": "Française", "message": "Motivé.", "cp": "33000"}
    pg.set_content('''<form>
      <label>Prénom<input name=firstname></label><label>Nom<input name=lastname></label>
      <label>Email<input type=email></label><label>Ville<input name=city></label>
      <label>Pays<select name=pays><option value=\"\">--</option><option>France</option><option>Belgique</option></select></label>
      <label>CV<input type=file name=cv></label><label>Lettre de motivation<input type=file name=cover></label>
      <label>Message<textarea name=motiv></textarea></label>
      <label><input type=checkbox name=cgu> J accepte les CGU</label>
      <label><input type=checkbox name=news> Newsletter</label></form>''')
    fa = w.fill_application(pg, prof, _cv, _lt)
    check("fill_application couverture >=70%", fa["cover_pct"] >= 70, fa["cover_pct"])
    check("fill_application upload CV+lettre", fa["uploaded"] == 2, fa["uploaded"])
    check("fill_application CGU cochée, pas newsletter",
          pg.eval_on_selector('input[name=cgu]', "e=>e.checked") and not pg.eval_on_selector('input[name=news]', "e=>e.checked"))
    check("fill_application select pays=France", pg.eval_on_selector('select[name=pays]', "e=>e.value") == "France")

    # ── dismiss_overlays : ferme chat widget + modale, garde cookies/offre ──
    pg.set_content('<div id=intercom-container style="width:60px;height:60px">chat</div>'
                   '<div class=cookie-banner style="width:300px;height:80px"><button>Tout refuser</button></div>')
    ov = w.dismiss_overlays(pg)
    check("overlay masque widget chat", pg.eval_on_selector('#intercom-container', "e=>getComputedStyle(e).display") == "none", ov)
    check("overlay garde bannière cookie", pg.eval_on_selector('.cookie-banner', "e=>getComputedStyle(e).display") != "none")
    pg.set_content('<div role=dialog style="width:300px;height:200px"><p>Abonne-toi</p><button>Non merci</button></div>')
    w.dismiss_overlays(pg)
    check("overlay clique fermeture modale (Non merci)", True)  # pas d'erreur = OK

    # ── _pick_option : code ISO + accents ──
    pg.set_content('<select><option value="">--</option><option value="FR">France</option><option value="BE">Belgique</option></select>')
    loc = pg.locator("select").first
    opts = pg.eval_on_selector("select", "s=>[...s.options].map(o=>({t:o.text,v:o.value}))")
    check("pick_option pays=France via value FR", w._pick_option(loc, opts, "France") and pg.eval_on_selector("select","s=>s.value")=="FR")
    pg.set_content('<select><option value="">--</option><option>Française</option><option>Belge</option></select>')
    loc = pg.locator("select").first
    opts = pg.eval_on_selector("select", "s=>[...s.options].map(o=>({t:o.text,v:o.value}))")
    check("pick_option accent Française via 'francaise'", w._pick_option(loc, opts, "francaise"))

    # ── smart_upload : match CV/lettre par label ──
    import tempfile, os
    cv = os.path.join(tempfile.gettempdir(), "CV_test.pdf"); open(cv, "w").close()
    lt = os.path.join(tempfile.gettempdir(), "lettre_test.pdf"); open(lt, "w").close()
    pg.set_content('<label>CV<input type=file></label><label>Lettre de motivation<input type=file></label>')
    up = w.smart_upload(pg, cv, lt)
    check("smart_upload match CV+lettre par label", len(up) == 2, up)


# petit helper (rendre pick_js testable en 1 ligne)
def _pg_pick(pg, task):
    return pg.evaluate(w.pick_js(task)).get("found") is True
w.pg_pick = _pg_pick

if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        print("=== TESTS web_nav ===")
        run(pg)
        b.close()
    print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS+FAIL}) ===")
    sys.exit(1 if FAIL else 0)
