"""LinkedIn Easy Apply : remplit, l'humain envoie.

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6).
"""

from typing import Any

from jobhunter.navigation.formulaires import fill_application
from jobhunter.navigation.segment import highlight_submit


def linkedin_ready(page: Any) -> Any:
    """LinkedIn : session connectée ? (aucun mdp tapé — on lit juste l'état).

    Retour True si nav globale connectée détectée, False si mur login/join.
    """
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


def linkedin_easy_apply(
    page: Any,
    profile: dict[str, Any],
    cv: Any = None,
    letter: Any = None,
    fast: bool = False,
    max_screens: int = 8,
) -> dict[str, Any]:
    """LinkedIn « Candidature simplifiée » SEMI-AUTO : 1.

    clique le bouton Easy Apply (si candidature EXTERNE → retour kind=external, pipeline
    générique prend le relais) 2. dans la modale : remplit champs + upload CV à chaque
    écran 3. avance via Suivant/Vérifier — s'ARRÊTE avant « Envoyer la candidature »
    (surligné, l'humain clique) Aucun mdp tapé, aucun envoi auto. Retour dict {ok, kind,
    screens, note, submit_label}.
    """
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
