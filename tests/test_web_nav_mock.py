"""web_nav with network and Ollama MOCKED: robust_goto, login_flow, vision_pick,
llm_agent, engine choice, homepage_fallback. No real call: goto through
FakePage, Ollama through a replaced urlopen. A real headless Chromium serves as the page.
Converted from Scripts/test_web_nav_mock.py.
"""

import json
import urllib.request

import pytest

from jobhunter import navigation as w


# ── FakePage: simulates page.goto without browser or network ──────────────────────
class _FakeResp:
    def __init__(self, status):
        self.status = status


class FakePage:
    """Replays a script of goto steps: ('ok', status) or ('raise',)."""

    def __init__(self, script):
        self.script, self.i, self.url = script, 0, "about:blank"

    def goto(self, url, timeout=0, wait_until=None):
        step = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        if step[0] == "raise":
            raise Exception("net::ERR_TIMED_OUT")
        self.url = url
        return _FakeResp(step[1])

    def wait_for_timeout(self, ms):
        pass


@pytest.mark.parametrize(
    ("script", "ok"),
    [
        ([("ok", 200)], True),
        ([("raise",), ("raise",), ("ok", 200)], True),
        ([("ok", 429), ("ok", 200)], True),
        ([("raise",), ("raise",), ("raise",)], False),
        ([("ok", 500), ("ok", 503), ("ok", 200)], True),
    ],
    ids=[
        "200 direct",
        "retry apres 2 erreurs reseau",
        "backoff sur 429",
        "abandon apres N echecs",
        "retry sur 5xx",
    ],
)
def test_robust_goto(script, ok):
    assert w.robust_goto(FakePage(script), "http://x", tries=3)["ok"] is ok


# ── Mocked Ollama: queue of responses for urlopen ───────────────────────────────
class _FakeHTTP:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def ollama(monkeypatch):
    """ollama(*generate_responses): /api/tags lists two models, /api/generate returns
    the responses in order."""

    def faire(*reponses):
        file = list(reponses)

        def urlopen(req, timeout=0):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if url.endswith("/api/tags"):
                return _FakeHTTP({"models": [{"name": "qwen2.5vl:3b"}, {"name": "mistral:latest"}]})
            return _FakeHTTP(file.pop(0) if file else {"response": ""})

        monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    return faire


# ── login_flow: never a password typed ───────────────────────────────────
@pytest.fixture
def login_une_etape(page):
    page.set_content(
        '<form onsubmit="return false"><input type=email id=e>'
        "<input type=password id=p><span>x</span></form>"
    )
    return page, w.login_flow(page, "camille@test.fr", "SECRET123", max_steps=1)


def test_login_flow_remplit_l_email(login_une_etape):
    steps = login_une_etape[1].get("steps", [])
    assert steps and steps[0].get("email")


def test_login_flow_email_injecte(login_une_etape):
    assert login_une_etape[0].eval_on_selector("#e", "e=>e.value") == "camille@test.fr"


def test_login_flow_ne_tape_jamais_le_mot_de_passe(login_une_etape):
    assert login_une_etape[0].eval_on_selector("#p", "e=>e.value") == ""


def test_login_flow_deux_etapes(page):
    page.set_content("<form><input type=email name=email><button>Continuer</button></form>")
    s0 = w.login_flow(page, "a@b.fr", "pw", max_steps=2)["steps"][0]
    assert s0.get("email") == 1 and "ontinuer" in (s0.get("btn") or "")


# ── vision_pick and llm_agent (mocked Ollama) ────────────────────────────────────
def test_vision_pick_clique_le_bouton_nomme(page, ollama):
    ollama({"response": "Postuler"})
    page.set_content('<button onclick="window.__v=1">Postuler</button>')
    assert w.vision_pick(page, "apply", model="fake-vision").get("clicked") is True


def test_vision_pick_none_pas_de_clic(page, ollama):
    ollama({"response": "NONE"})
    page.set_content("<div>rien de cliquable</div>")
    assert w.vision_pick(page, "apply", model="fake-vision").get("clicked") is False


def test_llm_agent_action_done(page, ollama):
    ollama({"response": json.dumps({"action": "done", "id": None, "why": "form prêt"})})
    page.set_content("<form><input type=email><input type=file></form>")
    ag = w.llm_agent(page, "atteindre le form", max_steps=3, model="fake-text")
    assert ag.get("ok") is True and ag.get("steps") == 1


def test_llm_agent_refuse_le_clic_d_envoi_final(page, ollama):
    page.set_content("<button>Envoyer ma candidature</button><button>Autre</button>")
    ollama({"response": json.dumps({"action": "click", "id": 0, "why": "envoyer"})})
    ag = w.llm_agent(page, "postuler", max_steps=2, model="fake-text")
    assert ag.get("ok") is False and "refus" in (ag.get("note") or "")


def test_llm_agent_degrade_si_ollama_absent(page, monkeypatch):
    def absent(req, timeout=0):
        raise Exception("connrefused")

    monkeypatch.setattr(urllib.request, "urlopen", absent)
    assert w.llm_agent(page, "x", max_steps=1).get("ok") is False  # model detection fails


# ── choice of the navigation engine: standard Playwright, no stealth engine ───
def test_available_engines():
    engs = w.available_engines()
    assert isinstance(engs, list) and "playwright" in engs


@pytest.mark.parametrize("demande", ["auto", "playwright"], ids=["auto", "explicite"])
def test_moteur_playwright_standard(demande):
    assert w.get_sync_playwright(demande)[1] == "playwright"


def test_moteur_inconnu_repli():
    assert w.get_sync_playwright("moteur_inexistant")[1] in w.available_engines()


# ── homepage_fallback : nom -> site officiel -> carrieres ──────────────────────
def test_homepage_fallback_atteint_les_offres(page, monkeypatch):
    offres = (
        "<ul>"
        + "".join(f"<li><a href=/jobs/{i}-p>Poste {i}</a></li>" for i in range(1, 6))
        + "</ul>"
    )

    def goto(pg, url, tries=3, **kw):
        pg.set_content(
            f'<nav><a href="#" onclick="document.body.innerHTML=\'{offres}\'">Carrières</a></nav>'
        )
        return {"ok": True, "note": "fake"}

    monkeypatch.setattr(w, "robust_goto", goto)
    hf = w.homepage_fallback(page, "TestCorp", "analyste esg", homepage="https://fake.corp")
    assert hf.get("ok") is True


def test_homepage_fallback_sans_homepage(page, monkeypatch):
    """Company not found: nothing to open. The resolution is SIMULATED: the real one
    queried the web (80 s) and could write into the Scripts/homepages.json cache
    — "Entreprise Inconnue XYZ 999" had already ended up there."""
    from jobhunter.programs import enrich_homepages

    monkeypatch.setattr(enrich_homepages, "resolve", lambda entreprise: None)
    assert (
        w.homepage_fallback(page, "Entreprise Inconnue XYZ 999", "x").get("note") == "no_homepage"
    )
