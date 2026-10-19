"""Reconnaissance des parties d'une page, ATS detecte, bouton d'envoi SURLIGNE (jamais clique).

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6).
"""

from typing import Any

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


def detect_ats(page: Any) -> Any:
    """Reconnait la plateforme/ATS du site d'entreprise (Workday, iCIMS, TalentSoft, SmartRecruiters, Greenhouse, Lever, Taleo, SuccessFactors, Teamtailor, Breezy, Recruitee, Workable, WTTJ, … + 'generic').

    Retour {name, jobLinkRx, searchSel}.
    """
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


def segment_page(page: Any) -> Any:
    """RECONNAISSANCE COMPLÈTE : mappe toutes les parties de la page — régions (header/nav/main/footer/aside/iframes), overlays (cookie/captcha/chat/ modal/newsletter), chaque bouton classé par rôle (cookie/login/register/apply/ submit/careers/search/social/menu/lang), chaque formulaire + son but, nb d'offres, signaux (mdp/fichier/email).

    Retour dict complet (base des décisions nav).
    """
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


def plan_action(page: Any, goal: str = "apply") -> dict[str, Any]:
    """CERVEAU déterministe : lit la carte complète (segment_page) et renvoie la MEILLEURE action suivante — {action, role, reason, seg}.

    Actions : stop(captcha) / cookies / ready / drill / careers / click / auth /
    register / search / none. Gratuit, hors-ligne, sans LLM. Complète smart_step (qui
    exécute).
    """
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


def describe_page(page: Any) -> str:
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


def try_open_form(page: Any) -> Any:
    """Clique un bouton 'Postuler/Apply' pour ouvrir le formulaire.

    JAMAIS un submit final. Retour label cliqué ou ''. (Défini dans web_nav pour
    apply_to_offer — était absent → NameError).
    """
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


def highlight_submit(page: Any) -> Any:
    """Surligne le bouton d'envoi final en ROUGE + scroll.

    Ne clique PAS (l'humain clique). Retour label ou ''. (Défini dans web_nav pour
    apply_to_offer — était absent → NameError).
    """
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
