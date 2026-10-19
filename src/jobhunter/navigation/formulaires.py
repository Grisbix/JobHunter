"""Application forms: multi-screen wizard, document upload, filling in.

Part of jobhunter.navigation (formerly Scripts/web_nav.py, phase 3.6).

Decision: docs/adr/0005-aucune-soumission-automatique.md
"""

import random as _rnd
import re as _re_lex
from typing import Any

from jobhunter import racine as _racine
from jobhunter.navigation import navigateur as _navigateur
from jobhunter.navigation.carrieres import drill_to_offer, smart_step
from jobhunter.navigation.navigateur import human_click, human_pause
from jobhunter.navigation.page import (
    _COUNT_VISIBLE_INPUTS_JS,
    analyze,
    dismiss_cookies,
    wait_for_form,
)
from jobhunter.navigation.segment import (
    _ATS_DETECT_JS,
    _SCAN_FORM_FIELDS_JS,
    highlight_submit,
    try_open_form,
)

# ── #3 MULTI-SCREEN WIZARD (Workday/iCIMS: apply = 4-6 pages) ─────────────────
# Marks the "next step" button (NOT the final submit). Refuses send/submit.
_WIZARD_NEXT_JS = r"""
() => {
  const _deep=(root,acc)=>{root.querySelectorAll('button,input[type=submit],[role=button],a').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
  const NEXT=/(suivant|continuer|next|[eé]tape suivante|enregistrer et continuer|save (and|&) continue|continue to|passer a|proceed|weiter)/i;
  const FINAL=/(envoyer ma candidature|soumettre|submit application|submit your application|postuler maintenant|confirmer et envoyer|valider (et )?envoyer|finaliser (ma |la )?candidature|envoyer definitivement)/i;
  const els=_deep(document,[]).filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0;});
  document.querySelectorAll('[data-wn-wnext]').forEach(e=>e.removeAttribute('data-wn-wnext'));
  let final=false;
  for(const el of els){
    const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    if(!t||t.length>50) continue;
    if(FINAL.test(t.normalize('NFD').replace(/[̀-ͯ]/g,''))){ final=true; continue; }
    if(NEXT.test(t.normalize('NFD').replace(/[̀-ͯ]/g,''))){ el.setAttribute('data-wn-wnext','1'); el.scrollIntoView({block:'center'}); return {next:t.slice(0,40), final}; }
  }
  return {next:'', final};
}
"""


def run_wizard(page: Any, fill_fn: Any = None, max_screens: int = 6) -> dict[str, Any]:
    """#3 Goes through a MULTI-SCREEN application form (Workday/iCIMS/SmartRecruiters).

    Loop: fills the screen (fill_fn) + ticks the T&Cs + clicks "Next/Continue" (never
    the final submit) → next screen → repeats. Stops when only the final submit
    remains (up to you to click Send) or there is no more progress. fill_fn(page)->int:
    filling callback (the runner's autofill). Returns {screens, filled_total, stopped}.
    """
    filled_total, screens = 0, 0
    seen_urls = []
    for _ in range(max(1, max_screens)):
        screens += 1
        dismiss_cookies(page)
        wait_for_form(page, min_inputs=1, timeout_ms=4000)
        if fill_fn:
            try:
                filled_total += int(fill_fn(page) or 0)
            except Exception:
                pass
        try:
            accept_consent(page)
        except Exception:
            pass
        try:
            nav = page.evaluate(_WIZARD_NEXT_JS)
        except Exception:
            nav = {"next": "", "final": False}
        # only the final submit present -> stop (the human clicks Send)
        if not nav.get("next"):
            return {
                "screens": screens,
                "filled_total": filled_total,
                "stopped": "final_submit" if nav.get("final") else "no_next",
            }
        cur = None
        try:
            cur = page.url
        except Exception:
            pass
        try:
            human_click(page, '[data-wn-wnext="1"]')
            page.wait_for_timeout(_rnd.randint(1200, 2200))
        except Exception:
            return {"screens": screens, "filled_total": filled_total, "stopped": "click_fail"}
        # no progress (URL + DOM identical) -> stop
        try:
            if cur and page.url == cur and cur in seen_urls:
                return {"screens": screens, "filled_total": filled_total, "stopped": "no_progress"}
            seen_urls.append(cur)
        except Exception:
            pass
    return {"screens": screens, "filled_total": filled_total, "stopped": "max_screens"}


# ── Robust UPLOAD: matches CV vs Letter by label, handles hidden inputs ───────
_FILEINPUT_JS = r"""
() => {
  const norm=s=>(s||'').toLowerCase();
  const lab=el=>{let t='';if(el.id){const l=document.querySelector(`label[for="${el.id}"]`);if(l)t+=' '+l.textContent;}let p=el.closest('label,[class*=upload i],[class*=file i],[class*=dropzone i]');if(p)t+=' '+(p.innerText||'');t+=' '+(el.name||'')+' '+(el.getAttribute('aria-label')||'');return norm(t);};
  const out=[];
  document.querySelectorAll('input[type=file]').forEach((el,i)=>{
    el.setAttribute('data-wn-file', i);
    const t=lab(el);
    let kind='cv';
    if(/lettre|motivation|cover|recommand/.test(t)) kind='letter';
    else if(/cv|resume|résumé|curriculum/.test(t)) kind='cv';
    out.push({i, kind});
  });
  return out;
}
"""


def accept_consent(page: Any) -> Any:
    """Ticks the MANDATORY consent boxes (T&Cs, terms, privacy policy, data processing) needed to apply.

    Does NOT tick marketing opt-ins (newsletter, commercial offers).
    """
    js = r"""
    () => {
      const REQ = /(accepte|conditions|cgu|c\.g\.u|politique|traitement.*donn|j'?ai lu|termes|terms|privacy|consent|rgpd|mentions l)/i;
      const MKT = /(newsletter|marketing|commercial|actualit|offres|partenaires|promo)/i;
      let n = 0;
      const boxes = [...document.querySelectorAll('input[type=checkbox]')];
      for (const b of boxes) {
        if (b.checked || b.disabled) continue;
        // texte associé : label[for], parent, aria-label, texte voisin
        let t = '';
        if (b.id) { const l = document.querySelector(`label[for="${b.id}"]`); if (l) t += ' ' + l.innerText; }
        t += ' ' + (b.getAttribute('aria-label')||'');
        let p = b.closest('label') || b.parentElement;
        if (p) t += ' ' + (p.innerText||'');
        if (REQ.test(t) && !MKT.test(t)) {
          try { b.click(); n++; } catch(e){}
        }
      }
      return n;
    }"""
    try:
        return page.evaluate(js)
    except Exception:
        return 0


def _handle_smartrecruiters_iframe(page: Any) -> Any:
    r"""SmartRecruiters: click Apply button, wait for the application iframe, and return the frame object (or None if not applicable).

    SmartRecruiters loads the application form inside a dynamically created
    iframe after clicking an "Apply"/"Postuler" button. This function:
      1. Detects the Apply button using ATS-specific selectors
      2. Clicks it
      3. Waits up to 15 s for the iframe to appear
      4. Returns the iframe's Frame object so callers can switch context

    Returns:
        playwright.sync_api.Frame or None
    """
    import time as _time

    # Don't proceed if a form is already visible on the main page
    try:
        n_inputs = page.evaluate(_COUNT_VISIBLE_INPUTS_JS)
        if n_inputs >= 2:
            return None
    except Exception:
        pass

    # SmartRecruiters / generic ATS Apply button selectors (ordered by specificity)
    APPLY_SELECTORS = [
        "button[data-apply-button]",
        "button.sr-apply-button",
        '[data-qa="apply-button"]',
        "a[data-apply-button]",
        'button:has-text("Apply")',
        'button:has-text("Postuler")',
        'button:has-text("Candidater")',
        'button:has-text("Candidature")',
        'a:has-text("Apply")',
        'a:has-text("Postuler")',
        'a:has-text("Candidater")',
        '[class*="apply-button"]',
        '[class*="postuler"]',
        '[class*="candidater"]',
        # Generic fallback — any visible "postuler/apply" button
        'button:has-text("postuler"):not(:has-text("envoyer"))',
        'button:has-text("apply"):not(:has-text("submit"))',
    ]

    clicked = False
    for sel in APPLY_SELECTORS:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                loc.click(timeout=5000)
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        return None

    # Wait for the iframe to appear (up to 15 s)
    deadline = _time.time() + 15
    while _time.time() < deadline:
        try:
            for f in page.frames:
                if f == page.main_frame:
                    continue
                url = (f.url or "").lower()
                # Accept frames with smartrecruiters/apply URLs OR about:blank frames
                # that contain form fields (some ATS write forms into about:blank iframes)
                has_keyword = "smartrecruiters" in url or "/apply" in url
                if has_keyword or url in ("", "about:blank"):
                    # Verify the frame actually has form content
                    try:
                        n = f.evaluate(_COUNT_VISIBLE_INPUTS_JS)
                        if n > 0:
                            # Give content a moment to fully render
                            try:
                                f.wait_for_timeout(1000)
                            except Exception:
                                pass
                            return f
                    except Exception:
                        # Cross-origin — still worth returning the frame
                        if has_keyword:
                            return f
        except Exception:
            pass
        try:
            page.wait_for_timeout(500)
        except Exception:
            break

    return None


def apply_to_offer(
    page: Any,
    offer_url: str,
    profile: dict[str, Any],
    cv_path: Any = None,
    lettre_path: Any = None,
    submit_highlight: bool = True,
) -> Any:
    """Navigates to a job offer, fills ALL the form fields, uploads the CV + cover letter, and highlights the submit button.

    Args:
        page: Playwright page object
        offer_url: URL of the job offer
        profile: dict with the profile fields (apply_profile.json)
        cv_path: absolute path to the PDF CV (optional, takes precedence over profile)
        lettre_path: absolute path to the PDF letter (optional, takes precedence over profile)
        submit_highlight: if True, highlights the submit button in red (without clicking)

    Returns:
        dict: {success, filled_count, uploaded, submit_found, submit_label, ats_type, errors, steps}
    """
    import re as _re
    import time as _time
    from pathlib import Path as _P

    result: dict[str, Any] = {
        "success": False,
        "filled_count": 0,
        "uploaded": [],
        "submit_found": False,
        "submit_label": "",
        "ats_type": "unknown",
        "errors": [],
        "steps": [],
        "url": offer_url,
    }

    ROOT = _racine.racine()  # project root (marker, JOBHUNTER_RACINE)

    def _resolve_path(p: Any) -> str | None:
        if not p:
            return None
        pp = _P(p)
        if pp.is_absolute() and pp.exists():
            return str(pp)
        # try relative to root
        abs_p = ROOT / p
        if abs_p.exists():
            return str(abs_p)
        return str(pp) if pp.exists() else None

    # resolve CV and letter paths
    cv = _resolve_path(cv_path)
    letter = _resolve_path(lettre_path)
    if not cv:
        # try from profile cv_paths
        for domain_key in ["ESG_Finance_Durable", "default"]:
            p = profile.get("cv_paths", {}).get(domain_key)
            trouve = _resolve_path(p)
            if trouve:
                cv = trouve
                break
    if not letter:
        for domain_key in ["ESG_Finance_Durable", "default"]:
            p = profile.get("lettre_paths", {}).get(domain_key)
            trouve = _resolve_path(p)
            if trouve:
                letter = trouve
                break

    # ── Step 1: Navigate ──
    try:
        r = _navigateur.robust_goto(page, offer_url, tries=3)
        if not r["ok"]:
            result["errors"].append(f"Navigation échouée: {r.get('note', '?')}")
            return result
        result["steps"].append("navigated")
    except Exception as e:
        result["errors"].append(f"Goto error: {e}")
        return result

    _time.sleep(0.5)
    dismiss_cookies(page)
    human_pause(page, 500, 1000)

    # ── Step 2: Detect ATS ──
    try:
        ats = page.evaluate(_ATS_DETECT_JS)
        result["ats_type"] = ats.get("name", "unknown")
        result["steps"].append(f"ats:{result['ats_type']}")
    except Exception:
        pass

    # ── SmartRecruiters: iframe flow — click Apply & switch to iframe ──
    if result["ats_type"] == "smartrecruiters":
        sr_frame = _handle_smartrecruiters_iframe(page)
        if sr_frame is not None:
            result["steps"].append("sr_iframe_entered")
            page = sr_frame  # subsequent ops use the iframe context

    # ── Step 3: Try to open the form ──
    for attempt in range(4):
        info = analyze(page)
        kind = info.get("kind", "other")
        if kind in ("apply_form", "register", "login"):
            result["steps"].append(f"form_visible:{kind}")
            break
        if kind == "apply_cta":
            clicked = try_open_form(page)
            if clicked:
                result["steps"].append("clicked_apply_cta")
                page.wait_for_timeout(2000)
                continue
        elif kind == "offer_list":
            # try clicking first offer
            dr = drill_to_offer(page, "")
            if dr.get("found"):
                result["steps"].append("drilled_to_offer")
                page.wait_for_timeout(2000)
                continue
        # try smart_step
        r = smart_step(page, task="apply", max_tries=2)
        if r["status"] == "ok":
            result["steps"].append(f"smart_step:{r['kind']}")
            break
        elif r["status"] == "blocked":
            result["errors"].append(f"Blocked: {r.get('note', '')}")
            return result
        page.wait_for_timeout(1000)

    # Wait for dynamic form to render
    wait_for_form(page, min_inputs=1, timeout_ms=8000)
    human_pause(page, 300, 700)

    # ── Step 4: Scan form fields ──
    try:
        scan = page.evaluate(_SCAN_FORM_FIELDS_JS)
    except Exception as e:
        result["errors"].append(f"Scan error: {e}")
        scan = {"fields": [], "checkboxes": [], "fileInputs": [], "submits": []}

    # ── Step 5: Fill text/email/tel/textarea/select fields ──
    field_aliases = profile.get("field_aliases", {})
    filled = 0

    # Build reverse mapping: canonical key -> list of aliases
    canonical_map = {}
    for canonical, aliases in field_aliases.items():
        for alias in aliases:
            canonical_map[alias] = canonical

    def _find_profile_value(ctx: str) -> Any:
        """Match field context to profile key and return the value."""
        # Check each canonical key's aliases
        for alias, canonical in canonical_map.items():
            if _re.search(_re.escape(alias), ctx):
                return profile.get(canonical, "")
        # Fallback: direct regex matching
        for canonical, aliases in field_aliases.items():
            for alias in aliases:
                if _re.search(_re.escape(alias), ctx):
                    return profile.get(canonical, "")
        return None

    for f in scan.get("fields", []):
        if f["currentValue"] and f["currentValue"].strip():
            continue  # already filled
        ctx = f["ctx"]
        val = _find_profile_value(ctx)

        # Special cases: detect motivation/message fields
        if not val and f["tag"] == "TEXTAREA":
            if _re.search(
                r"(message|motivation|cover|lettre|pourquoi|presentation|about|commentaire|additional)",
                ctx,
            ):
                val = profile.get("message", "")
        if not val and f["tag"] == "SELECT":
            # Match dropdown context with profile keys
            if _re.search(r"(country|pays)", ctx):
                val = profile.get("pays", "France")
            elif _re.search(r"(availability|disponibilite|start|date_debut|notice|preavis)", ctx):
                val = profile.get("disponibilite", "Immédiate")
            elif _re.search(r"(salary|salaire|remuneration|pretention|wage)", ctx):
                val = profile.get("salaire_souhaite", "")

        if not val:
            continue

        try:
            loc = page.locator(f'[data-ao-idx="{f["idx"]}"]')
            if not loc.count():
                continue

            if f["tag"] == "SELECT":
                # Try to select matching option
                val_lower = val.lower()
                options = f.get("options") or []
                matched = None
                for opt in options:
                    if val_lower in opt["text"].lower():
                        matched = opt["value"]
                        break
                if matched:
                    loc.select_option(matched, timeout=2000)
                    filled += 1
                elif options:
                    # try clicking the select then the option
                    loc.click(timeout=2000)
                    page.wait_for_timeout(300)
                    # find option by text
                    for opt in options:
                        if val_lower in opt["text"].lower()[:20]:
                            try:
                                page.locator(f'option[value="{opt["value"]}"]').click(timeout=1000)
                                filled += 1
                                break
                            except Exception:
                                pass
            else:
                loc.click(timeout=1000)
                loc.fill(str(val), timeout=3000)
                filled += 1
                human_pause(page, 50, 150)
        except Exception as e:
            result["errors"].append(f"Fill '{f['name'] or f['id']}' failed: {e}")

    result["filled_count"] = filled
    result["steps"].append(f"filled:{filled}")

    # ── Step 6: Handle checkboxes (consent CGU/RGPD) ──
    cb_checked = accept_consent(page)
    if cb_checked:
        result["steps"].append(f"consent:{cb_checked}")

    # Handle radios: select first option for empty required radios
    radio_js = r"""
    () => {
      let n = 0;
      const groups = {};
      [...document.querySelectorAll('input[type=radio]')].forEach(r => {
        const name = r.name || r.id || 'unnamed';
        if (!groups[name]) groups[name] = [];
        groups[name].push(r);
      });
      for (const [name, radios] of Object.entries(groups)) {
        if (radios.every(r => !r.checked) && radios.some(r => r.required)) {
          try { radios[0].click(); n++; } catch(e){}
        }
      }
      return n;
    }
    """
    try:
        n_radios = page.evaluate(radio_js)
        if n_radios:
            result["steps"].append(f"radios:{n_radios}")
    except Exception:
        pass

    # ── Step 7: Upload CV + cover letter ──
    if cv or letter:
        # First try smart_upload
        try:
            up = smart_upload(page, cv, letter)
            if up:
                result["uploaded"] = up
                result["steps"].append(f"uploaded:{len(up)}")
        except Exception:
            pass

        # Fallback: direct file input approach if smart_upload didn't work
        if not result["uploaded"]:
            file_inputs = scan.get("fileInputs", [])
            if file_inputs:
                files_to_upload = [f for f in (cv, letter) if f]
                for i, fi in enumerate(file_inputs):
                    if i >= len(files_to_upload):
                        break
                    try:
                        loc = page.locator(f'[data-ao-file="{fi["idx"]}"]')
                        if loc.count():
                            loc.set_input_files(files_to_upload[i], timeout=3000)
                            result["uploaded"].append(_P(files_to_upload[i]).name)
                            result["steps"].append(f"uploaded:{_P(files_to_upload[i]).name}")
                    except Exception as e:
                        result["errors"].append(f"Upload failed: {e}")
            elif cv or letter:
                # Try generic file input selector
                try:
                    inputs = page.locator('input[type="file"]')
                    files_to_upload = [f for f in (cv, letter) if f]
                    for i in range(min(inputs.count(), len(files_to_upload))):
                        inputs.nth(i).set_input_files(files_to_upload[i], timeout=3000)
                        result["uploaded"].append(_P(files_to_upload[i]).name)
                except Exception as e:
                    result["errors"].append(f"Generic upload failed: {e}")

    # ── Step 8: Highlight submit button ──
    if submit_highlight:
        submit_js = r"""
        () => {
          const SUBMIT_RX = /(envoyer|soumettre|submit|valider|confirmer|send|apply|postuler|je postule|finalize|complete)/i;
          const NEVER = /(cancel|annuler|cancel|reset|reinitialiser|delete|supprimer|save (draft|brouillon)|preview|apercu)/i;
          const els = [...document.querySelectorAll('button,input[type=submit],a,[role=button]')];
          let best = null, bestScore = -1;
          for (const el of els) {
            const t = (el.innerText||el.value||el.getAttribute('aria-label')||'').trim().toLowerCase();
            if (!t || t.length > 60 || NEVER.test(t)) continue;
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            let s = 0;
            if (el.type === 'submit' || el.tagName === 'BUTTON') s += 2;
            if (SUBMIT_RX.test(t)) s += 3;
            if (/(envoyer|soumettre|submit)/i.test(t)) s += 2;
            if (el.classList && /submit|send|apply/i.test(el.className)) s += 1;
            if (s > bestScore) { bestScore = s; best = el; }
          }
          if (best && bestScore >= 3) {
            best.style.outline = '3px solid red';
            best.style.outlineOffset = '2px';
            best.style.boxShadow = '0 0 10px red';
            best.style.animation = 'pulse 1s infinite';
            const style = document.createElement('style');
            style.textContent = '@keyframes pulse { 0%,100% { box-shadow: 0 0 5px red; } 50% { box-shadow: 0 0 20px red; } }';
            document.head.appendChild(style);
            best.scrollIntoView({block:'center', behavior:'smooth'});
            best.setAttribute('data-ao-submit', '1');
            return { found: true, label: (best.innerText||best.value||'').trim().slice(0,50), score: bestScore };
          }
          return { found: false };
        }
        """
        try:
            sub = page.evaluate(submit_js)
            if sub.get("found"):
                result["submit_found"] = True
                result["submit_label"] = sub.get("label", "")
                result["steps"].append(f"submit_highlighted:{sub['label']}")
            else:
                # Fallback to existing highlight_submit function
                sub2 = highlight_submit(page)
                if sub2:
                    result["submit_found"] = True
                    result["submit_label"] = sub2
                    result["steps"].append(f"submit_highlighted_fallback:{sub2}")
                else:
                    result["errors"].append("Submit button not found")
        except Exception as e:
            result["errors"].append(f"Submit highlight error: {e}")

    result["success"] = filled > 0 or bool(result["uploaded"])
    return result


def smart_upload(page: Any, cv: Any, letter: Any) -> Any:
    """Uploads CV + letter by matching each input[type=file] by label (cv/letter).

    Hidden inputs are handled (set_input_files works even when not visible).
    """
    from pathlib import Path as _P

    done = []
    try:
        metas = page.evaluate(_FILEINPUT_JS)
    except Exception:
        metas = []
    files: dict[str, Any] = {
        "cv": cv if cv and _P(cv).exists() else None,
        "letter": letter if letter and _P(letter).exists() else None,
    }
    used = set()
    # 1) match by label
    for m in metas:
        f = files.get(m["kind"])
        if f and m["kind"] not in used:
            try:
                page.locator(f'[data-wn-file="{m["i"]}"]').set_input_files(f, timeout=3000)
                done.append(f"{m['kind']}:{_P(f).name}")
                used.add(m["kind"])
            except Exception:
                pass
    # 2) fallback: remaining inputs -> cv then letter in order of appearance
    order = [x for x in ("cv", "letter") if x not in used and files.get(x)]
    for m in metas:
        if not order:
            break
        k = order[0]
        try:
            page.locator(f'[data-wn-file="{m["i"]}"]').set_input_files(files[k], timeout=2500)
            done.append(f"{k}:{_P(files[k]).name}")
            used.add(k)
            order.pop(0)
        except Exception:
            pass
    return done


# ── UNIVERSAL APPLICATION FILLING: all the fields + all the documents ─────────
# Scans EVERY editable element (shadow DOM), classifies it, fills it. Coverage report.
_FILL_SCAN_JS = r"""
() => {
  const N=s=>(s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
  const deep=(root,acc,sel)=>{root.querySelectorAll(sel).forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)deep(e.shadowRoot,acc,sel);});return acc;};
  const lab=el=>{let t='';if(el.id){const l=document.querySelector(`label[for="${CSS.escape(el.id)}"]`);if(l)t+=' '+l.textContent;}const p=el.closest('label,.form-group,.field,.form-field,.input-group,[class*=field i],[class*=form-row i]');if(p)t+=' '+(p.textContent||'').slice(0,120);const pr=el.previousElementSibling;if(pr&&['LABEL','SPAN','DIV','P'].includes(pr.tagName))t+=' '+pr.textContent;return t;};
  const vis=el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  let k=0; const out=[];
  deep(document,[],'input,textarea,select').forEach(el=>{
    const type=(el.type||el.tagName).toLowerCase();
    if(['hidden','submit','button','image','reset','search'].includes(type))return;
    const key=N([el.name,el.id,el.placeholder,el.getAttribute('aria-label'),el.autocomplete,lab(el)].join(' '));
    // bug5 : ne PAS remplir les champs recherche d'offre / newsletter / filtre (pas le formulaire de candidature)
    const SKIP=/(recherch|\bsearch\b|\bquery\b|keyword|mot.?cle|filtre|\bfilter\b|newsletter|s'?abonn|subscribe|alerte.?(email|emploi|job))/;
    const inSearchForm=(()=>{const f=el.closest('form');if(!f)return false;const fa=N((f.id||'')+(f.className||'')+(f.getAttribute('role')||'')+(f.getAttribute('action')||''));return /search|recherch|newsletter|subscribe|abonn/.test(fa);})();
    if((SKIP.test(key)||inSearchForm) && type!=='file'){return;}
    el.setAttribute('data-wn-fa',k);
    const o={i:k,tag:el.tagName,type,key:key.slice(0,140),
      required:el.required||el.getAttribute('aria-required')==='true',
      filled:!!(el.value&&String(el.value).trim() && type!=='radio' && type!=='checkbox'),
      vis:vis(el)};
    if(el.tagName==='SELECT') o.options=[...el.options].map(x=>({t:(x.text||'').trim(),v:x.value}));
    if(type==='radio') o.rvalue=N(el.value+' '+lab(el));
    if(type==='checkbox') o.checked=el.checked;
    out.push(o); k++;
  });
  return out;
}
"""


# rich lexicon: (regex on the field's context) -> profile key. Order = priority.
_PROFILE_LEX = [
    (r"(e-?mail|courriel|identifiant|username|login|user_?mail)", "email"),
    (r"(first.?name|f.?name|fname|pr[eé]nom|given.?name|vorname|nome)", "prenom"),
    (r"(last.?name|l.?name|lname|surname|family.?name|nom de famille|nachname|\bnom\b)", "nom"),
    (r"(date.?de.?naissance|birth|naissance|geburt|d\.?o\.?b|nascita)", "date_naissance"),
    (r"(nationalit|nationality|staatsang)", "nationalite"),
    (r"(linked ?in)", "linkedin"),
    (r"(github)", "github"),
    (r"(portfolio|site ?web|website|url perso|personal (site|web)|book)", "site_web"),
    (r"(mobile|portable|handy|t[eé]l[eé]?(phone)?|phone|num[eé]ro|tel\b)", "tel"),
    (r"(code postal|zip|postal|\bcp\b|plz|postcode)", "cp"),
    (r"(city|ville|localit|commune|stadt|citt)", "ville"),
    (r"(country|pays|land|nation)", "pays"),
    (r"(adresse|address|rue|street|stra[sß]e|via\b|voie)", "adresse"),
    (
        r"(disponibilit|availability|date.*(d[eé]but|entr[eé]e)|start date|preavis|pr[eé]avis|notice)",
        "disponibilite",
    ),
    (
        r"(salaire|salary|r[eé]mun[eé]ration|pr[eé]tention|expected.*(salary|comp)|gehalt|package)",
        "salaire_souhaite",
    ),
    (r"(mobilit|mobility|relocation|d[eé]m[eé]nag|willing to move)", "mobilite"),
    (r"(permis|driver|driving licen|f[üu]hrerschein)", "permis"),
    (
        r"(niveau.?(d')?[eé]tude|degree|dipl[oô]me|education level|study level|abschluss|qualification)",
        "niveau_etudes",
    ),
    (
        r"(poste actuel|dernier poste|current (position|job|role|title)|current employer|employeur actuel|titre du poste)",
        "dernier_poste",
    ),
    (r"(langue|language|sprach|lingua)", "langues"),
    (r"(comp[eé]tence|skills|comp[eé]tences cl[eé]|kenntnisse)", "competences"),
    (
        r"(message|motivation|lettre|cover|pourquoi|presentation|about you|tell us|parlez|why|motiv|commentaire|comment)",
        "message",
    ),
    (
        r"(full.?name|nom complet|votre nom|\bname\b|vollst[aä]ndiger name)",
        "full",
    ),  # generic last
]


def _match_profile_key(key: str) -> str | None:
    for rx, pk in _PROFILE_LEX:
        if _re_lex.search(rx, key):
            return pk
    return None


_CONSENT_DIALOG_JS = r"""
() => {
  const vis = el => { const r=el.getBoundingClientRect(); return r.width>4 && r.height>4; };
  // dialogue de consentement obligatoire : bouton Proceed/Continuer/Accepter (PAS Decline/Refuser)
  const OK = /^(proceed|continuer|continue|accept|accepter|j'?accepte|i agree|agree|allow|ok|confirmer|confirm|valider|weiter|akzeptieren)$/i;
  const NO = /(decline|refuser|cancel|annuler|reject|ablehnen)/i;
  const dialogs = [...document.querySelectorAll('[role=dialog],[aria-modal="true"],.modal,.dialog,[class*="dialog" i],[class*="modal" i]')].filter(vis);
  for (const dg of dialogs) {
    const txt = (dg.innerText||'').toLowerCase();
    if (!/(consent|privacy|confidentialit|données|data|conditions|terms|traitement|rgpd|gdpr)/.test(txt)) continue;
    const btn = [...dg.querySelectorAll('button,a,[role=button]')].filter(vis)
      .find(b => { const t=(b.innerText||b.value||'').trim(); return t && t.length<20 && OK.test(t) && !NO.test(t); });
    if (btn) { btn.click(); return {clicked: (btn.innerText||'').trim()}; }
  }
  return {clicked: ''};
}
"""


def accept_consent_dialog(page: Any) -> Any:
    """Clique Proceed/Continuer d'un dialogue de consentement obligatoire (≠ submit, ≠ Decline)."""
    try:
        return page.evaluate(_CONSENT_DIALOG_JS)
    except Exception:
        return {"clicked": ""}


def _best_form_target(page: Any) -> Any:
    """Returns the context (page OR iframe) that contains the real form.

    SmartRecruiters/Taleo/SuccessFactors load the form in an iframe: we choose the
    frame with the most visible input fields.
    """
    try:
        best_n = page.evaluate(_COUNT_VISIBLE_INPUTS_JS)
    except Exception:
        best_n = 0
    best = page
    try:
        main = page.main_frame
    except Exception:
        main = None
    for fr in getattr(page, "frames", []):
        if fr is main:
            continue
        try:
            if fr.is_detached():  # dead frame (page changed) → never a target
                continue
        except Exception:
            continue
        try:
            n = fr.evaluate(_COUNT_VISIBLE_INPUTS_JS)
        except Exception:
            continue
        if n > best_n + 1:  # margin: does not switch for 1 isolated field
            best, best_n = fr, n
    return best


def fill_application(
    page: Any, profile: dict[str, Any], cv: Any = None, letter: Any = None, docs: Any = None
) -> dict[str, Any]:
    """UNIVERSAL APPLY: recognises ALL the field patterns and fills everything — text/email/tel/date/select(dropdown)/radio(title)/checkbox(T&Cs)/textarea + upload of ALL the documents (CV, letter, + extra docs by label).

    Looks for the form in the iframes (SmartRecruiters/Taleo) if the page is empty.
    Returns {total, filled, uploaded, consent, cover_pct, unmatched:[…]}.
    """
    from pathlib import Path as _P

    page = _best_form_target(page)  # switches to the form's iframe if needed
    try:
        fields = page.evaluate(_FILL_SCAN_JS)
    except Exception:
        return {
            "total": 0,
            "filled": 0,
            "uploaded": 0,
            "consent": 0,
            "cover_pct": 0,
            "unmatched": [],
        }
    filled = 0
    unmatched = []
    text_fields = [f for f in fields if f["type"] not in ("radio", "checkbox", "file")]
    for f in text_fields:
        if f["filled"]:
            filled += 1
            continue  # already filled
        pk = _match_profile_key(f["key"])
        val = profile.get(pk) if pk else None
        if not val:
            if f["vis"] and f.get("required"):
                unmatched.append(f["key"][:40])
            continue
        loc = page.locator(f'[data-wn-fa="{f["i"]}"]').first
        try:
            if f["tag"] == "SELECT":
                if _pick_option(loc, f.get("options", []), str(val)):
                    filled += 1
            else:
                loc.fill(str(val), timeout=2500)
                filled += 1
        except Exception:
            pass
    # SELECT without a profile value: title -> Monsieur, country -> France
    for f in [x for x in fields if x["tag"] == "SELECT" and not x["filled"]]:
        if _re_lex.search(r"(civilit|title|anrede)", f["key"]):
            if _pick_option(
                page.locator(f'[data-wn-fa="{f["i"]}"]').first,
                f.get("options", []),
                "monsieur",
                extra=("m.", "mr", "male", "herr"),
            ):
                filled += 1
        elif _re_lex.search(r"(pays|country|land)", f["key"]):
            if _pick_option(
                page.locator(f'[data-wn-fa="{f["i"]}"]').first,
                f.get("options", []),
                "france",
                extra=("fr",),
            ):
                filled += 1
    # title RADIO (Monsieur / M.)
    radios = [f for f in fields if f["type"] == "radio"]
    if radios and not any(
        f.get("checked")
        for f in radios
        if _re_lex.search(r"civilit|monsieur|male|masculin", f.get("rvalue", ""))
    ):
        for f in radios:
            rv = f.get("rvalue", "")
            if _re_lex.search(
                r"(civilit|monsieur|\bm\.?\b|\bmr\b|male|masculin|herr)", rv
            ) and not _re_lex.search(r"(madame|mme|female|frau)", rv):
                try:
                    page.locator(f'[data-wn-fa="{f["i"]}"]').first.check(timeout=1500)
                    filled += 1
                    break
                except Exception:
                    pass
    # mandatory consent CHECKBOX (T&Cs/GDPR) — not marketing
    consent = 0
    for f in [x for x in fields if x["type"] == "checkbox" and not x.get("checked")]:
        if _re_lex.search(
            r"(cgu|cgv|condition|politique|traitement.*donn|j'?ai lu|termes|terms|privacy|consent|rgpd|mentions|accept)",
            f["key"],
        ) and not _re_lex.search(
            r"(newsletter|marketing|commercial|actualit|offres|promo|partenaires)", f["key"]
        ):
            try:
                page.locator(f'[data-wn-fa="{f["i"]}"]').first.check(timeout=1500)
                consent += 1
            except Exception:
                pass
    # bug7: after ticking the T&Cs, a consent dialog (Proceed/Continuer) may open
    # (SuccessFactors #dataPrivacyId). Clicking Proceed = validating the mandatory box, NOT submitting.
    if consent:
        try:
            page.evaluate(_CONSENT_DIALOG_JS)
        except Exception:
            pass
    # UPLOAD all documents: CV + letter by label + extra docs
    uploaded = smart_upload(page, cv, letter)
    if docs:  # docs = liste de chemins additionnels -> file inputs restants
        try:
            metas = page.evaluate(_FILEINPUT_JS)
            free = [m for m in metas]
            for path in docs:
                if not (path and _P(path).exists()):
                    continue
                for m in free:
                    try:
                        page.locator(f'[data-wn-file="{m["i"]}"]').set_input_files(
                            path, timeout=2500
                        )
                        uploaded.append("doc:" + _P(path).name)
                        free.remove(m)
                        break
                    except Exception:
                        pass
        except Exception:
            pass
    total = len([f for f in fields if f["vis"] and f["type"] not in ("radio", "checkbox")])
    cover = round(100 * filled / total) if total else 0
    return {
        "total": total,
        "filled": filled,
        "uploaded": len(uploaded),
        "docs": uploaded,
        "consent": consent,
        "cover_pct": cover,
        "unmatched": unmatched[:8],
    }


def _fold(s: str) -> str:
    """Minuscule + sans accents (Française→francaise) pour matcher les <option>."""
    import unicodedata as _ud

    return "".join(
        c for c in _ud.normalize("NFD", str(s).lower()) if _ud.category(c) != "Mn"
    ).strip()


def _pick_option(loc: Any, options: Any, val: Any, extra: Any = ()) -> bool:
    """Selects the option of a <select> matching val (label/value), + extra variants.

    Accent-insensitive + ISO code match (option value='FR' for 'France').
    """
    cands = [_fold(val)] + [_fold(e) for e in extra]
    try:
        for i, o in enumerate(options):
            t = _fold(o.get("t") or "")
            ov = _fold(o.get("v") or "")
            if not t and not ov:
                continue
            for c in cands:
                if c and (c in t or t in c or c == ov or (len(c) >= 4 and ov and ov == c[:2])):
                    loc.select_option(index=i, timeout=2000)
                    return True
    except Exception:
        pass
    return False
