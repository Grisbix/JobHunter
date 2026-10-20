"""Fallback through a local model (Ollama): vision and step-by-step agent.

Part of jobhunter.navigation (formerly Scripts/web_nav.py, phase 3.6).
"""

import random as _rnd
from typing import Any

from jobhunter.navigation.browser import human_click, human_scroll, human_type
from jobhunter.navigation.page import analyze
from jobhunter.network import exiger_http

# ── FALLBACK VISION (Ollama llava) : screenshot -> label bouton -> clic ────────
# Couvre canvas / DOM exotique / label hors-regex. Local, gratuit, offline.
_VISION_TASK_FR = {
    "apply": "postuler à l'offre (bouton Postuler / Candidater)",
    "register": "créer un compte / s'inscrire",
    "login": "se connecter (login)",
}


def _click_by_text_js(label: str) -> str:
    import json as _j

    lab = _j.dumps(label.strip().lower())
    return (
        r"""
    ((LAB) => {
      const _deep=(root,acc)=>{root.querySelectorAll('a,button,[role=button],input[type=button],input[type=submit],[onclick]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
      const els=_deep(document,[]).filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0;});
      let best=null;
      for(const el of els){
        const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim().toLowerCase();
        if(t && (t===LAB || t.includes(LAB) || LAB.includes(t))){ best=el; break; }
      }
      document.querySelectorAll('[data-wn-vpick]').forEach(e=>e.removeAttribute('data-wn-vpick'));
      if(best){ best.setAttribute('data-wn-vpick','1'); best.scrollIntoView({block:'center'}); return {found:true,label:(best.innerText||best.value||'').trim().slice(0,50)}; }
      return {found:false};
    })(%s)
    """
        % lab
    )


def vision_pick(
    page: Any, task: str, model: str | None = None, host: str = "http://localhost:11434"
) -> dict[str, Any]:
    """Vision fallback: screenshot -> Ollama reads the right button -> DOM click.

    Auto-detects the available vision model (qwen2.5vl, llava, etc.). Silent if
    Ollama/the model is missing. Returns {clicked, label, note}.
    """
    import base64
    import json
    import urllib.error
    import urllib.request

    # Auto-detection of the available vision model
    if model is None:
        model = _detect_vision_model(host)
        if model is None:
            return {"clicked": False, "note": "aucun modèle vision Ollama trouvé"}

    try:
        png = page.screenshot(type="png")
    except Exception as e:
        return {"clicked": False, "note": "screenshot KO: %s" % type(e).__name__}
    b64 = base64.b64encode(png).decode()
    goal = _VISION_TASK_FR.get(task, _VISION_TASK_FR["apply"])
    prompt = (
        "Capture d'une page web. Tâche: %s. "
        "Réponds UNIQUEMENT le texte visible EXACT du seul bouton/lien à cliquer. "
        "Pas d'explication. Si aucun, réponds NONE." % goal
    )
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode()
    try:
        req = urllib.request.Request(
            exiger_http(host + "/api/generate"),
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # nosec B310 : scheme checked by exiger_http
            out = json.loads(resp.read().decode())
        label = (out.get("response") or "").strip().strip('"').splitlines()[0][:60]
    except Exception as e:
        return {"clicked": False, "note": "ollama KO (%s) — pull %s ?" % (type(e).__name__, model)}
    if not label or label.upper() == "NONE":
        return {"clicked": False, "label": label, "note": "vision: aucun bouton"}
    try:
        r = page.evaluate(_click_by_text_js(label))
        if r and r.get("found"):
            page.locator('[data-wn-vpick="1"]').first.click(timeout=4000)
            return {"clicked": True, "label": r.get("label", label), "note": "vision OK"}
    except Exception as e:
        return {"clicked": False, "label": label, "note": "clic KO: %s" % type(e).__name__}
    return {"clicked": False, "label": label, "note": "label vu mais introuvable au DOM"}


def _detect_vision_model(host: str = "http://localhost:11434") -> str | None:
    """Detects the first vision model available through the Ollama API.

    Order of preference: qwen2.5vl → llava → minicpm-v → bakllava.
    """
    import json
    import urllib.error
    import urllib.request

    VISION_KEYWORDS = [
        "qwen2.5vl",
        "qwen2-vl",
        "llava",
        "minicpm-v",
        "bakllava",
        "llama3.2-vision",
        "llama-3.2-vision",
        "moondream",
    ]
    try:
        req = urllib.request.Request(exiger_http(host + "/api/tags"))
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310 : scheme checked by exiger_http
            data = json.loads(resp.read().decode())
        models: list[str] = [m.get("name", "") for m in data.get("models", [])]
        for kw in VISION_KEYWORDS:
            for m in models:
                if kw in m.lower():
                    return m.split(":")[0] if ":" in m else m
        # Fallback: any model with "vl" or "vision" in its name
        for m in models:
            ml = m.lower()
            if "vl" in ml or "vision" in ml:
                return m.split(":")[0] if ":" in m else m
    except Exception:
        pass
    return None  # nothing found → manual fallback


def _detect_text_model(host: str = "http://localhost:11434") -> str | None:
    """Detects an Ollama text model for reasoning (mistral/llama/qwen/phi)."""
    import json
    import urllib.request

    PREF = ["qwen2.5", "llama3", "llama-3", "mistral", "mixtral", "phi", "gemma", "qwen"]
    try:
        req = urllib.request.Request(exiger_http(host + "/api/tags"))
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310 : scheme checked by exiger_http
            models: list[str] = [
                m.get("name", "") for m in json.loads(resp.read().decode()).get("models", [])
            ]
        for kw in PREF:
            for m in models:
                if kw in m.lower() and "vl" not in m.lower() and "vision" not in m.lower():
                    return m
        return models[0] if models else None
    except Exception:
        return None


# ── #1 LLM AGENT (plan-act): reads the page, decides the action, runs it, starts again ─
# Human-equivalent reasoning on the DOM (+ optional vision). Local Ollama, free.
# SAFEGUARDS: never clicks the final submit, never solves a captcha.
_AGENT_DOM_JS = r"""
() => {
  const _deep=(root,acc,sel)=>{root.querySelectorAll(sel).forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc,sel);});return acc;};
  const vis=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.top<(window.innerHeight+800);};
  const lab=el=>{let t='';if(el.id){const l=document.querySelector(`label[for="${el.id}"]`);if(l)t+=' '+l.textContent;}const p=el.closest('label');if(p)t+=' '+p.textContent;return (t+' '+(el.placeholder||'')+' '+(el.getAttribute('aria-label')||'')+' '+(el.name||'')).trim().slice(0,60);};
  document.querySelectorAll('[data-wn-ag]').forEach(e=>e.removeAttribute('data-wn-ag'));
  let k=0; const clickables=[], inputs=[];
  _deep(document,[], 'a,button,[role=button],input[type=submit],input[type=button],summary').filter(vis).slice(0,40).forEach(el=>{
    const t=(el.innerText||el.value||el.getAttribute('aria-label')||el.title||'').trim().slice(0,50);
    if(!t) return; el.setAttribute('data-wn-ag', k); clickables.push({id:k, txt:t}); k++;
  });
  _deep(document,[], 'input,textarea,select').filter(vis).filter(e=>!['hidden','submit','button'].includes((e.type||'').toLowerCase())).slice(0,25).forEach(el=>{
    el.setAttribute('data-wn-ag', k); inputs.push({id:k, type:(el.type||'text'), label:lab(el), filled:!!(el.value&&el.value.trim())}); k++;
  });
  return {url:location.href, title:document.title.slice(0,80), clickables, inputs};
}
"""


def llm_agent(
    page: Any,
    goal: str,
    max_steps: int = 8,
    model: str | None = None,
    host: str = "http://localhost:11434",
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """#1 Plan-act agent: at each step reads the DOM (digest), asks the local LLM (Ollama) for the action to take to reach `goal`, runs it, starts again.

    Actions: click / fill / scroll / done / stop. SAFEGUARDS: refuses the final submit
    & captcha (returns stop). Degrades cleanly if Ollama is missing. Returns {ok, steps,
    log, note}.
    """
    import json
    import re as _re
    import urllib.request

    model = model or _detect_text_model(host)
    if not model:
        return {
            "ok": False,
            "steps": 0,
            "log": [],
            "note": "ollama absent — pull un modèle (mistral/qwen)",
        }
    prof = profile or {}
    NEVER = _re.compile(
        r"(envoyer ma candidature|soumettre|submit application|confirmer et envoyer|valider et envoyer|finaliser.*candidature|envoyer definitivement)",
        _re.I,
    )
    log: list[Any] = []
    for step in range(max(1, max_steps)):
        info = analyze(page)
        if info.get("captcha"):
            return {"ok": False, "steps": step, "log": log, "note": "captcha — humain requis"}
        try:
            dom = page.evaluate(_AGENT_DOM_JS)
        except Exception:
            return {"ok": False, "steps": step, "log": log, "note": "dom digest KO"}
        prompt = (
            "Tu pilotes un navigateur pour ce but: %s.\n"
            "Profil (pour remplir): %s.\n"
            "Page: %s | %s\n"
            "BOUTONS/LIENS (id:texte): %s\n"
            "CHAMPS (id:type:label:rempli): %s\n"
            'Réponds UNIQUEMENT en JSON: {"action":"click|fill|scroll|done|stop","id":<int|null>,'
            '"value":<str|null>,"why":<str>}.\n'
            "Règles: NE clique JAMAIS un bouton d'envoi/soumission FINAL de candidature. "
            "Si captcha/blocage -> action stop. Si but atteint (formulaire prêt) -> action done. "
            "Pour remplir un champ -> action fill avec id + value."
        ) % (
            goal,
            json.dumps(
                {k: prof.get(k) for k in ("full", "email", "tel", "prenom", "nom") if prof.get(k)},
                ensure_ascii=False,
            ),
            dom.get("title", ""),
            dom.get("url", "")[:80],
            json.dumps(dom.get("clickables", []), ensure_ascii=False)[:1500],
            json.dumps(dom.get("inputs", []), ensure_ascii=False)[:1200],
        )
        body = json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            }
        ).encode()
        try:
            req = urllib.request.Request(
                exiger_http(host + "/api/generate"),
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=90) as resp:  # nosec B310 : scheme checked by exiger_http
                out = json.loads(resp.read().decode())
            act = json.loads(out.get("response") or "{}")
        except Exception as e:
            return {"ok": False, "steps": step, "log": log, "note": "llm KO: %s" % type(e).__name__}
        a = (act.get("action") or "").lower()
        log.append(
            {"step": step + 1, "action": a, "id": act.get("id"), "why": (act.get("why") or "")[:60]}
        )
        if a == "done":
            return {"ok": True, "steps": step + 1, "log": log, "note": "but atteint"}
        if a == "stop":
            return {
                "ok": False,
                "steps": step + 1,
                "log": log,
                "note": "agent stop: %s" % (act.get("why") or "")[:60],
            }
        if a == "scroll":
            human_scroll(page, 2)
            continue
        idx = act.get("id")
        if idx is None:
            continue
        sel = '[data-wn-ag="%s"]' % idx
        if a == "click":
            # final submit safeguard
            try:
                txt = page.locator(sel).first.inner_text(timeout=1500)
            except Exception:
                txt = ""
            if NEVER.search(txt or ""):
                return {
                    "ok": False,
                    "steps": step + 1,
                    "log": log,
                    "note": "refus clic submit final: %s" % txt[:40],
                }
            human_click(page, sel)
            page.wait_for_timeout(_rnd.randint(1000, 2000))
        elif a == "fill":
            val = act.get("value") or ""
            human_type(page, sel, val)
    return {"ok": False, "steps": max_steps, "log": log, "note": "max_steps atteint"}
