"""Etapes intermediaires : boutons en deux temps, portails, menus, nouvelles tentatives.

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6)."""

from jobhunter.navigation.page import dismiss_cookies

# ── Wizbii 2-step : clic "Continuer avec email" avant que le form n'apparaisse ──
_WIZBII_EMAIL_BTN_JS = r"""
() => {
  const _deep=(root,acc)=>{root.querySelectorAll('a,button,[role=button],input[type=button],input[type=submit],[onclick]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
  const RE=/(continuer avec (votre |l'?)?email|continue with email|sign in with email|use email|se connecter avec (votre |l'?)?e?-?mail|log in with email)/i;
  const els=_deep(document,[]).filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0;});
  let best=null;
  for(const el of els){
    const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    if(t&&t.length<80&&RE.test(t)){ best=el; break; }
  }
  document.querySelectorAll('[data-wn-wizbii]').forEach(e=>e.removeAttribute('data-wn-wizbii'));
  if(best){ best.setAttribute('data-wn-wizbii','1'); best.scrollIntoView({block:'center'}); return {found:true,label:(best.innerText||'').trim().slice(0,50)}; }
  return {found:false};
}
"""


# ── Meeschaert 2-step : clic "Candidature spontanée"/"Postuler"/"Nous rejoindre" ──
_MEESCHAERT_REVEAL_JS = r"""
() => {
  const _deep=(root,acc)=>{root.querySelectorAll('a,button,[role=button],input[type=button],input[type=submit],div[onclick],div[class*="btn" i],div[class*="cta" i]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
  const RE=/(candidature spontan[eé]e|d[eé]poser (votre |ma |une )?candidature|postuler|nous rejoindre|rejoignez[ -]nous|rejoindre l'[eé]quipe|je postule|je candidate|envoyer (votre |ma )?candidature)/i;
  const els=_deep(document,[]).filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0;});
  let best=null;
  for(const el of els){
    const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    if(t&&t.length<120&&RE.test(t)){ best=el; break; }
  }
  document.querySelectorAll('[data-wn-meeschaert]').forEach(e=>e.removeAttribute('data-wn-meeschaert'));
  if(best){ best.setAttribute('data-wn-meeschaert','1'); best.scrollIntoView({block:'center'}); return {found:true,label:(best.innerText||'').trim().slice(0,50)}; }
  return {found:false};
}
"""


# ── Meeschaert connexion popin : force-show hidden login modal ──
# ANALYZE_JS détecte hasEmail=True + nPwd=1 mais 0 input visible car le
# formulaire login est caché dans #popin-moneypitch-form (display:none).
# Le bouton #btn-customer-area (déclencheur JS) est absent de la page
# recrutement — on force donc l'affichage directement.
_MEESCHAERT_CONNEXION_JS = r"""
(P) => {
  const popin = document.getElementById('popin-moneypitch-form');
  if (!popin) return {found: false, reason: 'popin not in DOM'};

  // 1. Force reveal the modal
  popin.style.display = 'block';

  // 2. Fill login (name="login")
  const loginInput = popin.querySelector('input[name="login"]');
  if (loginInput) {
    loginInput.focus();
    loginInput.value = P.email;
    loginInput.dispatchEvent(new Event('input', {bubbles: true}));
    loginInput.dispatchEvent(new Event('change', {bubbles: true}));
    loginInput.dispatchEvent(new Event('blur', {bubbles: true}));
  }

  // 3. Fill password (name="password")
  const pwdInput = popin.querySelector('input[name="password"]');
  if (pwdInput) {
    pwdInput.focus();
    pwdInput.value = P.password;
    pwdInput.dispatchEvent(new Event('input', {bubbles: true}));
    pwdInput.dispatchEvent(new Event('change', {bubbles: true}));
    pwdInput.dispatchEvent(new Event('blur', {bubbles: true}));
  }

  // 4. Find and click the Connexion submit button
  const btn = popin.querySelector('.popin-moneypitch-form_btn-connexion, button[type="submit"]');
  const filled = !!(loginInput && loginInput.value);
  const hasPwd = !!(pwdInput && pwdInput.value);

  if (btn) {
    // Mark button for Playwright locator
    btn.setAttribute('data-wn-meeschaert-connexion', '1');
    return {found: true, filled: filled && hasPwd, submitted: false, btn_available: true};
  }

  return {found: true, filled: filled && hasPwd, submitted: false, reason: 'no submit button found'};
}
"""


# ── Portail UBS / multi-liens login : détecter page portail → cliquer lien login ──
_PORTAL_LOGIN_JS = r"""
() => {
  const RE=/(log ?in|sign ?in|se connecter|connexion|identifiez-vous|access|espace (candidat|recrutement|personnel)|my account|mon compte|portal|existing user|compte existant)/i;
  const NOT=/(create|cr[eé]er|register|sign ?up|inscr|nouveau|new (user|account)|forgot|oubli)/i;
  const links=[...document.querySelectorAll('a[href]')].filter(a=>{
    const t=(a.innerText||a.getAttribute('aria-label')||'').trim();
    const r=a.getBoundingClientRect();
    return r.width>0&&r.height>0&&RE.test(t)&&!NOT.test(t)&&t.length<60;
  });
  document.querySelectorAll('[data-wn-portal]').forEach(e=>e.removeAttribute('data-wn-portal'));
  if(links.length>=1){
    links[0].setAttribute('data-wn-portal','1');
    links[0].scrollIntoView({block:'center'});
    return {found:true,label:(links[0].innerText||'').trim().slice(0,50),n:links.length};
  }
  return {found:false,n:links.length};
}
"""


def click_portal_login(page):
    """Page portail (UBS, etc.) : liste de liens vers différents espaces login.
    Clique le premier lien de connexion pertinent. Retour True si cliqué."""
    try:
        r = page.evaluate(_PORTAL_LOGIN_JS)
        if r and r.get("found"):
            page.locator('[data-wn-portal="1"]').first.click(timeout=4000)
            page.wait_for_timeout(2000)
            return True
    except Exception:
        pass
    return False


# Marque les déclencheurs de menu (aria-haspopup, caret, items de nav) pour hover.
_HOVERTRIG_JS = r"""
() => {
  const vh = window.innerHeight || 800;
  const trig=[...document.querySelectorAll('[aria-haspopup],[aria-expanded=false],nav a,nav button,.menu,.dropdown,[class*=menu i]>a,[class*=dropdown i]')]
    .filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0&&r.top<vh+400;});
  document.querySelectorAll('[data-wn-hov]').forEach(e=>e.removeAttribute('data-wn-hov'));
  trig.slice(0,8).forEach((e,i)=>e.setAttribute('data-wn-hov',i));
  return trig.length;
}
"""


# ── HAMBURGER MENU EXPANSION : clique ☰/menu icon avant de scanner ──
# v5.1: les sites responsive cachent la nav derrière une icône hamburger.
# Le headless browser (1366×768) reçoit souvent le layout mobile.
_HAMBURGER_JS = r"""
() => {
  const _vis = el => { try { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.width < 100 && r.height < 100; } catch(e) { return false; } };
  const HAMBURGER_SEL = [
    '[aria-label*="menu" i]', '[aria-label*="Menu" i]', '[aria-label*="navigation" i]',
    '[class*=hamburger i]', '[class*=burger i]', '[class*=toggle i]',
    '[class*=mobile-menu i]', '[class*=menu-icon i]', '[class*=nav-icon i]',
    '[class*=menu-trigger i]', '[class*=nav-toggle i]', '[class*=open-menu i]',
    'button[class*=menu i]', 'button[class*=nav i]',
    '.navbar-toggle', '.navbar-toggler',
    '[data-testid*="menu" i]', '[data-testid*="hamburger" i]',
    '[data-action*="menu" i]', '[data-action*="toggle" i]',
  ];
  // Strat 1: sélecteurs spécifiques
  for (const sel of HAMBURGER_SEL) {
    const el = document.querySelector(sel);
    if (el && _vis(el)) {
      el.setAttribute('data-wn-hamburger', '1');
      el.scrollIntoView({block: 'center'});
      return {found: true, selector: sel, label: (el.getAttribute('aria-label') || el.innerText || '').trim().slice(0, 50)};
    }
  }
  // Strat 2: chercher un bouton avec uniquement des icônes (☰, ≡, ▸) comme innerText
  const allBtns = [...document.querySelectorAll('button, [role=button], a')].filter(_vis);
  for (const btn of allBtns) {
    const t = (btn.innerText || '').trim();
    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
    // Texte = juste une icône hamburger ou aria-label menu
    if ((/^[☰≡☱☲☳☴☵☶☷▸▾▸▸]+$/.test(t) && t.length <= 5) || /menu|navigation|ouvrir|open/i.test(aria)) {
      btn.setAttribute('data-wn-hamburger', '1');
      btn.scrollIntoView({block: 'center'});
      return {found: true, selector: 'unicode-icon', label: t || aria.slice(0, 50)};
    }
  }
  return {found: false};
}
"""


def expand_hamburger_menu(page):
    """Détecte et clique l'icône hamburger (☰) pour révéler la navigation
    cachée. À appeler AVANT tout scan de liens carrière/login.
    Retour {expanded, label, selector}."""
    try:
        r = page.evaluate(_HAMBURGER_JS)
    except Exception:
        return {"expanded": False, "reason": "evaluate_error"}
    if not r or not r.get("found"):
        return {"expanded": False, "reason": "no_hamburger_found"}
    # Click strategies
    clicked = False
    try:
        page.locator('[data-wn-hamburger="1"]').first.click(timeout=3000)
        page.wait_for_timeout(800)
        clicked = True
    except Exception:
        pass
    if not clicked:
        try:
            page.evaluate(
                """const el=document.querySelector('[data-wn-hamburger=\"1\"]'); if(el){el.click();el.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"""
            )
            page.wait_for_timeout(800)
            clicked = True
        except Exception:
            pass
    return {"expanded": clicked, "label": r.get("label", ""), "selector": r.get("selector", "")}


def hover_menus(page):
    """Survole les déclencheurs de menu (dérouler panneau/sous-menu) pour révéler
    le bon bouton caché. Retour nb de triggers survolés."""
    try:
        n = page.evaluate(_HOVERTRIG_JS)
    except Exception:
        return 0
    hovered = 0
    for i in range(min(int(n or 0), 8)):
        try:
            page.locator(f'[data-wn-hov="{i}"]').first.hover(timeout=1500)
            page.wait_for_timeout(400)
            hovered += 1
        except Exception:
            pass
    return hovered


def _unstick(page, i):
    """Action de « déblocage » escaladante entre 2 essais d'un finder qui a raté :
    cookies → scroll → attente → hover sous-menus → reload. Idempotent, silencieux."""
    try:
        if i <= 0:
            dismiss_cookies(page)
        elif i == 1:
            page.mouse.wheel(0, 900)
            page.wait_for_timeout(700)
        elif i == 2:
            page.wait_for_timeout(2200)
        elif i == 3:
            hover_menus(page)
        else:
            try:
                page.reload(timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(1800)
                dismiss_cookies(page)
            except Exception:
                pass
    except Exception:
        pass


def retry(page, fn, is_ok, max_tries=3):
    """Relance `fn()` tant que `is_ok(result)` est faux, en appliquant _unstick
    (cookies/scroll/wait/hover/reload) entre chaque essai raté. Retour dernier result.
    Usage: retry(page, lambda: goto_careers(page), lambda r: r.get('clicked'))."""
    result = None
    for i in range(max(1, max_tries)):
        try:
            result = fn()
        except Exception:
            result = None
        if result and is_ok(result):
            if i:  # marque le nb d'essais si dispo
                try:
                    result["tries"] = i + 1
                except Exception:
                    pass
            return result
        _unstick(page, i)
    return result if result is not None else {}
