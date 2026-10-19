"""Lecture d'une page : bandeau cookies (REFUS d'abord), analyse, attente du formulaire.

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6).
"""

from typing import Any

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
    """Le script qui repère, sur la page, le lien ou bouton correspondant à une tâche.

    Args:
        task: « register », « login », « apply » ou « careers ».

    Returns:
        Le code JavaScript à évaluer dans la page.
    """
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


def dismiss_cookies(page: Any) -> Any:
    """Ferme le bandeau de cookies en REFUSANT d'abord ce qui n'est pas nécessaire.

    Args:
        page: la page Playwright.

    Returns:
        {done: ce qui a été fait} ; {done: "err"} si le script a échoué.
    """
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


def dismiss_overlays(page: Any) -> Any:
    """Ferme les widgets chat (Intercom/Drift/Zendesk/Crisp…) et modales non-essentielles qui interceptent les clics.

    NE touche PAS aux bannières cookies/formulaires d'offre/auth.
    """
    try:
        return page.evaluate(_OVERLAY_JS)
    except Exception:
        return {"closed": 0, "kinds": []}


def analyze(page: Any) -> Any:
    """Analyse la page : type (formulaire, connexion, offre…), CAPTCHA, blocage.

    Args:
        page: la page Playwright.

    Returns:
        Le diagnostic ; « other » sans CAPTCHA si l'analyse a échoué.
    """
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


def wait_for_form(
    page: Any, min_inputs: int = 1, timeout_ms: int = 7000, timeout: int | None = None
) -> Any:
    """Attend que les champs de saisie apparaissent (formulaire chargé dynamiquement).

    Retour nb d'inputs visibles (0 = jamais rendu).
    """
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


def click_for_task(page: Any, task: str) -> Any:
    """Clique le lien ou bouton qui mène à la tâche (jamais un bouton d'envoi).

    Args:
        page: la page Playwright.
        task: « register », « login », « apply » ou « careers ».

    Returns:
        Le libellé cliqué, ou None si rien ne correspond.
    """
    try:
        r = page.evaluate(pick_js(task))
        if r and r.get("found"):
            page.locator('[data-wn-pick="1"]').first.click(timeout=4000)
            page.wait_for_timeout(1500)
            return r.get("label")
    except Exception:
        pass
    return None
