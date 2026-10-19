"""Connexion par etapes (le mot de passe n'est JAMAIS tape) et bascule vers l'inscription.

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6).

Decision : docs/adr/0005-aucune-soumission-automatique.md
"""

from typing import Any

from jobhunter.navigation.page import analyze

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


def react_submit(page: Any) -> bool:
    """Soumission native HTML (form.requestSubmit) quand le clic bouton est avalé par React/SPA.

    Retour True si un form a été soumis.
    """
    try:
        return bool(page.evaluate(_REQSUBMIT_JS))
    except Exception:
        return False


def login_flow(page: Any, email: str, pwd: str, max_steps: int = 3) -> dict[str, Any]:
    """Login multi-étapes (SmartRecruiters : email→continue→password→login).

    Remplit les champs vides + clique continue/login à chaque étape. Fallback
    requestSubmit() si le clic ne fait pas avancer (React). Le mot de passe n'est JAMAIS
    tape : regle du projet, quel que soit pwd.
    """
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


def switch_to_register(page: Any) -> dict[str, Any]:
    """Bascule d'un écran login vers l'écran création de compte (toggle/onglet).

    Retour {switched, label, kind}. kind = analyze après clic.
    """
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
