#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_web_nav_mock.py — Tests avec réseau/Ollama MOCKÉS (login_flow, robust_goto,
vision_pick, llm_agent). Aucun appel réel : goto via FakePage, Ollama via urlopen patché.
Lance : python test_web_nav_mock.py"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys, json, io, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
import web_nav as w

from playwright.sync_api import sync_playwright

PASS = FAIL = 0
def check(name, cond, got=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {name}")
    else: FAIL += 1; print(f"  ❌ {name}  (got: {got})")


# ── FakePage : simule page.goto sans navigateur ni réseau ──
class _FakeResp:
    def __init__(self, status): self.status = status
class FakePage:
    """Rejoue un script d'étapes goto : ('ok', status) ou ('raise',)."""
    def __init__(self, script):
        self.script = script; self.i = 0; self.url = "about:blank"
    def goto(self, url, timeout=0, wait_until=None):
        step = self.script[min(self.i, len(self.script) - 1)]; self.i += 1
        if step[0] == "raise": raise Exception("net::ERR_TIMED_OUT")
        self.url = url; return _FakeResp(step[1])
    def wait_for_timeout(self, ms): pass


# ── Ollama mocké : file de réponses pour urlopen ──
class _FakeHTTP:
    def __init__(self, payload): self._b = json.dumps(payload).encode()
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False

_QUEUE = []
_real_urlopen = urllib.request.urlopen
def _fake_urlopen(req, timeout=0):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if url.endswith("/api/tags"):
        return _FakeHTTP({"models": [{"name": "qwen2.5vl:3b"}, {"name": "mistral:latest"}]})
    # /api/generate → prochaine réponse de la file
    payload = _QUEUE.pop(0) if _QUEUE else {"response": ""}
    return _FakeHTTP(payload)

def mock_ollama(*generate_responses):
    _QUEUE.clear(); _QUEUE.extend(generate_responses)
    urllib.request.urlopen = _fake_urlopen
def unmock_ollama():
    urllib.request.urlopen = _real_urlopen


def run(pg):
    # ── robust_goto (FakePage, aucun réseau) ──
    check("robust_goto 200 direct",
          w.robust_goto(FakePage([("ok", 200)]), "http://x")["ok"] is True)
    check("robust_goto retry après 2 erreurs réseau",
          w.robust_goto(FakePage([("raise",), ("raise",), ("ok", 200)]), "http://x", tries=3)["ok"] is True)
    check("robust_goto backoff sur 429 puis 200",
          w.robust_goto(FakePage([("ok", 429), ("ok", 200)]), "http://x", tries=3)["ok"] is True)
    r = w.robust_goto(FakePage([("raise",), ("raise",), ("raise",)]), "http://x", tries=3)
    check("robust_goto abandonne après N échecs", r["ok"] is False, r)
    r5 = w.robust_goto(FakePage([("ok", 500), ("ok", 503), ("ok", 200)]), "http://x", tries=3)
    check("robust_goto retry sur 5xx", r5["ok"] is True, r5)

    # ── login_flow (formulaire login 1 étape : email+pwd remplis + bouton) ──
    pg.set_content('<form><input type=email><input type=password><button>Se connecter</button></form>')
    # valeurs vérifiées AVANT que login_flow ne soumette (clic "Se connecter")
    pg.set_content('<form onsubmit="return false"><input type=email id=e><input type=password id=p><span>x</span></form>')
    lg = w.login_flow(pg, "camille@test.fr", "SECRET123", max_steps=1)  # pas de bouton NEXT → pas de submit
    steps = lg.get("steps", [])
    check("login_flow remplit l'email", bool(steps) and steps[0].get("email"), steps)
    check("login_flow email injecté", pg.eval_on_selector('#e', "e=>e.value") == "camille@test.fr")
    check("login_flow ne tape JAMAIS le mot de passe", pg.eval_on_selector('#p', "e=>e.value") == "")

    # login 2-étapes : étape 1 = email seul + "Continuer" (pas de champ pwd visible)
    pg.set_content('<form><input type=email name=email><button>Continuer</button></form>')
    lg2 = w.login_flow(pg, "a@b.fr", "pw", max_steps=2)
    s0 = lg2["steps"][0]
    check("login_flow 2-étapes: étape1 email + bouton Continuer",
          s0.get("email") == 1 and "ontinuer" in (s0.get("btn") or ""), s0)

    # ── vision_pick (Ollama mocké → renvoie 'Postuler') ──
    mock_ollama({"response": "Postuler"})
    pg.set_content('<button onclick="window.__v=1">Postuler</button>')
    vp = w.vision_pick(pg, "apply", model="fake-vision")
    unmock_ollama()
    check("vision_pick clique le bouton nommé par le LLM", vp.get("clicked") is True, vp)

    mock_ollama({"response": "NONE"})
    pg.set_content('<div>rien de cliquable</div>')
    vp2 = w.vision_pick(pg, "apply", model="fake-vision")
    unmock_ollama()
    check("vision_pick NONE → pas de clic", vp2.get("clicked") is False, vp2)

    # ── llm_agent (Ollama mocké : action done) ──
    mock_ollama({"response": json.dumps({"action": "done", "id": None, "why": "form prêt"})})
    pg.set_content('<form><input type=email><input type=file></form>')
    ag = w.llm_agent(pg, "atteindre le form", max_steps=3, model="fake-text")
    unmock_ollama()
    check("llm_agent action done → ok", ag.get("ok") is True and ag.get("steps") == 1, ag)

    # llm_agent garde-fou : refuse de cliquer un submit FINAL
    pg.set_content('<button>Envoyer ma candidature</button><button>Autre</button>')
    mock_ollama({"response": json.dumps({"action": "click", "id": 0, "why": "envoyer"})})
    ag2 = w.llm_agent(pg, "postuler", max_steps=2, model="fake-text")
    unmock_ollama()
    check("llm_agent REFUSE clic submit final", ag2.get("ok") is False and "refus" in (ag2.get("note") or ""), ag2)

    # llm_agent stop si Ollama absent (détection modèle échoue)
    def _no_model(req, timeout=0): raise Exception("connrefused")
    urllib.request.urlopen = _no_model
    ag3 = w.llm_agent(pg, "x", max_steps=1)   # model=None → détection → KO
    urllib.request.urlopen = _real_urlopen
    check("llm_agent dégrade si Ollama absent", ag3.get("ok") is False, ag3)

    # ── get_sync_playwright : sélection moteur nav (fallback en cascade) ──
    engs = w.available_engines()
    check("available_engines liste non vide", isinstance(engs, list) and "playwright" in engs, engs)
    sp, eff = w.get_sync_playwright("auto")
    check("engine auto -> Playwright standard (aucun moteur furtif)", eff == "playwright", eff)
    sp2, eff2 = w.get_sync_playwright("playwright")
    check("engine playwright explicite", eff2 == "playwright", eff2)
    sp3, eff3 = w.get_sync_playwright("moteur_inexistant")
    check("engine inconnu -> fallback playwright", eff3 in engs, eff3)

    # ── homepage_fallback : PIPELINE DE BASE nom→site officiel→carrières ──
    # homepage fournie directement + page synthétique avec lien Carrières → offres
    real_goto = w.robust_goto
    _jobs = "<ul>" + "".join(f"<li><a href=/jobs/{i}-p>Poste {i}</a></li>" for i in range(1, 6)) + "</ul>"
    def _fake_goto(page, url, tries=3, **kw):
        page.set_content(f'<nav><a href="#" onclick="document.body.innerHTML=\'{_jobs}\'">Carrières</a></nav>')
        return {"ok": True, "note": "fake"}
    w.robust_goto = _fake_goto
    hf = w.homepage_fallback(pg, "TestCorp", "analyste esg", homepage="https://fake.corp")
    w.robust_goto = real_goto
    check("homepage_fallback atteint carrières/offres", hf.get("ok") is True, hf)
    check("homepage_fallback sans homepage → no_homepage",
          w.homepage_fallback(pg, "Entreprise Inconnue XYZ 999", "x").get("note") in ("no_homepage", "homepage_goto_fail"))


if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); pg = b.new_page()
        print("=== TESTS web_nav (mock réseau/Ollama) ===")
        try: run(pg)
        finally: unmock_ollama()
        b.close()
    print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS+FAIL}) ===")
    sys.exit(1 if FAIL else 0)
