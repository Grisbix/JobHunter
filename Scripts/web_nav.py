#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web_nav.py — Navigation web intelligente (Playwright).
Fournit des SCRIPTS JS (évaluables par page.evaluate) :
  - COOKIE_JS       : ferme la bannière cookies, REFUS prioritaire
  - ANALYZE_JS      : analyse RÉELLE de la page -> {kind, signals}
  - pick_js(task)   : clic contextuel selon la tâche

⚠️ Captcha / anti-bot = DÉTECTÉS pour PAUSER (humain), jamais contournés.

Patchright prioritaire (anti-bot bypass), fallback Playwright.
"""

# ── COOKIES ──
COOKIE_JS = r"""
(() => {
  const REJECT = /(tout refuser|refuser tout|refuser|reject all|reject|decline|deny|non merci|continuer sans accepter|necessaires? uniquement|only necessary|essential(s)? only|strictement necessaires?|je refuse|weiger|ablehnen|nur (erforderlich|notwendig)|parametrer|personnaliser|gerer mes choix|configurer|manage (choices|preferences)|customi[sz]e|sans accepter|poursuivre sans)/i;
  const ACCEPT = /(tout accepter|accepter( tout| & fermer)?|accept all|accept( &? close| all cookies)?|j'?accepte|autoriser|allow all|alle akzeptieren|zustimmen|ok, ?tout accepter|ok pour moi|got it|d'accord)/i;
  const _deep=(root,acc)=>{root.querySelectorAll('a,button,[role=button],input[type=button],input[type=submit]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
  const clickable = () => _deep(document,[]).filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0;});
  // v5.1: sélecteurs CMP avec shadow DOM + exclure les éléments de navigation
  const _cmpFind = (sels) => {
    const all = _deep(document, []);
    for (const el of all) {
      for (const sel of sels) {
        if (el.matches && el.matches(sel)) {
          const cls = (el.className || '').toLowerCase();
          const id = (el.id || '').toLowerCase();
          // Ne pas cliquer si l'élément ressemble à de la navigation
          if (/nav|menu|header|navbar/.test(cls+' '+id)) continue;
          return el;
        }
      }
    }
    return null;
  };
  const CMP = ['#onetrust-reject-all-handler','.onetrust-close-btn-handler','#didomi-notice-disagree-button','button[aria-label*="refus" i]','#axeptio_btn_dismiss','.axeptio_btn_dismiss','#tarteaucitronAllDenied2','.tarteaucitronDeny','button#cmpwelcomebtnno','.sp_choice_type_REJECT_ALL','button[data-testid="uc-deny-all-button"]','#CybotCookiebotDialogBodyButtonDecline','#CybotCookiebotDialogBodyLevelButtonLevelOptinDeclineAll','#CybotCookiebotDialogBodyButtonReject','.cmplz-deny','.cc-deny','.cookie-decline','.js-cookie-refuse','#cookie-refuse','button[data-cy="reject-all"]','button[data-role="reject"]','#hs-eu-decline-button','.qc-cmp2-summary-buttons button[mode="secondary"]','#truste-consent-required','button[aria-label*="reject" i]','button[aria-label*="decline" i]','[data-testid="cookie-banner-reject"]','#gdpr-banner-decline','.evidon-banner-declinebutton'];
  const cmpEl = _cmpFind(CMP);
  if (cmpEl) { cmpEl.click(); return {done:'cmp-reject',sel:'cmp'}; }
  for (const el of clickable()){ const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim(); if(t&&t.length<40&&REJECT.test(t)){ el.click(); return {done:'reject',t}; } }
  // v5.1: banner query exclut les nav/menu
  const banner = document.querySelector('[id*="cookie" i]:not([class*=nav i]):not([class*=menu i]),[class*="cookie" i]:not([class*=nav i]):not([class*=menu i]),[id*="consent" i],[class*="consent" i],[aria-label*="cookie" i],[class*="axeptio" i],#axeptio_overlay,.didomi-popup-container');
  if (banner){ for (const el of clickable()){ const t=(el.innerText||el.value||'').trim(); if(t&&t.length<40&&ACCEPT.test(t)){ el.click(); return {done:'accept-fallback',t}; } } }
  return {done:'none'};
})()
"""

ANALYZE_JS = r"""
(() => {
  const txt = (document.body?document.body.innerText:'').slice(0,20000).toLowerCase();
  const has = (...r) => r.some(x => (x instanceof RegExp ? x.test(txt) : txt.includes(x)));
  const q = s => document.querySelector(s);
  const qa = s => [...document.querySelectorAll(s)];
  const nPwd = qa('input[type=password]').length;
  const nFile = qa('input[type=file]').length;
  const _emailLike = 'input[type=email], input[name*=email i], input[id*=email i], input[name*=\"Identifiant\" i], input[name*=\"Nouveau\" i], input[name*=\"txtNouveau\" i], input[name*=\"login\" i], input[name*=\"username\" i], input[name*=\"user\" i], input[placeholder*=\"email\" i], input[placeholder*=\"mail\" i], input[name*=\"courriel\" i], input[name*=\"e-mail\" i], input[name*=\"member\" i], input[name*=\"candidate\" i], input[autocomplete=\"email\"], input[autocomplete=\"username\"]';
  const _isNewsletterCtx = el => {
    const selfA = ((el.name||'')+(el.id||'')+(el.className||'')).toLowerCase();
    if (/newsletter|subscribe/.test(selfA)) return true;
    let n = el;
    while (n) {
      if (n.tagName === 'FOOTER') return true;
      if (n.tagName === 'FORM') {
        const fA = ((n.id||'')+(n.className||'')+(n.getAttribute('action')||'')+(n.getAttribute('name')||'')).toLowerCase();
        if (/newsletter|subscribe|s['\\u2019]?abonner/.test(fA)) return true;
        if (!n.querySelector('input[type=password]')) {
          const fT = (n.innerText||'').toLowerCase().slice(0,500);
          if (/newsletter|subscribe|s['\\u2019]?abonner/.test(fT)) return true;
        }
        break;
      }
      n = n.parentElement;
    }
    return false;
  };
  const hasEmail = qa(_emailLike).filter(e => !_isNewsletterCtx(e)).length > 0;
  // compte les liens d'offres (href OU texte=titre de poste) — pour ne pas confondre
  // une page carrière pleine d'offres avec un simple form newsletter
  const _JOBH=/\/(jobs?|offre|emploi|career|poste|vacan|position|stelle|opening)s?\//i;
  const _JOBT=/(analyste?|analyst|charg[eé]|manager|consultant|ing[eé]nieur|engineer|responsable|assistant|stagiaire|alternan|auditeur|business|data|risk|esg|quant)/i;
  const nOffers = qa('a[href]').filter(a=>{const t=(a.innerText||'').trim();return _JOBH.test(a.href)||(t.length>6&&t.length<90&&_JOBT.test(t));}).length;
  // v5: formulaire "newsletter-only" — SEULEMENT si email seul + contexte alerte
  // + AUCUNE offre et pas de signal apply/register (sinon = vraie page carrière)
  const _singleEmailNoPwd = hasEmail && nPwd===0 && nFile===0;
  // + jamais si signal postuler/inscription présent (page offre != newsletter)
  const _newsletterForm = _singleEmailNoPwd && nOffers < 3
    && has(/(alerte|alert|notification|recevoir|stay.*touch|keep.*posted|newsletter|subscribe|s['\\u2019]?abonner)/)
    && !has(/(postuler|candidater|deposer (votre|ma) candidature|apply now|apply for|votre candidature|cr[eé][eé]z? (un |mon )?compte|s'?inscri(re|vez)|sign ?up|create (an )?account)/);
  // v5: inputs non-standards BPCE / Engagement Jeunes
  const _bpceEmail = qa('input[name*=\\"_mail\\" i],input[name*=\\"EmailField\\" i],input[name*=\\"courriel\\" i],input[name*=\\"identifiant\\" i],input[name*=\\"login-email\\" i],input[name*=\\"txtEmail\\" i],input[name*=\\"email_address\\" i],input[name*=\\"user_email\\" i],input[id*=\\"identifiant\\" i],input[id*=\\"login\\" i],input[id*=\\"email\\" i],input[autocomplete=\\"email\\"],input[autocomplete=\\"username\\"]').filter(e => !_isNewsletterCtx(e)).length > 0;
  const _bpcePwd = qa('input[type=password],input[name*=\\"motdepasse\\" i],input[name*=\\"mot_de_passe\\" i],input[name*=\\"mdp\\" i],input[id*=\\"password\\" i],input[id*=\\"mdp\\" i]').length;
  // CAPTCHA = un defi qui BLOQUE, pas un simple script charge. Presque tous les
  // sites d'entreprise embarquent reCAPTCHA pour leur formulaire de contact :
  // le detecter suffisait a declarer « bloque » des sites parfaitement lisibles
  // (mirova.com, candriam.com, cressidf.org — tous en HTTP 200 avec leur contenu).
  // On exige donc que le widget soit VISIBLE et que la page soit pauvre en texte,
  // ou qu'un message de defi explicite s'affiche.
  const _capEls = [...document.querySelectorAll('iframe[src*="recaptcha"],iframe[src*="hcaptcha"],iframe[src*="turnstile"],.g-recaptcha,.h-captcha,#cf-challenge-running')];
  const _capVisible = _capEls.some(e => { const r = e.getBoundingClientRect(); return r.width > 60 && r.height > 40; });
  const _txtLen = (document.body ? (document.body.innerText || '') : '').trim().length;
  // Une page de defi n'a quasiment pas de contenu ; une page normale en a beaucoup.
  const _defiExplicite = has(/(je ne suis pas un robot|i'?m not a robot|verifi(er|cation) que vous etes (humain|une personne)|verifying you are human|checking your browser|un instant.*verifions|attention required)/);
  const captcha = _defiExplicite || (_capVisible && _txtLen < 1200);
  const rateLimited = has(/(429|too many requests|trop de requetes|rate ?limit|slow down|ralentissez)/);
  const blocked = rateLimited || has(/(access denied|acces refuse|forbidden|403|unusual traffic|trafic inhabituel|has been blocked|checking your browser|verifying you are human|cloudflare|please enable (js|cookies)|nice try.*(congrats|figuring out|land(ed)? on this)|bot detect|automated (access|traffic|request)|suspicious activity)/);
  // page morte / offre fermée (404 ATS, offre pourvue) → runner marque l'offre morte
  const dead = nOffers===0 && has(/(404 error|page (not found|introuvable)|offre (n'?existe plus|pourvue|expir[eé]e|clotur[eé]e|a [eé]t[eé] pourvue)|no longer (available|accepting)|(posting|job).{0,30}(closed|been removed)|posting you'?re looking for|cette offre n'?est plus)/);
  const registerTxt = has(/(cr[eé][eé]z? (un |mon )?compte|nouveau compte|ouvrir un compte|s'?inscri(re|vez)|inscri(ption|vez)|s'?enregistr(er|ez)|register|registrier|sign ?up|signup|create (an )?account|konto erstellen|cr[eé][eé]z? mon (espace|profil)|nouvel utilisateur|new user|reg[íi]strate|crea(re)? (un )?account)/);
  const loginTxt = has(/(se connecter|connexion|identifiez-vous|log ?in|sign ?in|already have an account|deja un compte|anmeld(en|ung)|einloggen|accedi|iniciar sesi[oó]n)/);
  const applyTxt = has(/(postuler|candidater|deposer (votre|ma) candidature|apply now|apply for|votre candidature)/);
  const confirmPwd = qa('input[type=password]').length >= 2 || !!q('input[name*=confirm i],input[id*=confirm i],input[placeholder*=confirm i]');
  let kind='other';
  if (captcha) kind='captcha';
  else if (blocked) kind='blocked';
  else if (dead) kind='dead';
  else if (_newsletterForm) kind='newsletter_form';
  else if (nFile>0 && (applyTxt||hasEmail||_bpceEmail)) kind='apply_form';
  else if ((nPwd>=1||_bpcePwd>=1) && loginTxt) kind='login';
  else if ((nPwd>=1||_bpcePwd>=1) && (registerTxt||confirmPwd)) kind='register';
  else if (applyTxt && (hasEmail||_bpceEmail||nFile>0)) kind='apply_form';
  else if (nOffers>=5) kind='offer_list';
  else if (registerTxt) kind='register';
  else if (loginTxt && (hasEmail||_bpceEmail||nPwd>=1||_bpcePwd>=1)) kind='login';
  else if (applyTxt) kind='apply_cta';
  return {kind, captcha, blocked, dead, rateLimited, nPwd, nFile, hasEmail, confirmPwd, nOffers, registerTxt, loginTxt, applyTxt, newsletterForm:_newsletterForm, bpceEmail:_bpceEmail, bpcePwd:_bpcePwd, url:location.href};
})()
"""

# Section "carrières / nous rejoindre" à atteindre depuis la home avant login/offre (FR/EN/DE/NL/IT/ES).
# v5.1 : mots-clés étendus — graduate, apprenticeship, RH, our people, culture, etc.
# v5.1 : negative lookahead global SUPPRIMÉ (faux négatifs). Exclusions faites dans _DEEP_CAREER_SCAN_JS.
CAREERS_RX = (
    r"(carri[eè]res?|nous rejoindre|rejoign(ez|dre)( ?-? ?nous| l'?[eé]quipe)?"
    r"|recrutement|recrute(ons?|ments?)?|recruiting|nos offres|offres? d'?emploi"
    r"|espace (candidat|recrutement|carri[eè]re)"
    r"|travailler (avec|chez|pour) nous|travailler ensemble|talents?|emplois?"
    r"|careers?|join (us|our team|the team)|work (with|for|at) us|working (here|at)"
    r"|jobs?|vacan(cy|cies)|openings?|opportunit(y|ies)|we'?re hiring|life at"
    r"|karriere|stellen(angebote)?|mitarbeiter werden|beruf"
    r"|talent community|talent network|talent acquisition|candidate portal|career portal"
    r"|job alerts?|talent (pool|pipeline)"
    r"|candidature spontan[eé]e|spontaneous application|unsolicited application"
    r"|open positions?|job opportunities?|current openings?"
    r"|werken bij|vacatures?|lavora con noi|posizioni aperte|trabaja con nosotros"
    r"|emplois? et carri[eè]res?|d[eé]couvr(ez|ir) nos (offres|m[eé]tiers|postes)"
    r"|postuler|candidater|apply|d[eé]poser (votre |ma |une )?candidature"
    r"|nos m[eé]tiers|notre [eé]quipe|rejoins?-nous"
    r"|graduate|graduates?|early careers?|early talent|students?|apprentice|internship"
    r"|apprentissage|alternance|stag(es?|iaires?)"
    r"|ressources humaines|RH|human resources?|people (and|&) culture"
    r"|our (people|team|culture)|why work|come (work|join) (with )?us"
    r"|make (a difference|an impact)|grow with us|employer branding|employeur"
    r"|bist du dabei|werde teil|aventure humaine"
    r"|job offers?|job openings?|find (a |your )?job|search jobs?|view (all |our )?jobs?)"
)

# JS partagé : collecte tous les cliquables EN PERÇANT le shadow DOM (web components).
_DEEP_CLICKABLE = r"""
  const _deep=(root,acc)=>{
    root.querySelectorAll('a,button,[role=button],input[type=button],input[type=submit],[onclick],summary,div[class*="apply" i],div[class*="cta" i]').forEach(e=>acc.push(e));
    root.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) _deep(e.shadowRoot,acc); });
    return acc;
  };
  const _vis=el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
"""


def pick_js(task: str) -> str:
    RX = {
        "register": r"(cr[eé][eé]?z? (un |mon |votre )?compte|nouveau compte|ouvrir un compte|s'?inscri(re|vez)|inscri(ption|vez)|s'?enregistr(er|ez)|enregistr(er|ez)|register|registrieren|konto erstellen|sign ?up|signup|create (an |your )?account|(cr[eé]e\w*|ouvrir) (un |mon |votre )?espace( candidat)?|cr[eé][eé]?z? mon profil|je m'?inscris|rejoign(ez|dre)|join us|devenir membre|pas (encore )?de compte|no account|don'?t have an account|nouvel utilisateur|new user)",
        "login": r"(se connecter|connexion|log ?in|sign ?in|j'?ai deja un compte|identifiez-vous|connectez-vous|acceder a mon compte|mon (espace|compte)( candidat| personnel)?|espace (candidat|personnel|client)|anmeld(en|ung)|einloggen|accedi|iniciar sesi[oó]n)",
        "apply": r"(postuler|postulez|candidater|je postule|je candidate|deposer (une |votre |ma )?candidature|postuler a (cette |l'?)offre|repondre a (cette |l'?)offre|rejoindre (l'?equipe|notre equipe)|apply now|apply for( this)?( job| role| position)?|apply|i'?m interested|commencer|demarrer|get started|start|continuer ma candidature)",
        "careers": CAREERS_RX,
    }
    NEVER = r"(envoyer ma candidature|soumettre ma candidature|submit application|confirmer et envoyer|valider (et )?envoyer|envoyer definitivement)"
    want = RX.get(task, RX["apply"])
    # CAREERS_RX chevauche register (join us/rejoindre) ET apply (postuler/candidater/apply).
    # Pas de pénalité croisée avec careers : sinon boutons Postuler/Inscription pénalisés.
    skip = {task}
    if task == "careers":
        skip.update(("register", "apply", "login"))
    if task in ("register", "apply", "login"):
        skip.add("careers")
    others = "|".join(v for k, v in RX.items() if k not in skip)
    return r"""
    (() => {
      %s
      const WANT=/%s/i, OTHER=/%s/i, NEVER=/%s/i;
      const els=_deep(document,[]).filter(_vis);
      let best=null,score=-1;
      const cls=el=>{const c=el.className;return ((c&&c.toString?c.toString():'')+' '+(el.id||'')).toLowerCase();};
      for(const el of els){
        const t=(el.innerText||el.value||el.getAttribute('aria-label')||el.getAttribute('title')||'').trim();
        if(!t||t.length>60) continue;
        const tn=t.normalize('NFD').replace(/[̀-ͯ]/g,'');  // sans accents
        if(NEVER.test(tn)) continue;
        let s=0;
        if(WANT.test(tn)) s+=3;
        if(OTHER.test(tn)) s-=2;
        if(/\b(create|creer|s'?inscrire|postuler|apply|connexion|connecter)\b/i.test(tn)) s+=1;
        if(el.tagName==='BUTTON'||el.type==='submit') s+=0.5;
        // signal class/id : bouton d'action réel (ATS : btn-primary, apply-button, cta…)
        if(/(btn|button|cta)[-_ ]?(primary|apply|postul|submit|main|action)|apply|postul|candidat|inscri|register|signup|s-btn/.test(cls(el))) s+=1;
        // anti-bruit : footer/mentions légales, bannière cookie = pas la CTA
        try{ if(el.closest('footer,[class*=footer i]')) s-=1.5; }catch(e){}
        try{ if(el.closest('[class*=cookie i],[class*=consent i],[id*=cookie i],[id*=consent i]')) s-=3; }catch(e){}
        // proéminence : visible sans scroll + gros bouton
        const rr=el.getBoundingClientRect();
        if(rr.top>=0 && rr.top<(window.innerHeight||900)) s+=0.4;
        if(rr.width*rr.height>4000) s+=0.3;
        if(s>score){score=s;best=el;}
      }
      document.querySelectorAll('[data-wn-pick]').forEach(e=>e.removeAttribute('data-wn-pick'));
      if(best&&score>=3){ best.setAttribute('data-wn-pick','1'); best.scrollIntoView({block:'center'}); return {found:true,label:(best.innerText||best.value||'').trim().slice(0,50),score}; }
      return {found:false};
    })()
    """ % (_DEEP_CLICKABLE, want, others, NEVER)


def dismiss_cookies(page):
    try:
        return page.evaluate(COOKIE_JS)
    except Exception:
        return {"done": "err"}


_OVERLAY_JS = r"""
() => {
  let closed = [];
  // 1) widgets de chat qui interceptent les clics (Intercom/Drift/Zendesk/Crisp/HubSpot/Tawk)
  const CHAT = ['#intercom-container','.intercom-launcher','#drift-widget','#hubspot-messages-iframe-container',
    '.crisp-client','#crisp-chatbox','iframe[title*="chat" i]','iframe[id*="chat" i]','.zEWidget-launcher',
    '#launcher','.tawk-min-container','iframe[src*="tawk.to"]','[class*="chat-widget" i]','[id*="livechat" i]'];
  for (const sel of CHAT) {
    document.querySelectorAll(sel).forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width>0 && r.height>0) { el.style.setProperty('display','none','important'); el.style.setProperty('pointer-events','none','important'); closed.push('chat'); }
    });
  }
  // 2) bouton de fermeture de modales génériques (pas les cookies, pas les forms d'offre)
  const CLOSE = /^(×|✕|✖|x|close|fermer|schließen|cerrar|no thanks|non merci|plus tard|maybe later|skip|passer|ignorer)$/i;
  const modals = [...document.querySelectorAll('[role=dialog],[aria-modal="true"],.modal,.popup,.overlay,[class*="modal" i],[class*="popup" i]')];
  for (const m of modals) {
    const r = m.getBoundingClientRect();
    if (r.width<80 || r.height<80) continue;
    const mt = (m.innerText||'').toLowerCase();
    if (/cookie|consent|postul|apply|candidat|inscri|connex|login|sign/.test(mt)) continue; // garde cookies/offre/auth
    const btn = [...m.querySelectorAll('button,a,[role=button],span')].find(b => {
      const t=(b.innerText||b.getAttribute('aria-label')||'').trim(); return t && t.length<16 && CLOSE.test(t);
    });
    if (btn) { try { btn.click(); closed.push('modal'); } catch(e){} }
  }
  return {closed: closed.length, kinds: [...new Set(closed)]};
}
"""


def dismiss_overlays(page):
    """Ferme les widgets chat (Intercom/Drift/Zendesk/Crisp…) et modales non-essentielles
    qui interceptent les clics. NE touche PAS aux bannières cookies/formulaires d'offre/auth."""
    try:
        return page.evaluate(_OVERLAY_JS)
    except Exception:
        return {"closed": 0, "kinds": []}


def analyze(page):
    try:
        return page.evaluate(ANALYZE_JS)
    except Exception:
        return {"kind": "other", "captcha": False, "blocked": False}


# #6 Wizbii/Meeschaert : form register détecté mais inputs rendus tard (React/Vue).
_COUNT_VISIBLE_INPUTS_JS = r"""
() => {
  const _deep=(root,acc)=>{root.querySelectorAll('input,textarea').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
  const bad=['hidden','submit','button','checkbox','radio'];
  return _deep(document,[]).filter(el=>{
    const t=(el.type||'').toLowerCase(); if(bad.includes(t))return false;
    const r=el.getBoundingClientRect(); return r.width>30&&r.height>0;
  }).length;
}
"""


def wait_for_form(page, min_inputs=1, timeout_ms=7000, timeout=None):
    """Attend que les champs de saisie apparaissent (formulaire chargé
    dynamiquement). Retour nb d'inputs visibles (0 = jamais rendu)."""
    if timeout is not None:
        timeout_ms = timeout
    import time as _t

    deadline = _t.time() + timeout_ms / 1000.0
    n = 0
    while _t.time() < deadline:
        try:
            n = page.evaluate(_COUNT_VISIBLE_INPUTS_JS)
        except Exception:
            n = 0
        if n >= min_inputs:
            return n
        try:
            page.wait_for_timeout(500)
        except Exception:
            break
    return n


def click_for_task(page, task):
    try:
        r = page.evaluate(pick_js(task))
        if r and r.get("found"):
            page.locator('[data-wn-pick="1"]').first.click(timeout=4000)
            page.wait_for_timeout(1500)
            return r.get("label")
    except Exception:
        pass
    return None


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


def smart_step(page, task, target_kinds=("apply_form", "register", "login"), max_tries=6):
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


def search_careers(page, query):
    """Tape le rôle dans le champ recherche d'offres de la page carrière puis
    soumet (Enter). Fait surgir l'offre quand la liste ne la montre pas.
    Retour {searched, ph}."""
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


def goto_careers(page):
    """Depuis la home corporate, atteint la section Carrières / Nous rejoindre /
    Careers / Join us (FR/EN/DE/NL, shadow DOM, data-attributes, JS-only links).
    Utilise un scan DOM profond multi-passes.
    Retour {clicked, label, kind, reason, href, top5}."""
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
def fetch_sitemap_careers(page, base_url: str = "") -> list:
    """Récupère /sitemap.xml et en extrait les URLs contenant des patterns
    carrière. Retour liste de {url, label, score}.
    À utiliser quand goto_careers() échoue (no_career_links)."""
    from urllib.parse import urlparse
    import re as _re

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
            import urllib.request, xml.etree.ElementTree as ET

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


def drill_to_offer(page, role_hint="", job_rx=""):
    """Page carrière = liste d'offres, pas d'offre précise. Clique le lien d'offre
    qui matche le mieux le rôle visé (sinon le 1er). `job_rx` = pattern liens
    spécifique à l'ATS (via detect_ats). Retour {clicked, label, n}."""
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
def find_offer(page, role_hint="", max_tries=3):
    """Point d'entrée UNIQUE pour atteindre une offre sur un site carrière.
    1) detect_ats (Workday/iCIMS/TalentSoft/… + pattern liens & champ recherche)
    2) si déjà sur form/CTA -> ok
    3) search_careers (tape le rôle) -> re-analyse
    4) drill_to_offer avec le pattern liens de l'ATS -> re-analyse
    LOOP : si pas atteint, _unstick (cookies/scroll/wait/hover/reload) + réessaie.
    Retour {reached, kind, ats, via, tries}."""
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


# ── #3 WIZARD MULTI-ÉCRANS (Workday/iCIMS : apply = 4-6 pages) ────────────────
# Marque le bouton "étape suivante" (PAS le submit final). Refuse envoyer/soumettre.
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


def run_wizard(page, fill_fn=None, max_screens=6):
    """#3 Parcourt un formulaire de candidature MULTI-ÉCRANS (Workday/iCIMS/SmartRecruiters).
    Boucle : remplit l'écran (fill_fn) + coche CGU + clique "Suivant/Continuer"
    (jamais le submit final) → écran suivant → répète. S'arrête quand seul le submit
    final reste (à toi de cliquer Envoyer) ou plus de progression.
    fill_fn(page)->int : callback de remplissage (autofill du runner). Retour
    {screens, filled_total, stopped}."""
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
        # seul le submit final présent -> stop (l'humain clique Envoyer)
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
        # pas de progression (URL + DOM identiques) -> stop
        try:
            if cur and page.url == cur and cur in seen_urls:
                return {"screens": screens, "filled_total": filled_total, "stopped": "no_progress"}
            seen_urls.append(cur)
        except Exception:
            pass
    return {"screens": screens, "filled_total": filled_total, "stopped": "max_screens"}


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


def vision_pick(page, task, model=None, host="http://localhost:11434"):
    """Fallback vision : screenshot -> Ollama lit le bon bouton -> clic DOM.
    Auto-détecte le modèle vision disponible (qwen2.5vl, llava, etc.).
    Silencieux si Ollama absent/modèle absent. Retour {clicked, label, note}."""
    import base64, json, urllib.request, urllib.error

    # Auto-détection du modèle vision disponible
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
            host + "/api/generate", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
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


def _detect_vision_model(host="http://localhost:11434") -> str | None:
    """Détecte le premier modèle vision disponible via l'API Ollama.
    Ordre de préférence : qwen2.5vl → llava → minicpm-v → bakllava."""
    import json, urllib.request, urllib.error

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
        req = urllib.request.Request(host + "/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        models = [m.get("name", "") for m in data.get("models", [])]
        for kw in VISION_KEYWORDS:
            for m in models:
                if kw in m.lower():
                    return m.split(":")[0] if ":" in m else m
        # Fallback: tout modèle avec "vl" ou "vision" dans le nom
        for m in models:
            ml = m.lower()
            if "vl" in ml or "vision" in ml:
                return m.split(":")[0] if ":" in m else m
    except Exception:
        pass
    return None  # rien trouvé → fallback manuel


def _detect_text_model(host="http://localhost:11434"):
    """Détecte un modèle texte Ollama pour le raisonnement (mistral/llama/qwen/phi)."""
    import json, urllib.request

    PREF = ["qwen2.5", "llama3", "llama-3", "mistral", "mixtral", "phi", "gemma", "qwen"]
    try:
        req = urllib.request.Request(host + "/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            models = [m.get("name", "") for m in json.loads(resp.read().decode()).get("models", [])]
        for kw in PREF:
            for m in models:
                if kw in m.lower() and "vl" not in m.lower() and "vision" not in m.lower():
                    return m
        return models[0] if models else None
    except Exception:
        return None


# ── #1 AGENT LLM (plan-act) : lit la page, décide l'action, exécute, recommence ─
# Raisonnement humain-équiv sur DOM (+ vision optionnelle). Ollama local, gratuit.
# GARDE-FOUS : ne clique jamais le submit final, ne résout jamais de captcha.
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


def llm_agent(page, goal, max_steps=8, model=None, host="http://localhost:11434", profile=None):
    """#1 Agent plan-act : à chaque étape lit le DOM (digest), demande au LLM local
    (Ollama) l'action à faire pour atteindre `goal`, l'exécute, recommence.
    Actions : click / fill / scroll / done / stop. GARDE-FOUS : refuse submit final
    & captcha (renvoie stop). Dégrade proprement si Ollama absent.
    Retour {ok, steps, log, note}."""
    import json, urllib.request, re as _re

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
    log = []
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
                host + "/api/generate", data=body, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
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
            # garde-fou submit final
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


# ── LOGIN multi-étapes (SmartRecruiters email→continue→password + génériques) ──
_LOGIN_JS = r"""
(P) => {
  const norm=s=>(s||'').toLowerCase();
  const lab=el=>{let t='';if(el.id){const l=document.querySelector(`label[for="${el.id}"]`);if(l)t+=' '+l.textContent;}const p=el.closest('label');if(p)t+=' '+p.textContent;return t;};
  let email=0,pwd=0;
  for(const el of document.querySelectorAll('input')){
    const type=(el.type||'').toLowerCase();
    if(el.value&&el.value.trim())continue;
    const r=el.getBoundingClientRect(); if(r.width===0&&r.height===0)continue;
    const key=norm([el.name,el.id,el.placeholder,el.getAttribute('aria-label'),lab(el)].join(' '));
    if(type==='email'||/e-?mail|courriel|identifiant|username|login/.test(key)){ el.focus(); el.value=P.email; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); el.dispatchEvent(new Event('blur',{bubbles:true})); email++; }
    else if(type==='password'){ el.focus(); el.value=P.password; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); el.dispatchEvent(new Event('blur',{bubbles:true})); pwd++; }
  }
  // TalentSoft / ASP.NET fallback: explicit name selectors (Login/Password/MotDePasse)
  if(email===0){
    for(const sel of ['input[name=\"Login\" i]','input[name=\"login\"]','input[name=\"Identifiant\" i]','input[name=\"txtIdentifiant\" i]']){
      const el=document.querySelector(sel);
      if(el&&!el.value.trim()&&el.getBoundingClientRect().width>0){
        el.focus(); el.value=P.email;
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
        el.dispatchEvent(new Event('blur',{bubbles:true}));
        email++; break;
      }
    }
  }
  if(pwd===0){
    for(const sel of ['input[name=\"Password\" i]','input[name=\"password\"]','input[name=\"MotDePasse\" i]','input[name=\"txtPassword\" i]']){
      const el=document.querySelector(sel);
      if(el&&!el.value.trim()&&el.getBoundingClientRect().width>0){
        el.focus(); el.value=P.password;
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
        el.dispatchEvent(new Event('blur',{bubbles:true}));
        pwd++; break;
      }
    }
  }
  const NEXT=/(continuer|continue|suivant|next|se connecter|log ?in|sign ?in|valider|connexion)/i;
  const NOT=/(créer|creer|s'?inscrire|register|sign ?up|forgot|oublié)/i;
  document.querySelectorAll('[data-wn-next]').forEach(e=>e.removeAttribute('data-wn-next'));
  for(const el of document.querySelectorAll('button,input[type=submit],[role=button],a')){
    const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    const r=el.getBoundingClientRect();
    if(t&&t.length<40&&r.width>0&&NEXT.test(t)&&!NOT.test(t)){ el.setAttribute('data-wn-next','1'); return {email,pwd,btn:t}; }
  }
  return {email,pwd,btn:''};
}
"""

# #7 React : fill() ne déclenche pas toujours l'état -> requestSubmit() natif.
# Cible le form contenant un input email/password rempli. Retour bool.
_REQSUBMIT_JS = r"""
() => {
  const inp=[...document.querySelectorAll('input[type=email],input[type=password],input[name*=email i]')].find(e=>e.value&&e.value.trim());
  const form=inp?inp.closest('form'):document.querySelector('form');
  if(form && form.requestSubmit){ form.requestSubmit(); return true; }
  if(form){ form.submit(); return true; }
  return false;
}
"""


def react_submit(page):
    """Soumission native HTML (form.requestSubmit) quand le clic bouton est avalé
    par React/SPA. Retour True si un form a été soumis."""
    try:
        return bool(page.evaluate(_REQSUBMIT_JS))
    except Exception:
        return False


def login_flow(page, email, pwd, max_steps=3):
    """Login multi-étapes (SmartRecruiters : email→continue→password→login).
    Remplit les champs vides + clique continue/login à chaque étape.
    Fallback requestSubmit() si le clic ne fait pas avancer (React).
    Le mot de passe n'est JAMAIS tape : regle du projet, quel que soit pwd."""
    pwd = ""
    import json as _json

    steps = []
    for _ in range(max_steps):
        try:
            r = page.evaluate(f"({_LOGIN_JS})({_json.dumps({'email': email, 'password': pwd})})")
        except Exception:
            break
        steps.append(r)
        submitted_pwd = bool(r.get("pwd"))
        if r.get("btn"):
            url_before = None
            try:
                url_before = page.url
            except Exception:
                pass
            try:
                page.locator('[data-wn-next="1"]').first.click(timeout=4000)
                page.wait_for_timeout(2000)
            except Exception:
                break
            # clic avalé (URL + DOM inchangés) -> requestSubmit natif
            try:
                still = page.locator('[data-wn-next="1"]').count() > 0
                if still and page.url == url_before:
                    if react_submit(page):
                        r["reqsubmit"] = True
                        page.wait_for_timeout(2000)
            except Exception:
                pass
        if submitted_pwd:  # password soumis -> login envoyé, stop
            break
        if not r.get("email") and not r.get("btn"):
            break
    return {"steps": steps}


# ── BASCULE vers CRÉATION DE COMPTE (sign in -> sign up) ──────────────────────
# Sur portail carrière : la page montre souvent LOGIN par défaut. Si pas de compte,
# faut cliquer le toggle/onglet "Créer un compte / Pas de compte ? Inscrivez-vous".
_SWITCH_REG_JS = r"""
() => {
  const _deep=(root,acc)=>{root.querySelectorAll('a,button,[role=button],[role=tab],input[type=button]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
  const REG=/(cr[eé][eé]z? (un |mon )?compte|cr[eé]er (un |mon )?compte|ouvrir un compte|s'?inscri(re|vez)|inscri(ption|vez)|s'?enregistr(er|ez)|register|registrieren|konto erstellen|sign ?up|signup|create (an |your )?account|(cr[eé]e\w*|ouvrir) (un |mon |votre )?espace( candidat)?|espace candidat|cr[eé]er mon profil|je m'?inscris|rejoign|devenir membre|pas (encore )?de compte|no account|don'?t have an account|nouvel utilisateur|new user)/i;
  const NOT=/(se connecter|connexion|log ?in|sign ?in|forgot|oubli[eé]|mot de passe oubli|already have|d[eé]j[aà] un compte)/i;
  const NEVER=/(envoyer|soumettre|submit application|postuler)/i;
  const els=_deep(document,[]).filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0;});
  let best=null,score=-1;
  for(const el of els){
    const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    if(!t||t.length>90||NEVER.test(t)) continue;
    let s=0;
    if(REG.test(t)) s+=3;
    if(NOT.test(t) && !REG.test(t)) continue;   // pur bouton login -> skip
    if(el.getAttribute('role')==='tab'||el.tagName==='A') s+=0.5;
    if(t.length<25) s+=0.3;                       // libellé court = plus sûr (onglet)
    if(s>score){score=s;best=el;}
  }
  document.querySelectorAll('[data-wn-reg]').forEach(e=>e.removeAttribute('data-wn-reg'));
  if(best&&score>=3){ best.setAttribute('data-wn-reg','1'); best.scrollIntoView({block:'center'}); return {found:true,label:(best.innerText||best.value||'').trim().slice(0,60)}; }
  return {found:false};
}
"""


def switch_to_register(page):
    """Bascule d'un écran login vers l'écran création de compte (toggle/onglet).
    Retour {switched, label, kind}. kind = analyze après clic."""
    try:
        r = page.evaluate(_SWITCH_REG_JS)
    except Exception:
        return {"switched": False}
    if not r or not r.get("found"):
        return {"switched": False}
    try:
        page.locator('[data-wn-reg="1"]').first.click(timeout=4000)
        page.wait_for_timeout(1800)
    except Exception:
        return {"switched": False, "label": r.get("label", "")}
    kind = analyze(page).get("kind", "other")
    return {"switched": True, "label": r.get("label", ""), "kind": kind}


# ── UPLOAD robuste : matche CV vs Lettre par label, gère inputs cachés ────────
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

# ── AUTO-APPLY : remplissage automatique de formulaire de candidature ────────


def accept_consent(page):
    """Coche les cases de consentement OBLIGATOIRES (CGU, conditions, politique de confidentialité,
    traitement des données) nécessaires pour postuler. Ne coche PAS les opt-ins
    marketing (newsletter, offres commerciales)."""
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


# JS : reconnait la PLATEFORME/ATS (URL host + signatures DOM) et renvoie
# {name, jobLinkRx (regex liens d'offre), searchSel (champ recherche), note}.
_ATS_DETECT_JS = r"""
(() => {
  const u = location.href.toLowerCase();
  const host = location.hostname.toLowerCase();
  const H = document.documentElement.innerHTML.toLowerCase();
  const h = H.slice(0, 8000);
  const meta = [...document.querySelectorAll('meta[name],script[src],link[href]')]
    .map(e=>(e.getAttribute('src')||e.getAttribute('href')||e.content||'').toLowerCase()).join(' ');
  const sig = h + ' ' + meta;
  const has = (...ks) => ks.some(k => u.includes(k) || host.includes(k) || sig.includes(k));
  // [name, test, jobLinkRx, searchSel]
  const T = [
    ['workday',        () => has('myworkdayjobs.com','workday','wd1.myworkday','wd3.myworkday'), '/job/',            '[data-automation-id=keywordSearchInput],input[type=search]'],
    ['smartrecruiters',() => has('smartrecruiters.com','smartrecruiters'),                       '/jobs?/',          'input[name=keyword],input[type=search]'],
    ['greenhouse',     () => has('greenhouse.io','grnhse','boards.greenhouse'),                   '/jobs?/\\d+',      'input#search,input[type=search]'],
    ['lever',          () => has('lever.co','jobs.lever'),                                        '/[a-f0-9-]{20,}', 'input[type=search]'],
    ['talentsoft',     () => has('talent-soft.com','talentsoft','recrutement.bpce'),              '/offre-de-emploi|/candidature|frontoffice', 'input[type=search],input[name*=keyword i]'],
    ['teamtailor',     () => has('teamtailor.com','teamtailor'),                                  '/jobs?/',          'input[type=search]'],
    ['breezy',         () => has('breezy.hr'),                                                    '/p/[a-f0-9]',      'input[type=search]'],
    ['welcometojungle',() => has('welcometothejungle.com','wttj'),                                '/(jobs|companies).*/', 'input[type=search],input[name=query]'],
    ['icims',          () => has('icims.com','icims'),                                            '/jobs?/\\d+',      'input[id*=search i],input[type=search]'],
    ['taleo',          () => has('taleo.net','taleo'),                                            '/careersection|/job/', 'input[id*=keyword i],input[type=search]'],
    ['successfactors', () => has('successfactors','sapsf','career.sap','jobs.sap'),               '/job/\\d+|/careers?/', 'input[type=search],input[id*=keyword i]'],
    ['oraclecloud',    () => has('oraclecloud.com','/hcmui/','fa-ext.oraclecloud'),               '/job/\\d+',        'input[type=search],input[id*=keyword i]'],
    ['recruitee',      () => has('recruitee.com','recruitee'),                                    '/o/',              'input[type=search]'],
    ['workable',       () => has('workable.com','workable'),                                      '/j/[a-f0-9]',      'input[type=search],input[aria-label*=search i]'],
    ['flatchr',        () => has('flatchr.io','flatchr'),                                         '/vacancy/|/offre', 'input[type=search]'],
    ['softgarden',     () => has('softgarden'),                                                   '/job/|/vacancies', 'input[type=search]'],
    ['jobvite',        () => has('jobvite.com','jobvite'),                                        '/careers?/',       'input[type=search]'],
    ['digitalrecruiters',()=> has('digitalrecruiters.com'),                                       '/offre/|/job',     'input[type=search],input[name*=keyword i]'],
    ['beetween',       () => has('beetween.com','beetween'),                                      '/offre|/job',      'input[type=search]'],
    ['eightfold',      () => has('eightfold.ai','eightfold'),                                     '/careers?/|/position', 'input[type=search]'],
    ['avature',        () => has('avature.net','avature'),                                        '/careers?/|/job',  'input[type=search]'],
    ['phenom',         () => has('phenompeople','phenom'),                                        '/job/',            'input[type=search],input[id*=keyword i]'],
    ['ashby',          () => has('ashbyhq.com','ashby'),                                          '/[a-f0-9-]{20,}',  'input[type=search]'],
    ['personio',       () => has('personio.','jobs.personio'),                                    '/job/\\d+',        'input[type=search]'],
  ];
  let name='generic', jobLinkRx='/(jobs?|offre|emploi|career|poste|vacan|position|stelle|opening)s?/', searchSel='input[type=search],input[name*=search i],input[placeholder*=recherch i],input[placeholder*=search i]';
  for (const [n, test, rx, ss] of T) {
    try { if (test()) { name=n; jobLinkRx=rx; searchSel=ss; break; } } catch(e){}
  }
  return {name, jobLinkRx, searchSel};
})()
"""


def detect_ats(page):
    """Reconnait la plateforme/ATS du site d'entreprise (Workday, iCIMS, TalentSoft,
    SmartRecruiters, Greenhouse, Lever, Taleo, SuccessFactors, Teamtailor, Breezy,
    Recruitee, Workable, WTTJ, … + 'generic'). Retour {name, jobLinkRx, searchSel}."""
    try:
        r = page.evaluate(_ATS_DETECT_JS)
        return r or {"name": "generic"}
    except Exception:
        return {"name": "generic"}


# ── SEGMENTEUR DE PAGE : reconnait TOUTES les parties du site ──────────────────
# regions (header/nav/main/footer/aside/modales/iframes) + overlays (cookie/captcha/
# chat/newsletter) + chaque bouton classé par rôle + chaque form + offres + signaux.
_SEGMENT_JS = r"""
(() => {
  const N=s=>(s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
  const deep=(root,acc,sel)=>{try{root.querySelectorAll(sel).forEach(e=>acc.push(e));}catch(e){}root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)deep(e.shadowRoot,acc,sel);});return acc;};
  const vis=e=>{const r=e.getBoundingClientRect();return r.width>1&&r.height>1;};
  const box=e=>{const r=e.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)};};
  // rôles de boutons/liens
  const ROLES=[
    ['cookie',   /(tout accepter|tout refuser|accepter|refuser|reject|accept cookies|consent|ok pour moi|parametrer les cookies)/],
    ['login',    /(se connecter|connexion|log ?in|sign ?in|identifiez|acceder a mon compte|connectez)/],
    ['register', /(creer? (un |mon )?compte|s'?inscri|inscription|register|sign ?up|espace candidat|nouvel utilisateur|rejoign)/],
    ['apply',    /(postuler|postulez|candidater|deposer.*candidature|apply|je postule|repondre a.*offre)/],
    ['submit',   /(envoyer ma candidature|soumettre|submit application|confirmer et envoyer|valider et envoyer|finaliser.*candidature)/],
    ['careers',  /(carrieres?|nous rejoindre|recrutement|offres? d'?emploi|nos offres|careers?|join us|jobs?|talents?|travailler)/],
    ['search',   /(rechercher|search|filtrer|trouver)/],
    ['social',   /(linkedin|twitter|facebook|instagram|youtube|partager|share)/],
    ['menu',     /(menu|navigation|toggle|ouvrir le menu|burger)/],
    ['lang',     /^(fr|en|de|es|it|nl|français|english|deutsch|langue|language)$/],
  ];
  const roleOf=t=>{const n=N(t);for(const[r,rx]of ROLES){if(rx.test(n))return r;}return 'other';};
  // overlays
  const q=s=>{try{return document.querySelector(s);}catch(e){return null;}};
  const bodyTxt=N((document.body?document.body.innerText:'').slice(0,15000));
  const overlays={
    cookie: !!q('[id*=cookie i],[class*=cookie i],[id*=consent i],[class*=consent i],[class*=axeptio i],#onetrust-banner-sdk,#didomi-host'),
    captcha: !!q('iframe[src*=recaptcha],iframe[src*=hcaptcha],iframe[src*=turnstile],.g-recaptcha,.h-captcha,#cf-challenge-running') || /captcha|not a robot|je ne suis pas un robot/.test(bodyTxt),
    chat: !!q('[id*=chat i],[class*=chat i],[class*=intercom i],[class*=drift i],[class*=crisp i],[id*=livechat i]'),
    newsletter: /(newsletter|inscrivez-vous a|abonnez)/.test(bodyTxt),
    modal: !!q('[role=dialog],[class*=modal i][style*=block],[class*=popup i],[aria-modal=true]'),
  };
  // regions présentes
  const regions={
    header: !!q('header,[role=banner],[class*=header i]'),
    nav:    !!q('nav,[role=navigation],[class*=navbar i],[class*=menu i]'),
    main:   !!q('main,[role=main],#content,[class*=content i]'),
    aside:  !!q('aside,[role=complementary],[class*=sidebar i]'),
    footer: !!q('footer,[role=contentinfo],[class*=footer i]'),
    iframes: deep(document,[],'iframe').filter(vis).map(f=>({src:(f.src||'').slice(0,80),box:box(f)})).slice(0,8),
  };
  // boutons/liens classés (dans le viewport élargi)
  const btns=[]; let k=0;
  deep(document,[],'a,button,[role=button],input[type=submit],input[type=button],summary').filter(vis).slice(0,120).forEach(el=>{
    const t=(el.innerText||el.value||el.getAttribute('aria-label')||el.title||'').trim().slice(0,45);
    if(!t) return;
    const inFooter=!!el.closest('footer,[class*=footer i]');
    btns.push({i:k++, txt:t, role:roleOf(t), tag:el.tagName.toLowerCase(), footer:inFooter, box:box(el)});
  });
  // agrégat rôles
  const byRole={};
  for(const b of btns){byRole[b.role]=(byRole[b.role]||0)+1;}
  // formulaires + but
  const forms=deep(document,[],'form').filter(vis).slice(0,10).map((f,i)=>{
    const ins=[...f.querySelectorAll('input,textarea,select')];
    const nPwd=ins.filter(e=>(e.type||'')==='password').length;
    const nFile=ins.filter(e=>(e.type||'')==='file').length;
    const hasEmail=ins.some(e=>(e.type||'')==='email'||/mail|identifiant/.test(N(e.name+e.id+e.placeholder)));
    const ftxt=N(f.innerText.slice(0,400));
    let purpose='other';
    if(nFile>0) purpose='apply';
    else if(nPwd>=2||/confirm|creer|inscri|register/.test(ftxt)) purpose='register';
    else if(nPwd===1) purpose='login';
    else if(/recherch|search|mot-cle|poste/.test(ftxt)) purpose='search';
    else if(/newsletter|abonn/.test(ftxt)) purpose='newsletter';
    return {i, purpose, nInputs:ins.length, nPwd, nFile, hasEmail};
  });
  // offres (liens d'emploi) : href OU texte = titre de poste (cartes JS)
  const JOB=/\/(jobs?|offre|emploi|career|poste|vacan|position|stelle|opening)s?\//i;
  const JOBTXT=/(analyste?|analyst|charg[eé]|manager|consultant|d[eé]veloppeur|ing[eé]nieur|engineer|responsable|assistant|stagiaire|alternan|apprenti|auditeur|gestionnaire|business|data|risk|esg|quant)/i;
  const offers=deep(document,[],'a[href]').filter(a=>{if(!vis(a))return false;const t=(a.innerText||'').trim();return JOB.test(a.href)||(t.length>6&&t.length<90&&JOBTXT.test(t));}).length;
  return {
    url:location.href, title:document.title.slice(0,80),
    regions, overlays, byRole, buttons:btns.slice(0,60), forms, offers,
    signals:{nPwd:deep(document,[],'input[type=password]').length,
             nFile:deep(document,[],'input[type=file]').length,
             hasEmail:!!q('input[type=email],input[name*=email i]')}
  };
})()
"""


def segment_page(page):
    """RECONNAISSANCE COMPLÈTE : mappe toutes les parties de la page —
    régions (header/nav/main/footer/aside/iframes), overlays (cookie/captcha/chat/
    modal/newsletter), chaque bouton classé par rôle (cookie/login/register/apply/
    submit/careers/search/social/menu/lang), chaque formulaire + son but, nb d'offres,
    signaux (mdp/fichier/email). Retour dict complet (base des décisions nav)."""
    try:
        return page.evaluate(_SEGMENT_JS)
    except Exception as e:
        return {
            "error": type(e).__name__,
            "regions": {},
            "overlays": {},
            "byRole": {},
            "buttons": [],
            "forms": [],
        }


def plan_action(page, goal="apply"):
    """CERVEAU déterministe : lit la carte complète (segment_page) et renvoie la
    MEILLEURE action suivante — {action, role, reason, seg}. Actions :
    stop(captcha) / cookies / ready / drill / careers / click / auth / register / search / none.
    Gratuit, hors-ligne, sans LLM. Complète smart_step (qui exécute)."""
    s = segment_page(page)
    ov = s.get("overlays", {})
    if ov.get("captcha"):
        return {"action": "stop", "role": "captcha", "reason": "captcha — humain", "seg": s}
    if ov.get("cookie") and s.get("byRole", {}).get("cookie"):
        return {"action": "cookies", "role": "cookie", "reason": "bannière cookie", "seg": s}
    forms = s.get("forms", [])
    purposes = {f["purpose"] for f in forms}
    roles = s.get("byRole", {})
    if goal == "apply":
        if "apply" in purposes:
            return {
                "action": "ready",
                "role": "apply_form",
                "reason": "formulaire de candidature présent",
                "seg": s,
            }
        if s.get("offers", 0) >= 1:
            return {
                "action": "drill",
                "role": "offer_list",
                "reason": "%d offre(s) — entrer" % s["offers"],
                "seg": s,
            }
        if roles.get("apply"):
            return {"action": "click", "role": "apply", "reason": "bouton Postuler", "seg": s}
        if roles.get("search"):
            return {
                "action": "search",
                "role": "search",
                "reason": "champ recherche d'offres",
                "seg": s,
            }
        if roles.get("careers"):
            return {"action": "careers", "role": "careers", "reason": "lien Carrières", "seg": s}
        if "register" in purposes:
            return {
                "action": "register",
                "role": "register",
                "reason": "formulaire inscription",
                "seg": s,
            }
        if "login" in purposes:
            return {"action": "auth", "role": "login", "reason": "formulaire login", "seg": s}
    else:  # goal register/login
        if goal in purposes:
            return {
                "action": "ready",
                "role": goal + "_form",
                "reason": "formulaire %s présent" % goal,
                "seg": s,
            }
        if roles.get(goal):
            return {"action": "click", "role": goal, "reason": "bouton %s" % goal, "seg": s}
        if roles.get("careers"):
            return {"action": "careers", "role": "careers", "reason": "lien Carrières", "seg": s}
    return {"action": "none", "role": "other", "reason": "rien de concluant", "seg": s}


def describe_page(page):
    """Résumé lisible du segment (debug/log) : régions + overlays + rôles + forms."""
    s = segment_page(page)
    if s.get("error"):
        return "segment KO: %s" % s["error"]
    reg = [k for k, v in s.get("regions", {}).items() if v is True]
    ov = [k for k, v in s.get("overlays", {}).items() if v]
    roles = ", ".join(
        "%s×%d" % (k, v) for k, v in sorted(s.get("byRole", {}).items(), key=lambda x: -x[1])
    )
    forms = ", ".join("%s(%d champs)" % (f["purpose"], f["nInputs"]) for f in s.get("forms", []))
    return (
        "PAGE '%s'\n  régions: %s | iframes: %d\n  overlays: %s\n  boutons par rôle: %s\n  forms: %s\n  offres: %d"
        % (
            s.get("title", "")[:50],
            "+".join(reg) or "—",
            len(s.get("regions", {}).get("iframes", [])),
            "+".join(ov) or "aucun",
            roles or "—",
            forms or "aucun",
            s.get("offers", 0),
        )
    )


# JS : scanne TOUS les champs du formulaire (input, textarea, select) avec leur contexte
_SCAN_FORM_FIELDS_JS = r"""
(() => {
  const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const labelText = el => {
    let t = '';
    if (el.id){ const l = document.querySelector(`label[for="${el.id}"]`); if(l) t += ' ' + l.textContent; }
    const p = el.closest('label'); if(p) t += ' ' + p.textContent;
    // sibling text nodes
    const prev = el.previousElementSibling;
    if (prev && ['LABEL','SPAN','DIV'].includes(prev.tagName)) t += ' ' + prev.textContent;
    const next = el.nextElementSibling;
    if (next && ['LABEL','SPAN','DIV'].includes(next.tagName)) t += ' ' + next.textContent;
    // parent container text
    const parent = el.closest('.form-group,.field,.input-group,.form-field') || el.parentElement;
    if (parent) t += ' ' + (parent.textContent||'').slice(0,200);
    return t;
  };
  const bad = ['hidden','submit','button','image','reset','search'];
  const fields = [];
  // text inputs, email, tel, etc.
  [...document.querySelectorAll('input,textarea,select')].forEach((el,i) => {
    const t = (el.type||'').toLowerCase();
    if (bad.includes(t) && el.tagName !== 'SELECT') return;
    if (t === 'checkbox' || t === 'radio') return; // handled separately
    const ctx = norm([el.name,el.id,el.placeholder,el.getAttribute('aria-label'),labelText(el),el.type].join(' '));
    fields.push({
      idx: i, tag: el.tagName, type: t, ctx,
      name: el.name||'', id: el.id||'',
      placeholder: el.placeholder||'',
      currentValue: el.value||'',
      visible: el.offsetParent !== null,
      required: el.required || el.getAttribute('aria-required') === 'true' || false,
      options: el.tagName === 'SELECT' ? [...el.options].map(o => ({text: o.text, value: o.value, selected: o.selected})) : null
    });
    el.setAttribute('data-ao-idx', i);
  });
  // checkboxes & radios
  const checkboxes = [...document.querySelectorAll('input[type=checkbox],input[type=radio]')].map((el,i) => {
    const ctx = norm([el.name,el.id,el.value,el.getAttribute('aria-label'),labelText(el)].join(' '));
    el.setAttribute('data-ao-cb', i);
    return { idx: i, tag: el.tagName, type: el.type, ctx, name: el.name||'', id: el.id||'', value: el.value||'', checked: el.checked, visible: el.offsetParent !== null, required: el.required || false };
  });
  // file inputs
  const fileInputs = [...document.querySelectorAll('input[type=file]')].map((el,i) => {
    const ctx = norm([el.name,el.id,el.getAttribute('aria-label'),labelText(el)].join(' '));
    el.setAttribute('data-ao-file', i);
    return { idx: i, ctx, name: el.name||'', id: el.id||'', accept: el.accept||'', visible: el.offsetParent !== null };
  });
  // submit buttons
  const submits = [...document.querySelectorAll('button[type=submit],input[type=submit],button:not([type]),a[role=button],button[type]')].map((el,i) => {
    const t = (el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    if (!t || t.length > 60) return null;
    return { idx: i, text: t, tag: el.tagName, visible: el.offsetParent !== null };
  }).filter(Boolean);
  return { fields, checkboxes, fileInputs, submits, url: location.href, title: document.title };
})()
"""

_OPEN_RX = r"(postuler|postulez|candidater|je postule|je candidate|d[eé]poser (une |votre |ma )?candidature|apply now|apply for( this)?|apply|i'?m interested)"
_SUBMIT_RX = r"(envoyer ma candidature|soumettre|submit application|submit your application|confirmer et envoyer|valider (et )?envoyer|finaliser (ma |la )?candidature|envoyer definitivement)"


def try_open_form(page):
    """Clique un bouton 'Postuler/Apply' pour ouvrir le formulaire. JAMAIS un submit final.
    Retour label cliqué ou ''. (Défini dans web_nav pour apply_to_offer — était absent → NameError)."""
    js = r"""
    ([openRx, submitRx]) => {
      const o=new RegExp(openRx,'i'), s=new RegExp(submitRx,'i');
      const _deep=(root,acc)=>{root.querySelectorAll('a,button,[role=button],input[type=button],input[type=submit]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
      for(const el of _deep(document,[])){
        const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
        if(!t) continue;
        const tn=t.normalize('NFD').replace(/[̀-ͯ]/g,'');
        if(s.test(tn)) continue;
        if(o.test(tn)){ const r=el.getBoundingClientRect(); if(r.width>0&&r.height>0){ el.setAttribute('data-pw-apply','1'); return t.slice(0,50); } }
      }
      return '';
    }"""
    try:
        label = page.evaluate(js, [_OPEN_RX, _SUBMIT_RX])
        if label:
            page.locator('[data-pw-apply="1"]').first.click(timeout=4000)
            page.wait_for_timeout(2500)
            return label
    except Exception:
        pass
    return ""


def highlight_submit(page):
    """Surligne le bouton d'envoi final en ROUGE + scroll. Ne clique PAS (l'humain clique).
    Retour label ou ''. (Défini dans web_nav pour apply_to_offer — était absent → NameError)."""
    js = r"""
    (submitRx) => {
      const s=new RegExp(submitRx,'i');
      const _deep=(root,acc)=>{root.querySelectorAll('button,input[type=submit],a,[role=button]').forEach(e=>acc.push(e));root.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)_deep(e.shadowRoot,acc);});return acc;};
      for(const el of _deep(document,[])){
        const t=(el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
        if(t && s.test(t.normalize('NFD').replace(/[̀-ͯ]/g,''))){
          el.style.outline='4px solid red'; el.style.outlineOffset='2px';
          el.scrollIntoView({block:'center'}); return t.slice(0,50);
        }
      }
      return '';
    }"""
    try:
        return page.evaluate(js, _SUBMIT_RX)
    except Exception:
        return ""


def linkedin_ready(page):
    """LinkedIn : session connectée ? (aucun mdp tapé — on lit juste l'état).
    Retour True si nav globale connectée détectée, False si mur login/join."""
    js = r"""
    () => {
      // signaux CONNECTÉ : nav globale + avatar "Me"
      if (document.querySelector('.global-nav__me, img.global-nav__me-photo, a[href*="/feed/"]')) return 'in';
      // signaux DÉCONNECTÉ : bandeau/join/sign-in modal
      const t=(document.body.innerText||'').toLowerCase();
      if (document.querySelector('a[href*="/login"], .authwall, .join-form, [data-tracking-control-name*="guest"]')) return 'out';
      if (/s'inscrire|sign in|join now|s'identifier/.test(t) && !document.querySelector('.jobs-apply-button')) return 'out';
      return 'unknown';
    }"""
    try:
        return page.evaluate(js)
    except Exception:
        return "unknown"


# Bouton envoi FINAL LinkedIn — JAMAIS cliqué par le bot (l'humain clique)
_LI_SUBMIT_RX = (
    r"(envoyer la candidature|soumettre la candidature|submit application|envoyer ma candidature)"
)
# Boutons d'avancement dans le wizard Easy Apply — cliqués auto
_LI_NEXT_RX = (
    r"(suivant|continuer vers|next|passer en revue|vérifier|review|continue to next|étape suivante)"
)


def linkedin_easy_apply(page, profile, cv=None, letter=None, fast=False, max_screens=8):
    """LinkedIn « Candidature simplifiée » SEMI-AUTO :
      1. clique le bouton Easy Apply (si candidature EXTERNE → retour kind=external, pipeline générique prend le relais)
      2. dans la modale : remplit champs + upload CV à chaque écran
      3. avance via Suivant/Vérifier — s'ARRÊTE avant « Envoyer la candidature » (surligné, l'humain clique)
    Aucun mdp tapé, aucun envoi auto. Retour dict {ok, kind, screens, note, submit_label}."""
    import time as _t

    st = linkedin_ready(page)
    if st == "out":
        return {
            "ok": False,
            "kind": "need_login",
            "screens": 0,
            "note": "session LinkedIn déconnectée — connecte-toi à la main puis relance",
        }

    # 1. bouton Easy Apply vs Apply externe
    open_js = r"""
    () => {
      const btns=[...document.querySelectorAll('button.jobs-apply-button, button[aria-label], .jobs-apply-button')];
      const norm=s=>(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
      for(const b of btns){
        const a=norm(b.getAttribute('aria-label')), t=norm(b.innerText);
        const easy=/candidature simplifiee|easy apply/.test(a+' '+t);
        const apply=/postuler|apply|candidater/.test(a+' '+t);
        if(easy){ b.scrollIntoView({block:'center'}); b.click(); return 'easy'; }
        if(apply && b.classList.contains('jobs-apply-button')){ return 'external'; }
      }
      return 'none';
    }"""
    try:
        kind = page.evaluate(open_js)
    except Exception as e:
        return {"ok": False, "kind": "err", "screens": 0, "note": type(e).__name__}
    if kind == "external":
        return {
            "ok": False,
            "kind": "external",
            "screens": 0,
            "note": "candidature EXTERNE (redirige hors LinkedIn) — pipeline générique",
        }
    if kind == "none":
        return {
            "ok": False,
            "kind": "no_button",
            "screens": 0,
            "note": "aucun bouton Easy Apply (offre expirée/déjà postulée ?)",
        }
    _t.sleep(0.6 if fast else 1.5)

    # 2-3. boucle écrans modale : remplir + avancer, STOP avant submit
    screens = 0
    while screens < max_screens:
        try:
            fill_application(page, profile, cv=cv, letter=letter)
        except Exception:
            pass
        _t.sleep(0.3 if fast else 0.8)
        # bouton submit FINAL présent → on s'arrête (l'humain clique)
        sub = highlight_submit(page)
        if not sub:
            # fallback : chercher explicitement le libellé submit LinkedIn
            try:
                sub = page.evaluate(
                    "(rx)=>{const s=new RegExp(rx,'i');for(const b of document.querySelectorAll('button,[role=button]')){"
                    "const t=(b.innerText||b.getAttribute('aria-label')||'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');"
                    "if(s.test(t)){b.style.outline='4px solid red';b.scrollIntoView({block:'center'});return t.trim().slice(0,50);}}return '';}",
                    _LI_SUBMIT_RX,
                )
            except Exception:
                sub = ""
        if sub:
            return {
                "ok": True,
                "kind": "ready_to_submit",
                "screens": screens,
                "submit_label": sub,
                "note": "form rempli — clique ENVOYER toi-même (surligné rouge)",
            }
        # sinon avancer : Suivant/Vérifier
        adv = r"""
        (rx) => {
          const s=new RegExp(rx,'i');
          for(const b of document.querySelectorAll('button,[role=button]')){
            const t=(b.innerText||b.getAttribute('aria-label')||'').normalize('NFD').replace(/[̀-ͯ]/g,'');
            if(t && s.test(t) && !b.disabled){ b.scrollIntoView({block:'center'}); b.click(); return t.trim().slice(0,40); }
          }
          return '';
        }"""
        try:
            nxt = page.evaluate(adv, _LI_NEXT_RX)
        except Exception:
            nxt = ""
        if not nxt:
            return {
                "ok": False,
                "kind": "stuck",
                "screens": screens,
                "note": "ni Suivant ni Envoyer trouvé — termine à la main",
            }
        screens += 1
        _t.sleep(0.5 if fast else 1.2)
    return {
        "ok": False,
        "kind": "max_screens",
        "screens": screens,
        "note": f"arrêt après {max_screens} écrans — termine à la main",
    }


def _handle_smartrecruiters_iframe(page):
    """SmartRecruiters: click Apply button, wait for the application iframe,
    and return the frame object (or None if not applicable).

    SmartRecruiters loads the application form inside a dynamically created
    iframe after clicking an \"Apply\"/\"Postuler\" button. This function:
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


def apply_to_offer(page, offer_url, profile, cv_path=None, lettre_path=None, submit_highlight=True):
    """Navigue vers une offre d'emploi, remplit TOUS les champs du formulaire,
    upload CV + lettre de motivation, et surligne le bouton de soumission.

    Args:
        page: Playwright page object
        offer_url: URL de l'offre d'emploi
        profile: dict avec les champs du profil (apply_profile.json)
        cv_path: chemin absolu vers le CV PDF (optionnel, prioritaire sur profile)
        lettre_path: chemin absolu vers la lettre PDF (optionnel, prioritaire sur profile)
        submit_highlight: si True, surligne le bouton submit en rouge (sans cliquer)

    Returns:
        dict: {success, filled_count, uploaded, submit_found, submit_label, ats_type, errors, steps}
    """
    import re as _re
    import time as _time
    from pathlib import Path as _P

    result = {
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

    ROOT = _P(__file__).resolve().parent.parent  # Scripts -> Root

    def _resolve_path(p):
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
            r = _resolve_path(p)
            if r:
                cv = r
                break
    if not letter:
        for domain_key in ["ESG_Finance_Durable", "default"]:
            p = profile.get("lettre_paths", {}).get(domain_key)
            r = _resolve_path(p)
            if r:
                letter = r
                break

    # ── Step 1: Navigate ──
    try:
        r = robust_goto(page, offer_url, tries=3)
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

    def _find_profile_value(ctx):
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


def smart_upload(page, cv, letter):
    """Upload CV + lettre en matchant chaque input[type=file] par label (cv/lettre).
    Inputs cachés gérés (set_input_files marche même non visible)."""
    from pathlib import Path as _P

    done = []
    try:
        metas = page.evaluate(_FILEINPUT_JS)
    except Exception:
        metas = []
    files = {
        "cv": cv if cv and _P(cv).exists() else None,
        "letter": letter if letter and _P(letter).exists() else None,
    }
    used = set()
    # 1) match par label
    for m in metas:
        f = files.get(m["kind"])
        if f and m["kind"] not in used:
            try:
                page.locator(f'[data-wn-file="{m["i"]}"]').set_input_files(f, timeout=3000)
                done.append(f"{m['kind']}:{_P(f).name}")
                used.add(m["kind"])
            except Exception:
                pass
    # 2) fallback : inputs restants -> cv puis letter dans l'ordre d'apparition
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


# ── REMPLISSAGE UNIVERSEL DE CANDIDATURE : tous les champs + tous les documents ─
# Scanne CHAQUE élément saisissable (shadow DOM), le classe, le remplit. Rapport couverture.
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

# lexique riche : (regex sur le contexte du champ) -> clé de profil. Ordre = priorité.
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
    ),  # générique en dernier
]
import re as _re_lex


def _match_profile_key(key):
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


def accept_consent_dialog(page):
    """Clique Proceed/Continuer d'un dialogue de consentement obligatoire (≠ submit, ≠ Decline)."""
    try:
        return page.evaluate(_CONSENT_DIALOG_JS)
    except Exception:
        return {"clicked": ""}


def _best_form_target(page):
    """Renvoie le contexte (page OU iframe) qui contient le vrai formulaire.
    SmartRecruiters/Taleo/SuccessFactors chargent le form dans une iframe :
    on choisit le frame avec le plus de champs de saisie visibles."""
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
            if fr.is_detached():  # frame mort (page changée) → jamais cible
                continue
        except Exception:
            continue
        try:
            n = fr.evaluate(_COUNT_VISIBLE_INPUTS_JS)
        except Exception:
            continue
        if n > best_n + 1:  # marge : ne bascule pas pour 1 champ isolé
            best, best_n = fr, n
    return best


def fill_application(page, profile, cv=None, letter=None, docs=None):
    """POSTULER UNIVERSEL : reconnait TOUS les patterns de champs et remplit tout —
    texte/email/tel/date/select(dropdown)/radio(civilité)/checkbox(CGU)/textarea +
    upload de TOUS les documents (CV, lettre, + docs extra par label).
    Cherche le form dans les iframes (SmartRecruiters/Taleo) si la page est vide.
    Retour {total, filled, uploaded, consent, cover_pct, unmatched:[…]}."""
    from pathlib import Path as _P

    page = _best_form_target(page)  # bascule sur l'iframe du form si besoin
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
            continue  # déjà rempli
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
    # SELECT sans valeur profil : civilité -> Monsieur, pays -> France
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
    # RADIO civilité (Monsieur / M.)
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
    # CHECKBOX consentement obligatoire (CGU/RGPD) — pas marketing
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
    # bug7 : après cochage CGU, un dialogue de consentement (Proceed/Continuer) peut s'ouvrir
    # (SuccessFactors #dataPrivacyId). Cliquer Proceed = valider la case obligatoire, PAS soumettre.
    if consent:
        try:
            page.evaluate(_CONSENT_DIALOG_JS)
        except Exception:
            pass
    # UPLOAD tous documents : CV + lettre par label + docs extra
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


def _fold(s):
    """minuscule + sans accents (Française→francaise) pour matcher les <option>."""
    import unicodedata as _ud

    return "".join(
        c for c in _ud.normalize("NFD", str(s).lower()) if _ud.category(c) != "Mn"
    ).strip()


def _pick_option(loc, options, val, extra=()):
    """Sélectionne l'option d'un <select> matchant val (label/valeur), + variantes extra.
    Accent-insensible + match code ISO (option value='FR' pour 'France')."""
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


# ── NAVIGATION : aides simples ──────────────────────────────────────────────
# Le projet ne cherche PAS a se faire passer pour un humain : ni souris en
# courbe, ni frappe au hasard, ni masquage du navigateur automatise. Ces aides
# gardent leurs noms (appelees partout) mais font l'action directement ; la
# pause est fixe, par politesse envers le site, pas pour tromper sa detection.

import random as _rnd


def human_pause(page, lo=350, hi=1100):
    """Pause fixe (moyenne de lo et hi), pour ne pas marteler le site."""
    try:
        page.wait_for_timeout((lo + hi) // 2)
    except Exception:
        pass


def human_type(page, selector, text, click_first=True):
    """Remplit le champ. Retour True si champ trouve."""
    try:
        loc = page.locator(selector).first
        if click_first:
            loc.click(timeout=3000)
        loc.fill(str(text), timeout=3000)
        return True
    except Exception:
        return False


def human_click(page, selector, steps=None, timeout=4000):
    """Clique l'element. Retour True si clique."""
    try:
        page.locator(selector).first.click(timeout=timeout)
        return True
    except Exception:
        return False


def human_scroll(page, steps=None):
    """Fait defiler la page de quelques ecrans."""
    for _ in range(steps or 3):
        try:
            page.mouse.wheel(0, 500)
            human_pause(page, 250, 800)
        except Exception:
            break


import re as _re_block

# domaines pubs/analytics/tags : inutiles pour postuler, ralentissent → bloqués
_AD_RX = _re_block.compile(
    r"(doubleclick|googlesyndication|google-analytics|googletagmanager|/gtag/|/gtm\.js"
    r"|facebook\.net|connect\.facebook|hotjar|mouseflow|fullstory|segment\.(io|com)"
    r"|criteo|taboola|outbrain|adservice|adsystem|/pixel|/beacon|cdn\.cookielaw|onetrust)",
    _re_block.I,
)

# captcha/anti-bot : JAMAIS bloqué (l'humain doit VOIR la grille d'images pour résoudre)
_CAPTCHA_OK_RX = _re_block.compile(
    r"(recaptcha|gstatic\.com/recaptcha|hcaptcha|turnstile|challenges\.cloudflare"
    r"|arkoselabs|funcaptcha|geo\.captcha|captcha-delivery)",
    _re_block.I,
)


def block_resources(ctx, images=False):
    """TURBO : abandonne les requêtes lourdes/inutiles (media, fonts, pubs, analytics ;
    images aussi si images=False). Accélère 2-5× le chargement. CSS gardé (layout/clics).
    Les ressources CAPTCHA passent toujours (sinon grille invisible = insoluble)."""
    heavy = {"media", "font"} | (set() if images else {"image"})

    def _route(route):
        try:
            rq = route.request
            if _CAPTCHA_OK_RX.search(rq.url):
                return route.continue_()
            if rq.resource_type in heavy or _AD_RX.search(rq.url):
                return route.abort()
            return route.continue_()
        except Exception:
            try:
                return route.continue_()
            except Exception:
                pass

    try:
        ctx.route("**/*", _route)
    except Exception:
        pass


def robust_goto(page, url, tries=3, wait_until="domcontentloaded"):
    """goto avec retry + backoff sur erreurs réseau/timeout transitoires.
    Retour {ok, status, note}. Ne contourne pas captcha (détecté ailleurs)."""
    last = ""
    for i in range(tries):
        try:
            resp = page.goto(url, timeout=45000, wait_until=wait_until)
            # iCIMS + SPAs: client-side redirect can destroy context — settle wait
            try:
                page.wait_for_load_state("domcontentloaded", timeout=2500)
            except Exception:
                pass
            page.wait_for_timeout(_rnd.randint(300, 700))
            code = resp.status if resp else 0
            if code and (code == 429 or code >= 500):
                last = f"HTTP {code}"
                page.wait_for_timeout(min(2**i * 3000, 20000))
                continue
            return {"ok": True, "status": code, "note": "ok"}
        except Exception as e:
            last = str(e).splitlines()[0][:120]
            page.wait_for_timeout(min(2**i * 2500, 15000))
    return {"ok": False, "status": 0, "note": last or "goto échoué"}


# ── OTP / code email (SEMI-AUTO : colle le code, surligne Verify, l'humain clique) ──
_OTP_RX_ATTR = r"(otp|passcode|one.?time|verification|verif|\bcode\b|s[eé]cur|security|token|\bpin\b|2fa|mfa|activation|confirm)"

_OTP_DETECT_JS = r"""
() => {
  const vis = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0; };
  const bad = ['hidden','checkbox','radio','file','submit','button','password'];
  const ins = [...document.querySelectorAll('input')].filter(vis).filter(e=>!bad.includes((e.type||'').toLowerCase()));
  const RX = /__OTP__/i;
  const single = ins.some(e => RX.test((e.name||'')+(e.id||'')+(e.placeholder||'')+(e.getAttribute('aria-label')||'')+(e.autocomplete||'')));
  const oc = ins.some(e => e.getAttribute('autocomplete')==='one-time-code');
  const boxes = ins.filter(e => e.maxLength===1).length >= 4;
  const bodyOtp = /(code (de |à |a )?(v[eé]rification|confirmation|s[eé]curit[eé])|verification code|one.?time (code|password|passcode)|entrez le code|enter the code|saisissez le code|passcode)/i
                  .test((document.body?document.body.innerText:'').slice(0,4000));
  return {otp: !!(single||oc||boxes||bodyOtp), single, oc, boxes, bodyOtp};
}
""".replace("__OTP__", _OTP_RX_ATTR)

_OTP_FILL_JS = r"""
(code) => {
  const vis = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0; };
  const bad = ['hidden','checkbox','radio','file','submit','button','password'];
  const ins = [...document.querySelectorAll('input')].filter(vis).filter(e=>!bad.includes((e.type||'').toLowerCase()));
  const set = (el,v)=>{ el.focus(); el.value=v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); };
  const RX = /__OTP__/i;
  // 1) champ unique (name/id/placeholder/aria = code) et assez large
  const single = ins.find(e => RX.test((e.name||'')+(e.id||'')+(e.placeholder||'')+(e.getAttribute('aria-label')||'')) && (e.maxLength<0 || e.maxLength>=code.length));
  if (single) { set(single, code); return {filled:1, mode:'single'}; }
  // 2) autocomplete one-time-code
  const oc = ins.find(e => e.getAttribute('autocomplete')==='one-time-code');
  if (oc) { set(oc, code); return {filled:1, mode:'auto'}; }
  // 3) boîtes 1 chiffre (maxlength=1)
  const boxes = ins.filter(e => e.maxLength===1);
  if (boxes.length >= code.length) {
    for (let i=0;i<code.length;i++) set(boxes[i], code[i]);
    return {filled:code.length, mode:'boxes'};
  }
  return {filled:0, mode:'none'};
}
""".replace("__OTP__", _OTP_RX_ATTR)

_OTP_VERIFY_JS = r"""
() => {
  const vis = el => { const r=el.getBoundingClientRect(); return r.width>4 && r.height>4; };
  const RX = /(v[eé]rifier|verify|valider|validate|confirmer|confirm|soumettre|submit|continuer|continue|activer|activate|envoyer)/i;
  const NEVER = /(annuler|cancel|renvoyer|resend|renvoi|retour|back|modifier)/i;
  const els = [...document.querySelectorAll('button,input[type=submit],a,[role=button]')].filter(vis);
  for (const el of els) {
    const t = (el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    if (t && t.length<26 && RX.test(t) && !NEVER.test(t)) {
      el.style.outline='4px solid red'; el.style.outlineOffset='2px';
      el.setAttribute('data-wn-otp','verify'); el.scrollIntoView({block:'center'});
      return t;
    }
  }
  return '';
}
"""


def otp_present(page):
    """True si la page attend un code OTP (champ code / boîtes 1-chiffre / texte)."""
    try:
        return bool(page.evaluate(_OTP_DETECT_JS).get("otp"))
    except Exception:
        return False


def paste_otp(page, code):
    """Colle le code OTP dans le(s) champ(s). NE soumet PAS. Retour {filled, mode}."""
    if not code:
        return {"filled": 0, "mode": "no_code"}
    try:
        return page.evaluate(_OTP_FILL_JS, str(code).strip())
    except Exception as e:
        return {"filled": 0, "mode": "err:" + type(e).__name__}


def highlight_otp_verify(page):
    """Surligne en ROUGE le bouton Vérifier/Valider (data-wn-otp=verify). NE clique PAS.
    Retour le libellé du bouton, ou '' si introuvable."""
    try:
        return page.evaluate(_OTP_VERIFY_JS)
    except Exception:
        return ""


def otp_flow(page, code):
    """SEMI-AUTO : colle le code + surligne le bouton de validation. L'HUMAIN clique.
    Retour {pasted, mode, verify}."""
    r = paste_otp(page, code)
    v = highlight_otp_verify(page) if r.get("filled") else ""
    return {"pasted": r.get("filled", 0), "mode": r.get("mode"), "verify": v}


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


def homepage_fallback(page, entreprise, role="", homepage=None):
    """PIPELINE DE BASE quand l'URL d'offre est morte :
    nom entreprise → site officiel (cache homepages.json, sinon résolution
    enrich_homepages : slug+validation+web) → section Carrières → offre.
    Retour {ok, homepage, careers, kind, via, note}."""
    import json as _json
    from pathlib import Path as _P

    hp = homepage
    if not hp:  # 1) cache
        try:
            hp = _json.loads(
                (_P(__file__).parent / "homepages.json").read_text(encoding="utf-8")
            ).get(entreprise)
        except Exception:
            hp = None
    if not hp:  # 2) résolution à la volée (devine domaine + valide HTTP)
        try:
            from enrich_homepages import resolve as _resolve

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
                    _hp_f = _P(__file__).parent / "homepages.json"
                    c = _json.loads(_hp_f.read_text(encoding="utf-8"))
                    c[entreprise] = hp
                    # Atomique : ce cache est relu par d'autres programmes, et
                    # un write_text interrompu le laissait tronque — donc
                    # illisible, donc reconstruit de zero au scan suivant.
                    __import__("jutil").jwrite(_hp_f, c)
                except Exception:
                    pass
        except Exception:
            hp = None
    if not hp:
        return {"ok": False, "note": "no_homepage"}
    g = robust_goto(page, hp, tries=2)
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


def apply_stealth(context_or_page):
    """RETIRE. Masquer l'automatisation au site (navigator.webdriver, empreinte
    WebGL...) est un contournement anti-bot, contraire aux regles du projet.
    Garde pour les appelants ; ne fait rien."""
    return False


# ── MOTEUR NAV : Playwright standard, seul ──────────────────────────────────
# Les moteurs « furtifs » (patchright, rebrowser) sont retires : leur raison
# d'etre est d'echapper a la detection des robots. Le parametre engine est
# garde pour compatibilite et ignore.


def available_engines():
    """Moteurs installes : Playwright seul."""
    try:
        import playwright.sync_api  # noqa: F401

        return ["playwright"]
    except Exception:
        return []


def get_sync_playwright(engine="auto"):
    """Retourne (sync_playwright, "playwright"), quel que soit engine."""
    from playwright.sync_api import sync_playwright

    return sync_playwright, "playwright"


# ── BROWSER ROBUSTNESS : crash recovery + auto-relaunch ──────────────────


class BrowserSession:
    """Gère le cycle de vie du navigateur avec recovery automatique.

    Usage:
        bs = BrowserSession()
        page = bs.start()
        # ... si crash ...
        page = bs.recover()  # relance navigateur + contexte + page fluo
    """

    def __init__(self, headless: bool = False, engine: str = "playwright"):
        self.headless = headless
        self.engine = engine
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._crashed = False

    def _get_playwright(self):
        sp, self.engine = get_sync_playwright(self.engine)
        return sp

    def start(self):
        """Lance le navigateur et retourne la page active."""
        SyncPlaywright = self._get_playwright()
        self._playwright = SyncPlaywright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--disable-gpu" if self.headless else "",
            ],
        )
        self._context = self._browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        self._page = self._context.new_page()
        self._crashed = False
        return self._page

    def recover(self):
        """Relance navigateur après crash (même context, nouvelle page). Retour page."""
        import time as _t

        _t.sleep(1)
        try:
            if self._page and not self._page.is_closed():
                self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser and self._browser.is_connected():
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        _t.sleep(1)
        self._crashed = True
        return self.start()

    def is_alive(self) -> bool:
        """Vérifie si le navigateur est toujours connecté."""
        try:
            return (
                self._browser is not None
                and self._browser.is_connected()
                and self._page is not None
                and not self._page.is_closed()
                and not self._page.evaluate("() => true").get("_bogus") == 1
            )
        except Exception:
            return False

    def close(self):
        try:
            if self._page and not self._page.is_closed():
                self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser and self._browser.is_connected():
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass


# ── GOTO robuste v2 : browser recovery intégré ───────────────────────────

# ── STRATEGIES PAR CATEGORIE (v5 — 62 sites) ──────────────────────────────

# JS snippets importes de site_strategies.py
from site_strategies import (
    FIRST_JOB_OFFER_JS,
    ATS_APPLY_REGISTER_DETECT_JS,
    ROOT_DOMAIN_CHECK_JS,
    SITEMAP_PROBE_JS,
    BPIFRANCE_DIDOMI_JS,
    BPCE_INPUT_JS,
    MEESCHAERT_REGISTER_FALLBACK_JS,
    get_strategy,
)


def click_first_job_offer(page):
    """Cat2/3 : trouve et clique la premiere offre d'emploi sur la page.
    Retour {found, href, label, total_offers}."""
    try:
        r = page.evaluate(FIRST_JOB_OFFER_JS)
    except Exception:
        return {"found": False, "total_offers": 0}
    if not r or not r.get("found"):
        return r or {"found": False, "total_offers": 0}
    try:
        page.locator('[data-wn-firstjob="1"]').first.click(timeout=5000)
        page.wait_for_timeout(2500)
        return r
    except Exception:
        try:
            page.goto(r["href"], timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            return r
        except Exception:
            return {"found": False, "error": "click and goto failed", "href": r.get("href", "")}


def check_apply_for_register(page):
    """Cat2/3 : apres avoir clique une offre, verifie si le flux apply
    inclut une creation de compte (email + password demandes).
    Retour {kind, hasEmail, hasNewPwd, ...}."""
    try:
        return page.evaluate(ATS_APPLY_REGISTER_DETECT_JS)
    except Exception:
        return {"kind": "error"}


def probe_auth_endpoints(page):
    """Cat3 : scanne les liens /login, /register, /signin dans la page.
    Retour {found, authLinks, footerAuthLinks}."""
    try:
        return page.evaluate(SITEMAP_PROBE_JS)
    except Exception:
        return {"found": 0, "authLinks": [], "footerAuthLinks": []}


def check_root_domain(page):
    """Cat4 : verifie si le domaine racine est accessible et a des liens carriere.
    Retour {title, bodyPreview, hasCareerLinks, careerLinks, url, status}."""
    try:
        return page.evaluate(ROOT_DOMAIN_CHECK_JS)
    except Exception:
        return {
            "title": "",
            "hasCareerLinks": False,
            "careerLinks": [],
            "url": "",
            "status": "error",
        }


def didomi_reject_and_wait(page, wait_ms=12000):
    """Ferme la banniere Didomi (Bpifrance) et attend le chargement React.
    Retour {done, ...}."""
    try:
        r = page.evaluate(BPIFRANCE_DIDOMI_JS)
    except Exception:
        r = {"done": "err"}
    page.wait_for_timeout(wait_ms)
    return r


def scan_nonstandard_inputs(page):
    """Scan les inputs non-standards (BPCE, Engagement Jeunes) pour diagnostic.
    Retour {found, inputs}."""
    try:
        return page.evaluate(BPCE_INPUT_JS)
    except Exception:
        return {"found": 0, "inputs": []}
