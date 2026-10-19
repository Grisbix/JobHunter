"""Trouver la page carriere d'une societe, puis l'offre dedans.

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6).
"""

import importlib
from typing import Any

from jobhunter import racine as _racine
from jobhunter.navigation import navigateur as _navigateur
from jobhunter.navigation.compte import react_submit
from jobhunter.navigation.etapes import (
    _unstick,
    click_portal_login,
    expand_hamburger_menu,
    hover_menus,
    retry,
)
from jobhunter.navigation.llm import vision_pick
from jobhunter.navigation.page import (
    ANALYZE_JS,
    analyze,
    click_for_task,
    dismiss_cookies,
    dismiss_overlays,
    pick_js,
)
from jobhunter.navigation.segment import detect_ats


def smart_step(
    page: Any,
    task: str,
    target_kinds: tuple[str, ...] = ("apply_form", "register", "login"),
    max_tries: int = 6,
) -> dict[str, Any]:
    """Fait avancer la page vers l'une des cibles, en essayant des stratégies dans l'ordre.

    Cookies, clic sur le bon lien, page carrières, menus, portail… Un CAPTCHA ou un
    blocage arrête et passe la main : rien n'est contourné.

    Args:
        page: la page Playwright.
        task: l'intention (« apply », « login »…).
        target_kinds: les types de page qui terminent la recherche.
        max_tries: nombre maximal d'essais.

    Returns:
        {status: ok | stuck | blocked, kind, note, …}.
    """
    strategies = [
        "cookies",
        "click",
        "careers",
        "hover",
        "portal",
        "scroll",
        "wait",
        "iframe",
        "reload",
    ]
    rate_hits = 0
    for attempt in range(max_tries):
        info = analyze(page)
        kind = info.get("kind", "other")
        # captcha = humain direct (jamais contourné)
        if info.get("captcha"):
            return {"status": "blocked", "kind": kind, "note": "captcha — humain requis"}
        # rate-limit / anti-bot soft = backoff exponentiel + reload AVANT de rendre la main
        if info.get("blocked"):
            if info.get("rateLimited") and rate_hits < 3:
                wait = min(2**rate_hits * 4000, 30000)  # 4s,8s,16s
                rate_hits += 1
                try:
                    page.wait_for_timeout(wait)
                    page.reload(timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                except Exception:
                    pass
                continue
            return {"status": "blocked", "kind": kind, "note": "anti-bot — humain requis"}
        if kind in target_kinds:
            return {"status": "ok", "kind": kind, "note": "atteint a l'essai %d" % (attempt + 1)}
        # apply_cta : bouton Apply/Candidater visible mais pas de form encore → cliquer
        if kind == "apply_cta":
            lbl = click_for_task(page, task)
            if not lbl:  # fallback: essayer register/login
                lbl = click_for_task(page, "register") or click_for_task(page, "login")
            if lbl:
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=4000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)
                continue  # re-analyse après clic
        strat = strategies[attempt % len(strategies)]
        try:
            if strat == "cookies":
                dismiss_cookies(page)
                dismiss_overlays(page)
            elif strat == "click":
                dismiss_overlays(page)  # écarte widgets chat qui interceptent le clic
                lbl = click_for_task(page, task)
                if lbl:
                    page.wait_for_timeout(1200)
            elif strat == "careers":
                # home corporate -> section Carrières/Nous rejoindre/Careers avant login/offre
                # v5.1: expand hamburger + hover_menus AVANT le scan carrière
                expand_hamburger_menu(page)
                page.wait_for_timeout(500)
                hover_menus(page)
                page.wait_for_timeout(500)
                gc = goto_careers(page)
                if gc.get("clicked"):
                    page.wait_for_timeout(1000)
            elif strat == "hover":
                if hover_menus(page):  # dérouler sous-menu puis re-cliquer
                    lbl = click_for_task(page, task)
                    if lbl:
                        page.wait_for_timeout(1200)
            elif strat == "portal":
                # UBS / portails multi-liens : clic lien login → form login
                if click_portal_login(page):
                    page.wait_for_timeout(2000)
                    # re-analyse après clic portal
                    info2 = analyze(page)
                    if info2.get("kind") in target_kinds:
                        return {
                            "status": "ok",
                            "kind": info2["kind"],
                            "note": "portal link clicked → %s" % info2["kind"],
                        }
            elif strat == "scroll":
                page.mouse.wheel(0, 1200)
            elif strat == "wait":
                page.wait_for_timeout(2500)
            elif strat == "iframe":
                for fr in page.frames:
                    try:
                        fi = fr.evaluate(ANALYZE_JS)
                        if fi.get("kind") in target_kinds:
                            return {
                                "status": "ok",
                                "kind": fi["kind"],
                                "note": "form dans une iframe",
                                "frame": fr.url,
                            }
                    except Exception:
                        pass
            elif strat == "reload":
                page.reload(timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
        except Exception:
            pass
    # dernier recours : vision LLM (Ollama llava) — "voit" le bon bouton
    v = vision_pick(page, task)
    if v.get("clicked"):
        page.wait_for_timeout(1500)
        info = analyze(page)
        if info.get("kind") in target_kinds:
            return {
                "status": "ok",
                "kind": info["kind"],
                "note": "vision LLM: '%s'" % v.get("label", ""),
            }
    return {
        "status": "stuck",
        "kind": analyze(page).get("kind", "other"),
        "note": "objectif non atteint apres %d essais — verifie a la main" % max_tries,
    }


# ── #9 DRILL : page carrière (liste d'offres) -> entrer dans la bonne offre ───
def _drill_js(role_hint: str, job_rx: str = "") -> str:
    import json as _j

    hint = _j.dumps((role_hint or "").lower())
    # pattern liens d'offre : celui de l'ATS détecté, sinon générique
    jrx = _j.dumps(job_rx or r"/(jobs?|offre|emploi|career|poste|vacan|position|stelle|opening)s?/")
    return r"""
    ((HINT, JRX) => {
      const _deep=(root,acc)=>{root.querySelectorAll('a[href]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
      let JOB; try { JOB=new RegExp(JRX,'i'); } catch(e){ JOB=/\/(jobs?|offre|emploi|career|poste|vacan)s?\//i; }
      // titre de poste dans le TEXTE du lien (cartes JS sans /jobs/ dans l'href)
      const JOBTXT=/(analyste?|analyst|charg[eé]|manager|consultant|d[eé]veloppeur|developer|ing[eé]nieur|engineer|responsable|assistant|stagiaire|alternan|apprenti|directeur|conseiller|auditeur|gestionnaire|technicien|comptable|juriste|business|data|risk|esg|finance|quant)/i;
      const CARD=/(job|offer|offre|vacan|opening|position|poste|career|carriere|listing|result|card)/i;
      const inCard=a=>{let p=a.closest('[class],[data-testid],[data-automation-id],li,article'); for(let d=0;p&&d<3;d++){const s=((p.className&&p.className.toString?p.className.toString():'')+' '+(p.getAttribute('data-testid')||'')+' '+(p.getAttribute('data-automation-id')||'')); if(CARD.test(s))return true; p=p.parentElement;} return false;};
      const links=_deep(document,[]).filter(a=>{
        const r=a.getBoundingClientRect(); if(r.width<=0||r.height<=0) return false;
        const t=(a.innerText||a.getAttribute('aria-label')||'').trim();
        return JOB.test(a.href) || (t.length>6 && t.length<90 && (JOBTXT.test(t) || inCard(a)));
      });
      if(!links.length) return {found:false};
      const words=HINT.split(/\s+/).filter(w=>w.length>3);
      let best=links[0],score=-1;
      for(const a of links){
        const t=(a.innerText||a.getAttribute('aria-label')||a.href||'').toLowerCase();
        let s=0; for(const w of words){ if(t.includes(w)) s++; }
        if(s>score){score=s;best=a;}
      }
      document.querySelectorAll('[data-wn-drill]').forEach(e=>e.removeAttribute('data-wn-drill'));
      best.setAttribute('data-wn-drill','1'); best.scrollIntoView({block:'center'});
      return {found:true, label:(best.innerText||best.href||'').trim().slice(0,60), score, n:links.length};
    })(%s, %s)
    """ % (hint, jrx)


# Champ recherche d'offres sur page carrière : tape le rôle -> fait surgir l'offre.
_SEARCH_JS = r"""
() => {
  const _deep=(root,acc)=>{root.querySelectorAll('input,textarea').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
  const RX=/(recherch|search|mot[- ]?cl[eé]|keyword|poste|m[eé]tier|intitul[eé]|job title|what.*looking|quel.*poste|filtr)/i;
  const ins=_deep(document,[]).filter(el=>{
    const t=(el.type||'').toLowerCase();
    if(['hidden','password','checkbox','radio','file','submit','button','email','tel','number'].includes(t))return false;
    const r=el.getBoundingClientRect(); if(r.width<40||r.height===0)return false;
    return true;
  });
  let best=null;
  for(const el of ins){
    const key=[el.name,el.id,el.placeholder,el.getAttribute('aria-label'),el.type].join(' ');
    if(el.type==='search'||RX.test(key)){ best=el; break; }
  }
  if(!best && ins.length===1) best=ins[0];   // 1 seul champ visible -> c'est lui
  document.querySelectorAll('[data-wn-search]').forEach(e=>e.removeAttribute('data-wn-search'));
  if(best){ best.setAttribute('data-wn-search','1'); best.scrollIntoView({block:'center'}); return {found:true, ph:(best.placeholder||best.getAttribute('aria-label')||best.name||'').slice(0,40)}; }
  return {found:false};
}
"""


def search_careers(page: Any, query: str) -> dict[str, Any]:
    """Tape le rôle dans le champ recherche d'offres de la page carrière puis soumet (Enter).

    Fait surgir l'offre quand la liste ne la montre pas. Retour {searched, ph}.
    """
    if not query:
        return {"searched": False}
    try:
        r = page.evaluate(_SEARCH_JS)
    except Exception:
        return {"searched": False}
    if not r or not r.get("found"):
        return {"searched": False}
    try:
        loc = page.locator('[data-wn-search="1"]').first
        loc.click(timeout=3000)
        loc.fill(str(query)[:60], timeout=3000)
        page.wait_for_timeout(400)
        loc.press("Enter", timeout=3000)
        page.wait_for_timeout(2500)
        return {"searched": True, "ph": r.get("ph", ""), "q": str(query)[:60]}
    except Exception:
        # fallback : requestSubmit du form contenant le champ
        try:
            react_submit(page)
            page.wait_for_timeout(2000)
            return {"searched": True, "ph": r.get("ph", ""), "q": str(query)[:60]}
        except Exception:
            return {"searched": False, "ph": r.get("ph", "")}


# ── DEEP CAREER SCAN : scan complet de la page pour trouver les liens carrière ──
# Stratégies :
#  1. Scan ALL <a> hrefs pour patterns career (careers, jobs, recrutement, stellen, etc.)
#  2. Scan innerText de TOUS les éléments visibles pour mots-clés career, remonte au parent cliquable
#  3. Scan data-attributes (data-nav, data-track, data-category, data-section, data-href)
#  4. Scan structures nav/menu/header (<nav>, [class*=nav], [class*=menu], [class*=header])
#  5. Pour les éléments JS-only (no href, onclick/event): retourne élément pour .click() JS dispatch
#  6. Scoring: href match (+4), text match (+3), header/nav context (+2), short text (+1)
_DEEP_CAREER_SCAN_JS = r"""
(() => {
  const CAREER_HREF = /\/(career|carr[ièe]re|job|emplo|recrut|talent|stellen|karriere|beruf|vacanc|vacature|opening|position|offer|work|apply|join)/i;
  const CAREER_DATA = /^(careers?|jobs?|recrut|talent|stellen|karriere|emplo|vacanc)/i;

  // Detecte le texte de carrière dans n'importe quel élément
  const _isCareerText = (t) => {
    if (!t) return false;
    const lo = t.toLowerCase();
    // v5.1: frontières permissives (^|\\s|['\"(\\[{])...(?:$|\\s|['\")\\]}!?,;.])
    // pour gérer les composés et non-ASCII
    const B = '(?:^|[\\s\\W])'; const E = '(?:$|[\\s\\W])';
    const KW_LIST = [
      'carri[eè]res?', 'careers?', 'nous rejoindre', 'rejoign(?:ez|dre)', 'recrutement',
      'recrute', 'recruiting', 'nos offres', "offres? d'?emploi",
      'espace candidat', 'espace recrutement', 'espace carri[eè]re',
      'travailler (?:avec|chez|pour) nous', 'travailler ensemble', 'talents?', 'emplois?',
      'join (?:us|our team|the team)', 'work (?:with|for|at) us', 'working (?:here|at)',
      'jobs?', 'vacanc(?:y|ies)', 'openings?', 'opportunit(?:y|ies)',
      "we'?re hiring", 'life at', 'karriere', 'stellen(?:angebote)?', 'mitarbeiter werden', 'beruf',
      'talent community', 'talent network', 'talent acquisition', 'candidate portal', 'career portal',
      'job alerts?', 'talent (?:pool|pipeline)', 'candidature spontan[eé]e',
      'spontaneous application', 'open positions?', 'job opportunities?', 'current openings?',
      'werken bij', 'vacatures?', 'postuler', 'candidater', 'apply now',
      'd[eé]poser (?:votre |ma |une )?candidature', 'emplois? et carri[eè]res?',
      'd[eé]couvr(?:ez|ir) nos (?:offres|m[eé]tiers|postes)', 'nos m[eé]tiers', 'rejoins?-nous',
      'graduate', 'graduates?', 'early careers?', 'early talent', 'students?', 'apprentice', 'internship',
      'apprentissage', 'alternance', 'stag(?:es?|iaires?)',
      'ressources humaines', 'RH', 'human resources?', 'people (?:and|&) culture',
      'our (?:people|team|culture)', 'why work', 'come (?:work|join) (?:with )?us',
      'make (?:a difference|an impact)', 'grow with us', 'employer branding', 'employeur',
      'bist du dabei', 'werde teil', 'aventure humaine',
      'job offers?', 'job openings?', 'find (?:a |your )?job', 'search jobs?', 'view (?:all |our )?jobs?',
      'lavora con noi', 'posizioni aperte', 'trabaja con nosotros',
      'unsolicited application', 'current openings?',
    ];
    for (const kw of KW_LIST) {
      try {
        const rx = new RegExp(B + kw + E, 'i');
        if (rx.test(lo)) return true;
      } catch(e) {}
    }
    return false;
  };

  // Remonte au parent cliquable le plus proche
  const _findClickableAncestor = (el, maxDepth) => {
    let n = el, d = 0;
    const CLICKABLE_TAGS = new Set(['A','BUTTON','INPUT','SUMMARY','LABEL']);
    while (n && d < (maxDepth || 6)) {
      const tag = n.tagName || '';
      if (CLICKABLE_TAGS.has(tag)) return n;
      if (n.hasAttribute && (n.hasAttribute('onclick') || n.hasAttribute('role') || n.hasAttribute('tabindex'))) return n;
      if (n.getAttribute && n.getAttribute('href')) return n;
      const cls = (n.className || '').toLowerCase();
      if (/nav|menu|btn|cta|link|click|item/.test(cls)) return n;
      n = n.parentElement;
      d++;
    }
    return el; // fallback: retourne l'élément original
  };

  // Collecte tous les éléments de navigation/menu (v5.1: patterns étendus)
  const NAV_SELECTORS = 'nav a, nav button, nav li, nav [role=button], nav [onclick],' +
    '[class*="nav" i] a, [class*="nav" i] button, [class*="nav" i] li, [class*="nav" i] [onclick],' +
    '[class*="navbar" i] a, [class*="navbar" i] button, [class*="navbar" i] li,' +
    '[class*="menu" i] a, [class*="menu" i] button, [class*="menu" i] li, [class*="menu" i] [onclick],' +
    '[class*="header" i] a, [class*="header" i] button, [class*="header" i] li,' +
    '[class*="topbar" i] a, [class*="topbar" i] button,' +
    '[class*="top" i] a, [class*="top" i] button,' +
    '[class*="mega" i] a, [class*="mega" i] button,' +
    '[class*="dropdown" i] a, [class*="dropdown" i] button,' +
    '[class*="hamburger" i] a, [class*="hamburger" i] button,' +
    '[class*="burger" i] a, [class*="burger" i] button,' +
    '[role="navigation"] a, [role="navigation"] button, [role="navigation"] li,' +
    '[id*="nav" i] a, [id*="nav" i] button, [id*="nav" i] li,' +
    '[id*="menu" i] a, [id*="menu" i] button, [id*="menu" i] li,' +
    '[id*="header" i] a, [id*="header" i] button,' +
    'footer a, footer button';

  const _vis = el => {
    try { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
    catch(e) { return false; }
  };

  const candidates = []; // {el, score, reason, href}

  // === PASS 0: Scan React Router <a> sans href + boutons onclick ===
  const jsLinks = [...document.querySelectorAll('a:not([href]), button, [onclick], [role=link], span[data-href], div[data-href], [data-url], [data-route]')].filter(_vis);
  for (const el of jsLinks) {
    const href = (el.getAttribute('data-href') || el.getAttribute('data-url') || el.getAttribute('data-route') || el.getAttribute('onclick') || '').toLowerCase();
    const txt = (el.innerText || el.getAttribute('aria-label') || el.title || '').trim();
    let score = 0, reason = '';
    if (CAREER_HREF.test(href)) { score += 4; reason = 'js_href_match'; }
    if (_isCareerText(txt)) { score += 3; if (!reason) reason = 'js_text_match'; }
    if (txt.length > 0 && txt.length < 40) score += 1;
    if (score > 0) candidates.push({el, score, reason, href: href});
  }

  // === PASS 1: Scan ALL <a> hrefs pour patterns career ===
  const allLinks = [...document.querySelectorAll('a[href]')].filter(_vis);
  for (const a of allLinks) {
    const href = (a.getAttribute('href') || '').toLowerCase();
    const txt = (a.innerText || a.getAttribute('aria-label') || a.title || '').trim();
    let score = 0, reason = '';

    if (CAREER_HREF.test(href)) {
      score += 4; reason = 'href_match';
      // Bonus: href très spécifique
      if (/\/(careers?|jobs?|recrut|talent|stellen|karriere)\b/i.test(href)) score += 2;
    }
    if (_isCareerText(txt)) {
      score += 3;
      if (!reason) reason = 'text_match';
    }
    if (txt.length > 0 && txt.length < 40) score += 1; // texte court = plus probable
    // Exclure les faux positifs
    const badHref = /(newsletter|subscribe|investor|press|media|contact|about|privacy|terms|cookie|legal|sitemap|mentions|CGU|CGV)/i;
    if (badHref.test(href) && score < 5) score = 0;
    const badText = /(newsletter|subscribe|s['\u2019]?abonner|investor|press|media|contactez?[ -]?nous|mentions l[eé]gales)/i;
    if (badText.test(txt) && score < 5) score = 0;

    if (score > 0) candidates.push({el: a, score, reason, href: a.getAttribute('href')});
  }

  // === PASS 2: Scan innerText de TOUS les éléments visibles dans nav/menu ===
  try {
    const navEls = [...document.querySelectorAll(NAV_SELECTORS)].filter(_vis);
    for (const el of navEls) {
      // Éviter les doublons déjà capturés en PASS 1
      if (el.tagName === 'A' && el.getAttribute('href')) {
        const already = candidates.some(c => c.el === el);
        if (already) continue;
      }
      const txt = (el.innerText || el.getAttribute('aria-label') || el.title || '').trim();
      if (_isCareerText(txt)) {
        const clickable = _findClickableAncestor(el, 4);
        // Vérifier si ce clickable a déjà été ajouté
        const dup = candidates.some(c => c.el === clickable);
        if (!dup) {
          candidates.push({el: clickable, score: 3, reason: 'nav_text_match', href: clickable.getAttribute ? (clickable.getAttribute('href') || '') : ''});
        }
      }
    }
  } catch(e) {}

  // === PASS 3: Scan data-attributes + aria-label ===
  try {
    const DATA_ATTRS = ['data-nav', 'data-menu', 'data-track', 'data-category', 'data-section', 'data-href', 'data-page', 'data-link', 'data-testid', 'data-target', 'data-action', 'data-route', 'data-path', 'data-url', 'data-gtm-category', 'data-layer', 'data-component', 'data-module', 'data-cy', 'aria-label'];
    for (const attr of DATA_ATTRS) {
      const selector = attr === 'aria-label' ? `[${attr}*="career" i],[${attr}*="carri" i],[${attr}*="job" i],[${attr}*="recrut" i],[${attr}*="talent" i],[${attr}*="stellen" i],[${attr}*="emplo" i],[${attr}*="work" i],[${attr}*="join" i]` : `[${attr}]`;
      try {
        const els = [...document.querySelectorAll(selector)].filter(_vis);
        for (const el of els) {
          const val = attr === 'aria-label' ? (el.getAttribute('aria-label') || '').toLowerCase() : (el.getAttribute(attr) || '').toLowerCase();
          if (CAREER_DATA.test(val)) {
            const clickable = _findClickableAncestor(el, 4);
            const dup = candidates.some(c => c.el === clickable);
            if (!dup) {
              candidates.push({el: clickable, score: 3, reason: 'data_attr_' + attr, href: clickable.getAttribute ? (clickable.getAttribute('href') || '') : ''});
            }
          }
        }
      } catch(e) {}
    }
  } catch(e) {}

  // === PASS 3.5: Scan inside iframes (Taleo, iCIMS, SuccessFactors embed) ===
  try {
    const iframes = document.querySelectorAll('iframe');
    for (const iframe of iframes) {
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        if (!doc) continue;
        const frameLinks = [...doc.querySelectorAll('a[href]')].filter(el => {
          try { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; } catch(e) { return false; }
        });
        for (const a of frameLinks) {
          const href = (a.getAttribute('href') || '').toLowerCase();
          const txt = (a.innerText || a.getAttribute('aria-label') || a.title || '').trim();
          let score = 0;
          if (CAREER_HREF.test(href)) score += 4;
          if (_isCareerText(txt)) score += 3;
          if (txt.length > 0 && txt.length < 40) score += 1;
          const badHref = /(newsletter|subscribe|investor|press|media|contact|about|privacy|terms|cookie|legal|sitemap)/i;
          if (badHref.test(href) && score < 5) score = 0;
          if (score > 0) {
            const dup = candidates.some(c => c.el === a);
            if (!dup) candidates.push({el: a, score, reason: 'iframe_link', href: a.getAttribute('href')});
          }
        }
      } catch(e) {} // cross-origin iframe
    }
  } catch(e) {}

  // === PASS 4: Scan TOUS les éléments visibles dans body pour texte carrière ===
  // (catch-all pour les sites avec des structures DOM exotiques)
  // v5.1: toujours exécuté (pas seulement si candidates.length===0) avec score=1
  try {
    const allVis = [...document.querySelectorAll('a, button, [role=button], [onclick], [class*=link i], [class*=item i], li, span')].filter(_vis);
    for (const el of allVis) {
      const txt = (el.innerText || el.getAttribute('aria-label') || el.title || '').trim();
      if (!txt || txt.length > 80) continue;
      if (_isCareerText(txt)) {
        const clickable = _findClickableAncestor(el, 5);
        const dup = candidates.some(c => c.el === clickable);
        if (!dup) {
          const href = clickable.getAttribute ? (clickable.getAttribute('href') || '') : '';
          const badHref = /(newsletter|subscribe|investor|press|media|contact|about|privacy|terms|cookie|legal|sitemap)/i;
          if (badHref.test(href)) continue;
          candidates.push({el: clickable, score: 1, reason: 'body_text', href: href});
        }
      }
    }
  } catch(e) {}

  // === TRI : par score décroissant, puis par longueur de texte croissant (préfère court = précis) ===
  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    const ta = ((a.el.innerText || '').trim()).length;
    const tb = ((b.el.innerText || '').trim()).length;
    return ta - tb;
  });

  // === Marquer le meilleur candidat ===
  document.querySelectorAll('[data-wn-dcareer]').forEach(e => e.removeAttribute('data-wn-dcareer'));
  if (candidates.length > 0) {
    const best = candidates[0];
    best.el.setAttribute('data-wn-dcareer', '1');
    try { best.el.scrollIntoView({block: 'center'}); } catch(e) {}
    return {
      found: true,
      label: (best.el.innerText || best.el.value || best.el.getAttribute('aria-label') || '').trim().slice(0, 60),
      href: best.href || '',
      score: best.score,
      reason: best.reason,
      total_candidates: candidates.length,
      // fournir les 5 meilleurs pour debug
      top5: candidates.slice(0, 5).map(c => ({
        label: (c.el.innerText || c.el.value || '').trim().slice(0, 40),
        score: c.score,
        reason: c.reason,
        tag: c.el.tagName,
      })),
    };
  }
  return {found: false, total_candidates: 0};
})()
"""


def goto_careers(page: Any) -> dict[str, Any]:
    """Depuis la home corporate, atteint la section Carrières / Nous rejoindre / Careers / Join us (FR/EN/DE/NL, shadow DOM, data-attributes, JS-only links).

    Utilise un scan DOM profond multi-passes. Retour {clicked, label, kind, reason,
    href, top5}.
    """
    # ── Primary: deep career scan (4-pass comprehensive DOM search) ──
    try:
        r = page.evaluate(_DEEP_CAREER_SCAN_JS)
    except Exception:
        r = None

    # If deep scan found nothing, fall back to pick_js("careers")
    if not r or not r.get("found"):
        try:
            r = page.evaluate(pick_js("careers"))
        except Exception:
            return {"clicked": False, "reason": "scan_error"}

    if not r or not r.get("found"):
        # v5.1: fallback sitemap.xml si aucun lien carrière trouvé
        sitemap_results = fetch_sitemap_careers(page)
        if sitemap_results:
            best_sm = sitemap_results[0]
            try:
                page.goto(best_sm["url"], timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3500)
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                kind = analyze(page).get("kind", "other")
                return {
                    "clicked": True,
                    "label": best_sm.get("label", ""),
                    "kind": kind,
                    "reason": "sitemap_fallback",
                    "href": best_sm["url"],
                    "is_js_only": False,
                    "top5": [],
                }
            except Exception:
                pass
        return {
            "clicked": False,
            "reason": "no_career_links",
            "top5": r.get("top5", []) if r else [],
        }

    label = r.get("label", "")
    href = r.get("href", "")
    is_js_only = not href or href.startswith("#") or href.startswith("javascript:")

    # ── Click: try multiple strategies ──
    clicked = False
    # Strategy 1: Playwright native click via data attribute
    if not clicked:
        try:
            page.locator('[data-wn-dcareer="1"]').first.click(timeout=4000)
            page.wait_for_timeout(3500)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            clicked = True
        except Exception:
            pass
    # Strategy 2: JS click via evaluate (bypasses Playwright actionability checks)
    if not clicked:
        try:
            page.evaluate(
                """const el = document.querySelector('[data-wn-dcareer="1"]'); if(el) { el.click(); return true; } return false;"""
            )
            page.wait_for_timeout(3500)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            clicked = True
        except Exception:
            pass
    # Strategy 3: For JS-only links (no href), dispatch MouseEvent
    if not clicked and is_js_only:
        try:
            page.evaluate("""
              const el = document.querySelector('[data-wn-dcareer="1"]');
              if (el) {
                el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                return true;
              }
              return false;
            """)
            page.wait_for_timeout(3500)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            clicked = True
        except Exception:
            pass
    # Strategy 4: If element has no href but has parent <a>, click parent
    if not clicked:
        try:
            page.evaluate("""
              const el = document.querySelector('[data-wn-dcareer="1"]');
              if (el) {
                const parent = el.closest('a[href]');
                if (parent) { parent.click(); return true; }
              }
              return false;
            """)
            page.wait_for_timeout(3500)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            clicked = True
        except Exception:
            pass
    # Strategy 5: navigate directly to href if available
    if not clicked and href and not is_js_only:
        try:
            # resolve relative URLs
            base = page.evaluate("() => window.location.origin")
            full_url = (
                href
                if href.startswith("http")
                else (base + (href if href.startswith("/") else "/" + href))
            )
            page.goto(full_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clicked = True
        except Exception:
            pass

    if not clicked:
        return {
            "clicked": False,
            "label": label,
            "reason": "click_failed_5_strategies",
            "href": href,
            "is_js_only": is_js_only,
        }

    kind = analyze(page).get("kind", "other")
    return {
        "clicked": True,
        "label": label,
        "kind": kind,
        "reason": r.get("reason", ""),
        "href": href,
        "is_js_only": is_js_only,
        "top5": r.get("top5", []),
    }


# ── CANDIDATE AUTH on careers page ────────────────────────────────────────
# Scanne TOUS les liens (y compris header/footer, shadow DOM) sur la page
# carrière pour trouver le vrai login/register CANDIDAT (pas newsletter).
# Les vrais logins candidats sont souvent dans le header de la page carrière.
_CAREERS_AUTH_JS = r"""
(() => {
  const _deep=(root,acc)=>{
    root.querySelectorAll('a[href],button,[role=button],input[type=button],input[type=submit],[onclick],summary').forEach(e=>acc.push(e));
    root.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) _deep(e.shadowRoot,acc); });
    return acc;
  };
  // Mots-clés qui sentent le vrai compte candidat (pas newsletter)
  const CANDIDATE = /(candidate?( portal| login| sign| account| profile| zone| space| area)|talent (community|network|pool|pipeline|profile|portal)|career (portal|login|sign|account|profile|centre|center)|applicant (login|portal|sign|account)|job (alerts?|agent)|my (profile|account|candidat)|espace (candidat|personnel|recrutement|carri[eè]re)|mon (compte|espace|profil)|(log ?in|sign ?in) (candidate?|applicant|talent|career)|(candidate?|talent|applicant|career) (log ?in|sign ?in|sign ?up|register|portal)|existing (candidate?|applicant|user)|returning (candidate?|applicant|user)|already (a |registered )?(candidate?|applicant|user|member))/i;
  // Mots-clés génériques login/register — OK si dans un contexte candidat (header, nav, pas footer)
  const GENERIC_LOGIN = /(log ?in|sign ?in|se connecter|connexion|identifiez-vous|access my|my account|mon compte|sign ?up|register|s'?inscrire|cr[eé]er (un |mon )?compte|create account|join (us|now|today)|apply|postuler|candidat|rejoignez)/i;
  // v5.1: LOGIN_STRICT = uniquement login/signup pur, pas apply/postuler/rejoignez
  const LOGIN_STRICT = /(log ?in|sign ?in|se connecter|connexion|identifiez-vous|access my|my account|mon compte|sign ?up|register|s'?inscrire|cr[eé]er (un |mon )?compte|create account|espace (candidat|personnel|recrutement)|mon espace|d[eé]j[aà] (un |inscrit|membre)|already (have|a |registered)|returning (user|candidate))/i;
  // Ce qui sent la newsletter ou le contenu marketing (à exclure)
  const NEWSLETTER = /(newsletter|subscribe|s['\u2019]?abonner|mailing|alert|notification|investor|press|media|contact us|nous contacter|rss|feed|blog|actualit[eé]s|news)/i;
  // Éléments de nav/header (contexte privilégié pour auth candidat)
  // v5.1: lien standalone hors header/footer explicite = header implicite (ex: lien "Espace candidat" en haut à droite)
  const _isHeaderContext = el => {
    let n = el;
    while (n) {
      const tag = (n.tagName||'').toLowerCase();
      const cls = (n.className||'').toLowerCase();
      const id = (n.id||'').toLowerCase();
      if (tag === 'header' || /header|navbar|top-bar|nav(igation)?(-bar|-top|-main)?/.test(cls+' '+id)) return true;
      if (tag === 'footer' || /footer/.test(cls+' '+id)) return false;
      if (tag === 'body') return true;  // v5.1: lien dans <body> sans header/footer = implicite header (zone neutre)
      if (tag === 'main' || /content|main|body/.test(cls+' '+id)) return true;  // v5.1: zone neutre aussi
      n = n.parentElement;
    }
    return true;  // v5.1: fallback = header implicite
  };
  const els = _deep(document,[]).filter(el=>{
    const r=el.getBoundingClientRect();
    return r.width>0 && r.height>0;
  });
  let best = null, bestScore = -1;
  for (const el of els) {
    const t = (el.innerText||el.value||el.getAttribute('aria-label')||el.getAttribute('title')||'').trim();
    if (!t || t.length > 80) continue;
    if (NEWSLETTER.test(t)) continue;  // hors newsletter
    const href = (el.getAttribute('href')||'').toLowerCase();
    // Exclure les liens qui pointent clairement ailleurs
    if (/(investor|press|media|news|blog|contact|about|privacy|terms|cookie|legal)/.test(href) && !CANDIDATE.test(t)) continue;
    let score = 0;
    if (CANDIDATE.test(t)) score += 5;  // fort signal : c'est un portail candidat
    if (GENERIC_LOGIN.test(t)) score += 2;
    if (_isHeaderContext(el)) score += 3;  // header = bon contexte (pas footer)
    // Bonus href qui contient des mots candidat
    if (/(career|talent|candidate?|job|applicant|recruit)/.test(href)) score += 2;
    // Bonus : bouton ou input submit
    if (el.tagName === 'BUTTON' || el.type === 'submit') score += 1;
    // Bonus : lien avec texte court (plus probablement un bouton nav)
    if (t.length < 30) score += 0.5;
    if (score > bestScore) { bestScore = score; best = el; }
  }
  document.querySelectorAll('[data-wn-cauth]').forEach(e=>e.removeAttribute('data-wn-cauth'));
  if (best && bestScore >= 5) {
    best.setAttribute('data-wn-cauth','1');
    best.scrollIntoView({block:'center'});
    return {found:true, label:(best.innerText||best.value||'').trim().slice(0,60), score:bestScore, url:best.href||''};
  }
  // Fallback moins strict : premier lien login/signup STRICT dans le header
  if (!best || bestScore < 4) {
    for (const el of els) {
      const t = (el.innerText||el.value||'').trim();
      if (!t || t.length > 50 || NEWSLETTER.test(t)) continue;
      if (LOGIN_STRICT.test(t) && _isHeaderContext(el) && !/(newsletter|subscribe|investor)/.test((el.getAttribute('href')||'').toLowerCase())) {
        best = el; bestScore = 1; break;
      }
    }
  }
  if (best) {
    best.setAttribute('data-wn-cauth','1');
    best.scrollIntoView({block:'center'});
    return {found:true, label:(best.innerText||best.value||'').trim().slice(0,60), score:bestScore, url:best.href||'', fallback:bestScore<4};
  }
  return {found:false};
})()
"""


# ── FALLBACK SITEMAP.XML : dernier recours quand aucun lien carrière trouvé ──
def fetch_sitemap_careers(page: Any, base_url: str = "") -> list[Any]:
    """Récupère /sitemap.xml et en extrait les URLs contenant des patterns carrière.

    Retour liste de {url, label, score}. À utiliser quand goto_careers() échoue
    (no_career_links).
    """
    import re as _re
    from urllib.parse import urlparse

    CAREER_URL_RX = _re.compile(
        r"/(career|carri[eè]re|job|emplo|recrut|talent|stellen|karriere|beruf|vacanc|vacature|opening|position|work|apply|join)",
        _re.IGNORECASE,
    )
    results = []
    sitemap_urls = []
    if base_url:
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
    else:
        try:
            origin = page.evaluate("() => window.location.origin")
        except Exception:
            origin = ""
    if origin:
        sitemap_urls = [
            f"{origin}/sitemap.xml",
            f"{origin}/sitemap_index.xml",
            f"{origin}/wp-sitemap.xml",
        ]
    for sitemap_url in sitemap_urls:
        try:
            import urllib.request
            import xml.etree.ElementTree as ET

            req = urllib.request.Request(sitemap_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            # Try XML parse
            try:
                root = ET.fromstring(data)
                ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                urls = root.findall(".//ns:loc", ns) or root.findall(
                    ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                )
                for loc in urls:
                    url_text = (loc.text or "").strip()
                    if url_text and CAREER_URL_RX.search(url_text):
                        # Extraire label du dernier segment
                        path = urlparse(url_text).path.rstrip("/")
                        label = path.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")
                        results.append(
                            {"url": url_text, "label": label, "score": 2, "source": "sitemap"}
                        )
            except Exception:
                # Fallback: regex brut sur le XML
                for match in _re.finditer(
                    r"<loc>([^<]+)</loc>", data.decode("utf-8", errors="ignore")
                ):
                    url_text = match.group(1).strip()
                    if CAREER_URL_RX.search(url_text):
                        path = urlparse(url_text).path.rstrip("/")
                        label = path.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")
                        results.append(
                            {"url": url_text, "label": label, "score": 2, "source": "sitemap_regex"}
                        )
            if results:
                break
        except Exception:
            continue
    return results


def drill_to_offer(page: Any, role_hint: str = "", job_rx: str = "") -> dict[str, Any]:
    """Page carrière = liste d'offres, pas d'offre précise.

    Clique le lien d'offre qui matche le mieux le rôle visé (sinon le 1er). `job_rx` =
    pattern liens spécifique à l'ATS (via detect_ats). Retour {clicked, label, n}.
    """
    try:
        r = page.evaluate(_drill_js(role_hint, job_rx))
    except Exception:
        return {"clicked": False}
    if not r or not r.get("found"):
        return {"clicked": False}
    try:
        page.locator('[data-wn-drill="1"]').first.click(timeout=4000)
        page.wait_for_timeout(2000)
        return {"clicked": True, "label": r.get("label", ""), "n": r.get("n", 0)}
    except Exception:
        return {"clicked": False, "label": r.get("label", "")}


# ── RECHERCHE D'OFFRE UNIFIÉE : reconnait l'ATS -> cherche -> entre dans l'offre ─
def find_offer(page: Any, role_hint: str = "", max_tries: int = 3) -> Any:
    """Point d'entrée UNIQUE pour atteindre une offre sur un site carrière.

    1) detect_ats (Workday/iCIMS/TalentSoft/… + pattern liens & champ recherche) 2) si
    déjà sur form/CTA -> ok 3) search_careers (tape le rôle) -> re-analyse 4)
    drill_to_offer avec le pattern liens de l'ATS -> re-analyse LOOP : si pas atteint,
    _unstick (cookies/scroll/wait/hover/reload) + réessaie. Retour {reached, kind, ats,
    via, tries}.
    """
    TARGET = ("apply_form", "apply_cta", "register", "login")
    # laisse le JS rendre les offres (cartes React/Vue) avant d'analyser
    try:
        page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:
        try:
            page.wait_for_timeout(2000)
        except Exception:
            pass
    ats = detect_ats(page)
    last = {}
    for attempt in range(max(1, max_tries)):
        info = analyze(page)
        if info.get("kind") in TARGET:
            return {
                "reached": True,
                "kind": info["kind"],
                "ats": ats.get("name"),
                "via": "direct" if attempt == 0 else "retry",
                "tries": attempt + 1,
            }
        via = []
        # 1) recherche par mot-clé (champ recherche d'offres)
        sc = search_careers(page, role_hint)
        if sc.get("searched"):
            via.append("search")
            info = analyze(page)
            if info.get("kind") in TARGET:
                return {
                    "reached": True,
                    "kind": info["kind"],
                    "ats": ats.get("name"),
                    "via": "+".join(via),
                    "tries": attempt + 1,
                }
        # 2) entrer dans une offre de la liste (pattern ATS si connu, sinon générique)
        dr = drill_to_offer(page, role_hint, ats.get("jobLinkRx", ""))
        if not dr.get("clicked") and ats.get("name") != "generic":
            dr = drill_to_offer(page, role_hint, "")  # fallback pattern générique
        if dr.get("clicked"):
            via.append("drill")
            dismiss_cookies(page)
            info = analyze(page)
        # 3) perdu (0 offre, rien cliqué) → saute vers la section Carrières puis re-tente
        if (
            not via
            and info.get("kind") in ("other", "newsletter_form")
            and info.get("nOffers", 0) < 3
        ):
            gc = goto_careers(page)
            if gc.get("clicked"):
                via.append("careers")
                dismiss_cookies(page)
                ats = detect_ats(page)  # l'ATS peut changer après le saut
                info = analyze(page)
                if info.get("kind") in TARGET:
                    return {
                        "reached": True,
                        "kind": info["kind"],
                        "ats": ats.get("name"),
                        "via": "+".join(via),
                        "tries": attempt + 1,
                    }
                sc2 = search_careers(page, role_hint)
                if sc2.get("searched"):
                    via.append("search")
                dr2 = drill_to_offer(page, role_hint, ats.get("jobLinkRx", ""))
                if dr2.get("clicked"):
                    via.append("drill")
                    dismiss_cookies(page)
                info = analyze(page)
        last = {
            "reached": info.get("kind") in TARGET,
            "kind": info.get("kind"),
            "ats": ats.get("name"),
            "via": "+".join(via) or "none",
            "label": dr.get("label", ""),
            "tries": attempt + 1,
        }
        if last["reached"]:
            return last
        _unstick(page, attempt)  # déblocage avant le prochain essai
    return last


# Annuaires et agregateurs : jamais le site d'une societe.
_ANNUAIRES = (
    "annuaire-entreprises",
    "societe.com",
    "pappers",
    "verif.com",
    "infogreffe",
    "manageo",
    "kompass",
    "bilansgratuits",
    "linkedin.com",
    "wikipedia.org",
    "glassdoor",
    "indeed.com",
)


def homepage_fallback(
    page: Any, entreprise: str, role: str = "", homepage: str | None = None
) -> dict[str, Any]:
    """PIPELINE DE BASE quand l'URL d'offre est morte : nom entreprise → site officiel (cache homepages.json, sinon résolution enrich_homepages : slug+validation+web) → section Carrières → offre.

    Retour {ok, homepage, careers, kind, via, note}.
    """
    import json as _json

    hp = homepage
    if not hp:  # 1) cache
        try:
            hp = _json.loads(
                (_racine.scripts() / "homepages.json").read_text(encoding="utf-8")
            ).get(entreprise)
        except Exception:
            hp = None
    if not hp:  # 2) résolution à la volée (devine domaine + valide HTTP)
        try:
            from jobhunter.programmes.enrich_homepages import resolve as _resolve

            hp = _resolve(entreprise)
            if isinstance(hp, tuple):  # resolve() retourne (nom, url)
                hp = hp[1]
            # Un ANNUAIRE n'est pas le site de la societe. La recherche y
            # atterrit quand le nom ne resout pas, et le cacher enverrait
            # ensuite le runner au mauvais endroit — durablement, puisque le
            # cache fait foi. Mesure : « Entreprise Inconnue XYZ 999 » avait
            # ainsi ete cachee vers annuaire-entreprises.data.gouv.fr.
            if hp and any(a in hp.lower() for a in _ANNUAIRES):
                hp = None
            if hp:  # persiste dans le cache pour la prochaine fois
                try:
                    _hp_f = _racine.scripts() / "homepages.json"
                    c = _json.loads(_hp_f.read_text(encoding="utf-8"))
                    c[entreprise] = hp
                    # Atomique : ce cache est relu par d'autres programmes, et
                    # un write_text interrompu le laissait tronque — donc
                    # illisible, donc reconstruit de zero au scan suivant.
                    importlib.import_module("jobhunter.programmes.jutil").jwrite(_hp_f, c)
                except Exception:
                    pass
        except Exception:
            hp = None
    if not hp:
        return {"ok": False, "note": "no_homepage"}
    g = _navigateur.robust_goto(page, hp, tries=2)
    if not g.get("ok"):
        return {"ok": False, "note": "homepage_goto_fail", "homepage": hp}
    dismiss_cookies(page)
    gc = retry(page, lambda: goto_careers(page), lambda x: x.get("clicked"), 3)
    if gc.get("clicked"):
        dismiss_cookies(page)
    fo = find_offer(page, role, max_tries=2)
    good = (
        fo.get("reached")
        or gc.get("clicked")
        or fo.get("kind") in ("offer_list", "apply_cta", "apply_form", "register", "login")
    )
    return {
        "ok": bool(good),
        "homepage": hp,
        "careers": bool(gc.get("clicked")),
        "kind": fo.get("kind"),
        "via": fo.get("via"),
        "note": "fallback",
    }
