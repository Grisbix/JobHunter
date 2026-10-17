#!/usr/bin/env python3
"""
site_strategies.py — Stratégies spécifiques par site pour les 62 sites sans compte.

4 catégories :
  CAT1 — ESPACE CANDIDAT BLOQUÉ (11 sites) : solutions de contournement
  CAT2 — ATS EXTERNE (5 sites) : création via offre d'emploi
  CAT3 — SANS ESPACE CANDIDAT (37 sites) : scan offres → apply → register implicite
  CAT4 — INACCESSIBLE (9 sites) : fallback domaines racine

Chaque entrée = {domain: {category, strategy, url_override, js_fix, wait_ms, note}}
"""

from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# CATÉGORIE 1 — ESPACE CANDIDAT EXISTANT MAIS BLOQUÉ (11 sites)
# ──────────────────────────────────────────────────────────────────────────────
CAT1_BLOCKED: dict[str, dict[str, Any]] = {
    # ── PROBLÈME : formulaire alerte email (pas un vrai register) ──
    "jobs.amundi.com": {
        "category": "blocked",
        "subtype": "newsletter_masquerade",
        "strategy": "detect_newsletter_form",
        "url_override": "https://jobs.amundi.com/",
        "js_fix": None,
        "wait_ms": 0,
        "note": "Create candidate area = email alert form. ANALYZE must detect single email+no password = newsletter, not register.",
    },
    # ── PROBLÈME : Cloudflare + CAPTCHA login ──
    "group.pictet": {
        "category": "blocked",
        "subtype": "cloudflare_captcha",
        "strategy": "manual_only",
        "url_override": None,
        "js_fix": None,
        "wait_ms": 0,
        "note": "Cloudflare anti-bot + CAPTCHA. Impossible en automatique. Requiert intervention humaine.",
    },
    # ── PROBLÈME : formulaire React ne charge pas (cookies Didomi bloquent JS) ──
    "talents.bpifrance.fr": {
        "category": "blocked",
        "subtype": "didomi_react_block",
        "strategy": "didomi_reject_then_wait",
        "url_override": "https://talents.bpifrance.fr/connexion-compte-candidatures/",
        "js_fix": "BPIFRANCE_DIDOMI_JS",  # Fermer Didomi + attendre 10s pour React
        "wait_ms": 12000,  # React hydration peut prendre 8-12s
        "note": "Didomi bloque le chargement React. Fermer Didomi + wait long (>10s) pour hydratation.",
    },
    # ── PROBLÈME : inputs non-standards (noms différents de email/password) ──
    "labanquepostale.fr": {
        "category": "blocked",
        "subtype": "nonstandard_inputs",
        "strategy": "extended_input_detect",
        "js_fix": "BPCE_INPUT_JS",  # Scanner les vrais noms d'inputs
        "wait_ms": 3000,
        "note": "Page 'Accès à vos comptes'. Inputs nommés différemment. Scanner les names réels.",
    },
    "banquepopulaire.fr": {
        "category": "blocked",
        "subtype": "nonstandard_inputs",
        "strategy": "extended_input_detect",
        "js_fix": "BPCE_INPUT_JS",
        "wait_ms": 3000,
        "note": "Même problème que BanquePostale — groupe BPCE.",
    },
    # ── PROBLÈME : anti-bot extrême (patchright timeout) ──
    "recrutement.bpce.fr": {
        "category": "blocked",
        "subtype": "extreme_antibot",
        "strategy": "manual_only",
        "url_override": None,
        "js_fix": None,
        "wait_ms": 0,
        "note": "Anti-bot extrême — même patchright timeout. Requiert intervention humaine.",
    },
    # ── PROBLÈME : CAPTCHA login ──
    "recrutement.natixis.com": {
        "category": "blocked",
        "subtype": "captcha_login",
        "strategy": "manual_only",
        "url_override": None,
        "js_fix": None,
        "wait_ms": 0,
        "note": "Login CAPTCHA. Requiert intervention humaine.",
    },
    # ── PROBLÈME : inputs nommés différemment ──
    "engagement-jeunes.com": {
        "category": "blocked",
        "subtype": "nonstandard_inputs",
        "strategy": "extended_input_detect",
        "js_fix": "ENGAGEMENT_JEUNES_JS",
        "wait_ms": 3000,
        "note": "Register email=False car inputs nommés différemment. Scanner les noms réels.",
    },
    # ── PROBLÈME : login employés uniquement (popin fonctionne mais pas de register) ──
    "meeschaert.com": {
        "category": "blocked",
        "subtype": "employee_login_only",
        "strategy": "login_only_no_register",
        "url_override": "https://www.meeschaert.com/carrieres/recrutement",
        "js_fix": "MEESCHAERT_REGISTER_FALLBACK_JS",  # Tenter register via API cachée
        "wait_ms": 3000,
        "note": "Login employés via popin OK. Pas de register visible. Chercher endpoint register caché ou candidature spontanée.",
    },
    # ── PROBLÈME : login investisseurs uniquement ──
    "kkr.com": {
        "category": "blocked",
        "subtype": "investor_login_only",
        "strategy": "skip_no_candidate_space",
        "url_override": "https://www.kkr.com/careers",
        "js_fix": None,
        "wait_ms": 0,
        "note": "Login investisseurs uniquement. Pas d'espace candidat. Postuler directement sur les offres.",
    },
    # ── PROBLÈME : login clients (MyLO, LO Gate) ──
    "lombardodier.com": {
        "category": "blocked",
        "subtype": "client_login_only",
        "strategy": "skip_no_candidate_space",
        "url_override": "https://www.lombardodier.com/careers",
        "js_fix": None,
        "wait_ms": 0,
        "note": "Login clients (MyLO, LO Gate). Pas d'espace candidat. Postuler directement sur offres.",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# CATÉGORIE 2 — ATS EXTERNE (5 sites)
# ──────────────────────────────────────────────────────────────────────────────
CAT2_ATS: dict[str, dict[str, Any]] = {
    "jobs.smartrecruiters.com": {
        "category": "ats_external",
        "subtype": "smartrecruiters",
        "strategy": "apply_creates_account",
        "url_override": None,  # URL spécifique à l'offre, pas le domaine générique
        "js_fix": None,
        "wait_ms": 0,
        "note": "Pas de login direct. Passer par une offre spécifique → postuler = créer compte.",
        "ats_type": "SmartRecruiters",
    },
    "carbon4finance.breezy.hr": {
        "category": "ats_external",
        "subtype": "breezyhr",
        "strategy": "apply_creates_account",
        "url_override": None,
        "js_fix": None,
        "wait_ms": 0,
        "note": "BreezyHR — postuler via offre = compte créé.",
        "ats_type": "BreezyHR",
    },
    "karmen.breezy.hr": {
        "category": "ats_external",
        "subtype": "breezyhr",
        "strategy": "apply_creates_account",
        "url_override": None,
        "js_fix": None,
        "wait_ms": 0,
        "note": "BreezyHR — postuler via offre = compte créé.",
        "ats_type": "BreezyHR",
    },
    "sweep.net": {
        "category": "ats_external",
        "subtype": "teamtailor",
        "strategy": "apply_creates_account",
        "url_override": "https://sweep.net/jobs",  # ou /careers
        "js_fix": None,
        "wait_ms": 0,
        "note": "Teamtailor — login hasEmail=False. Postuler via offre = créer compte.",
        "ats_type": "Teamtailor",
    },
    "carlyle.com": {
        "category": "ats_external",
        "subtype": "workday",
        "strategy": "apply_creates_account",
        "url_override": "https://www.carlyle.com/about-carlyle/careers",
        "js_fix": None,
        "wait_ms": 0,
        "note": "Workday (myworkdayjobs). Postuler via offre → création compte Workday.",
        "ats_type": "Workday",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# CATÉGORIE 3 — SANS ESPACE CANDIDAT (37 sites)
# ──────────────────────────────────────────────────────────────────────────────
CAT3_NO_SPACE: dict[str, dict[str, Any]] = {
    "careers.societegenerale.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Page carrière avec offres. Cliquer première offre → vérifier formulaire apply.",
    },
    "careers.axa.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Page carrière avec offres. Cliquer première offre.",
    },
    "careers.bnpparibas.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "BNP Paribas Careers. Offres → apply = compte.",
    },
    "careers.lu.bnpparibas.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "BNP Paribas Luxembourg. Offres → apply = compte.",
    },
    "careers.bpce.fr": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "BPCE Careers (différent de recrutement.bpce.fr). Offres seulement.",
    },
    "eiffage.com": {
        "category": "no_space",
        "strategy": "spontaneous_application",
        "url_override": None,
        "note": "Candidature spontanée. Pas d'espace candidat. Postuler = compte.",
    },
    "rejoindre-ey.com": {
        "category": "no_space",
        "strategy": "spontaneous_application",
        "url_override": None,
        "note": "EY — rejoindre-ey. Candidature spontanée.",
    },
    "ey.com": {
        "category": "no_space",
        "strategy": "probe_sitemap",
        "url_override": None,
        "note": "EY corporate. Chercher /careers/login dans le sitemap.",
    },
    "eurazeo.com": {
        "category": "no_space",
        "strategy": "click_apply_cta",
        "url_override": None,
        "note": "Bouton Apply/Postuler visible (apply_cta). Cliquer pour dérouler le formulaire.",
    },
    "tikehaucapital.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Tikehau Capital. Page carrière avec offres.",
    },
    "largilliere-finance.com": {
        "category": "no_space",
        "strategy": "click_apply_cta",
        "url_override": None,
        "note": "Apply CTA visible.",
    },
    "ca-cib.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Crédit Agricole CIB. Offres → postuler.",
    },
    "credit-agricole.fr": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Crédit Agricole. Offres → postuler.",
    },
    "caissedesdepots.fr": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Caisse des Dépôts. Offres → postuler.",
    },
    "robeco.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Robeco careers. Offres → postuler.",
    },
    "carbon4finance.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Carbon4 Finance (site corporate, pas breezy.hr).",
    },
    "group.bnpparibas": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": "https://group.bnpparibas/carrieres",
        "note": "BNP Paribas Groupe. Page carrières.",
    },
    "im.natixis.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Natixis IM. Offres → postuler.",
    },
    "ubs.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": "https://www.ubs.com/global/en/careers.html",
        "note": "UBS Careers. Déjà redirigé dans batch_comptes. Offres → postuler.",
    },
    "apax.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Apax Partners. Offres → postuler.",
    },
    "paipartners.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "PAI Partners. Offres → postuler.",
    },
    "oliverwyman.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Oliver Wyman. Offres → postuler.",
    },
    "mckinsey.com": {
        "category": "no_space",
        "strategy": "blocked_geo",
        "url_override": None,
        "note": "McKinsey — bloqué (géolocalisation?). Essayer via VPN ou /careers global.",
    },
    "bain.com": {
        "category": "no_space",
        "strategy": "blocked_geo",
        "url_override": None,
        "note": "Bain — bloqué. Essayer via VPN ou /careers global.",
    },
    "bcg.com": {
        "category": "no_space",
        "strategy": "blocked_geo",
        "url_override": None,
        "note": "BCG — bloqué. Essayer via VPN ou /careers global.",
    },
    "kearney.com": {
        "category": "no_space",
        "strategy": "blocked_geo",
        "url_override": None,
        "note": "Kearney — bloqué. Essayer via VPN ou /careers global.",
    },
    "zurich.com": {
        "category": "no_space",
        "strategy": "blocked_geo",
        "url_override": None,
        "note": "Zurich Insurance — bloqué.",
    },
    "swissre.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Swiss Re. Offres → postuler.",
    },
    "swisslife-am.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Swiss Life AM. Offres → postuler.",
    },
    "juliusbaer.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Julius Baer. Offres → postuler.",
    },
    "ardian.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Ardian. Offres → postuler.",
    },
    "candriam.com": {
        "category": "no_space",
        "strategy": "captcha_blocked",
        "url_override": None,
        "note": "Candriam — CAPTCHA sur page carrière. Intervention humaine.",
    },
    "allianzgi.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Allianz GI. Offres → postuler.",
    },
    "axa-im.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "AXA IM. Offres → postuler.",
    },
    "quilvest.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Quilvest. Offres → postuler.",
    },
    "greenly.earth": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Greenly. Offres → postuler.",
    },
    "sipios.com": {
        "category": "no_space",
        "strategy": "click_offer_then_detect",
        "url_override": None,
        "note": "Sipios. Offres → postuler.",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# CATÉGORIE 4 — INACCESSIBLE (9 sites)
# ──────────────────────────────────────────────────────────────────────────────
CAT4_DEAD: dict[str, dict[str, Any]] = {
    "rafp.fr": {
        "category": "dead",
        "subtype": "timeout",
        "strategy": "retry_root_domain",
        "url_override": "https://www.rafp.fr",
        "note": "Timeout page carrière. Essayer domaine racine.",
    },
    "dedale-intelligence.com": {
        "category": "dead",
        "subtype": "connection_refused",
        "strategy": "retry_root_domain",
        "url_override": "https://www.dedale-intelligence.com",
        "note": "Connexion refusée. Essayer domaine racine.",
    },
    "jobs.careers.altios.com": {
        "category": "dead",
        "subtype": "dns_error",
        "strategy": "skip_unrecoverable",
        "url_override": None,
        "note": "DNS error — sous-domaine probablement supprimé. Domaine racine altios.com OK.",
    },
    "missionhandicap.fr": {
        "category": "dead",
        "subtype": "timeout",
        "strategy": "retry_root_domain",
        "url_override": "https://www.missionhandicap.fr",
        "note": "Timeout. Essayer domaine racine.",
    },
    "glassdoor.fr": {
        "category": "dead",
        "subtype": "agregateur",
        "strategy": "skip_agregateur",
        "url_override": None,
        "note": "Agrégateur — pas de compte candidat individuel. Ignorer.",
    },
    "apec.fr": {
        "category": "dead",
        "subtype": "agregateur",
        "strategy": "skip_agregateur",
        "url_override": None,
        "note": "APEC — agrégateur. Pas dans le scope création de compte entreprise.",
    },
    "linkfinance.fr": {
        "category": "dead",
        "subtype": "agregateur",
        "strategy": "skip_agregateur",
        "url_override": None,
        "note": "Agrégateur finance. Pas de compte candidat entreprise.",
    },
    "bgl.lu": {
        "category": "dead",
        "subtype": "timeout",
        "strategy": "retry_root_domain",
        "url_override": "https://www.bgl.lu",
        "note": "Timeout. Essayer domaine racine.",
    },
    "bil.com": {
        "category": "dead",
        "subtype": "timeout",
        "strategy": "retry_root_domain",
        "url_override": "https://www.bil.com",
        "note": "Timeout. Essayer domaine racine.",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# MAPPING COMPLET : toutes les 62 entrées
# ──────────────────────────────────────────────────────────────────────────────
ALL_SITE_STRATEGIES: dict[str, dict[str, Any]] = {}
ALL_SITE_STRATEGIES.update(CAT1_BLOCKED)
ALL_SITE_STRATEGIES.update(CAT2_ATS)
ALL_SITE_STRATEGIES.update(CAT3_NO_SPACE)
ALL_SITE_STRATEGIES.update(CAT4_DEAD)


def get_strategy(domain: str) -> dict[str, Any] | None:
    """Retourne la stratégie pour un domaine donné. None si pas trouvé."""
    # Nettoyer le domaine
    clean = domain.lower().strip().replace("https://", "").replace("http://", "").rstrip("/")
    # Chercher correspondance exacte
    if clean in ALL_SITE_STRATEGIES:
        return ALL_SITE_STRATEGIES[clean]
    # Chercher correspondance 'contient' (sous-domaine)
    for key, val in ALL_SITE_STRATEGIES.items():
        if key in clean or clean in key:
            return val
    return None


def get_category(domain: str) -> str:
    """Retourne la catégorie: blocked, ats_external, no_space, dead, unknown."""
    s = get_strategy(domain)
    if s:
        return s.get("category", "unknown")
    return "unknown"


def get_sites_by_category(category: str) -> dict[str, dict[str, Any]]:
    """Retourne tous les sites d'une catégorie donnée."""
    return {k: v for k, v in ALL_SITE_STRATEGIES.items() if v.get("category") == category}


# ──────────────────────────────────────────────────────────────────────────────
# JOB OFFER URLS pour les ATS externes (offres spécifiques à utiliser)
# ──────────────────────────────────────────────────────────────────────────────
ATS_JOB_URLS: dict[str, str] = {
    # SmartRecruiters: chercher sur Google "site:jobs.smartrecruiters.com ESG/Finance"
    "smartrecruiters_search": "https://jobs.smartrecruiters.com/",
    # BreezyHR: les pages carrières pointent vers des offres spécifiques
    "carbon4finance_breezy": "https://carbon4finance.breezy.hr/",
    "karmen_breezy": "https://karmen.breezy.hr/",
    # Teamtailor (sweep)
    "sweep_jobs": "https://careers.sweep.net/jobs",
    # Workday (carlyle)
    "carlyle_workday": "https://carlyle.wd5.myworkdayjobs.com/External",
}


# ──────────────────────────────────────────────────────────────────────────────
# JS FIXES pour les problèmes spécifiques
# ──────────────────────────────────────────────────────────────────────────────

# Bpifrance : fermer Didomi + attendre React
BPIFRANCE_DIDOMI_JS = r"""
(() => {
  // 1. Fermer la bannière Didomi (refuser)
  const didomiDisagree = document.querySelector('#didomi-notice-disagree-button');
  if (didomiDisagree) {
    didomiDisagree.click();
    return {done: 'didomi-rejected'};
  }
  // Fallback: chercher tout bouton Didomi refuser
  const btns = [...document.querySelectorAll('button')];
  for (const b of btns) {
    const t = (b.innerText || '').trim().toLowerCase();
    if (/(refuser|continuer sans accepter|ne pas accepter)/i.test(t)) {
      b.click();
      return {done: 'didomi-reject-fallback', label: t};
    }
  }
  return {done: 'no-didomi-found'};
})()
"""

# BPCE (BanquePostale, BanquePopulaire) : scanner les vrais noms d'inputs
BPCE_INPUT_JS = r"""
(() => {
  // Scanner TOUS les inputs visibles et retourner leurs attributs pour diagnostic
  const inputs = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button])')]
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 30 && r.height > 0; });
  const result = inputs.map(el => ({
    tag: el.tagName,
    type: el.type || 'text',
    name: el.name || '',
    id: el.id || '',
    placeholder: el.placeholder || '',
    ariaLabel: el.getAttribute('aria-label') || '',
    autocomplete: el.getAttribute('autocomplete') || '',
    className: (el.className || '').slice(0, 60),
    parentFormId: (el.closest('form') || {}).id || '',
    parentFormAction: (el.closest('form') || {}).action || '',
  }));
  // Détecter aussi les inputs dans les iframes
  const iframes = [...document.querySelectorAll('iframe')];
  for (const iframe of iframes) {
    try {
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      const frameInputs = [...doc.querySelectorAll('input:not([type=hidden]):not([type=submit])')]
        .filter(el => { const r = el.getBoundingClientRect(); return r.width > 30 && r.height > 0; });
      for (const el of frameInputs) {
        result.push({
          tag: 'IFRAME_INPUT',
          type: el.type || 'text',
          name: el.name || '',
          id: el.id || '',
          placeholder: el.placeholder || '',
          iframeSrc: iframe.src || '',
        });
      }
    } catch(e) {}
  }
  return { found: result.length, inputs: result };
})()
"""

# Engagement Jeunes : scanner les inputs spécifiques
ENGAGEMENT_JEUNES_JS = r"""
(() => {
  // Ce site utilise probablement des noms comme 'identifiant', 'motdepasse', etc.
  const inputs = [...document.querySelectorAll('input:not([type=hidden])')]
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 30 && r.height > 0; });
  const result = inputs.map(el => ({
    name: el.name || '',
    id: el.id || '',
    type: el.type || 'text',
    placeholder: el.placeholder || '',
    ariaLabel: el.getAttribute('aria-label') || '',
    autocomplete: el.getAttribute('autocomplete') || '',
  }));
  return { found: result.length, inputs: result };
})()
"""

# Meeschaert : chercher un endpoint register alternatif (candidature spontanée)
MEESCHAERT_REGISTER_FALLBACK_JS = r"""
(() => {
  // Stratégie : cliquer "Candidature spontanée" → ça ouvre un formulaire
  // qui peut servir de compte implicite
  const RE = /(candidature spontan[eé]e|postuler|nous rejoindre|rejoignez|d[eé]poser|candidater|apply)/i;
  const links = [...document.querySelectorAll('a[href], button, [role=button]')]
    .filter(el => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return false;
      const t = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim();
      return t && t.length < 100 && RE.test(t);
    });
  document.querySelectorAll('[data-wn-msreg]').forEach(e => e.removeAttribute('data-wn-msreg'));
  if (links.length > 0) {
    links[0].setAttribute('data-wn-msreg', '1');
    links[0].scrollIntoView({block: 'center'});
    return {
      found: true,
      label: (links[0].innerText || links[0].value || '').trim().slice(0, 60),
      total: links.length,
    };
  }
  return { found: false };
})()
"""


# ──────────────────────────────────────────────────────────────────────────────
# JS pour CAT 2 (ATS externes) : trouver la première offre d'emploi
# ──────────────────────────────────────────────────────────────────────────────
FIRST_JOB_OFFER_JS = r"""
(() => {
  const _deep = (root, acc) => {
    root.querySelectorAll('a[href]').forEach(e => acc.push(e));
    root.querySelectorAll('*').forEach(e => { if (e.shadowRoot) _deep(e.shadowRoot, acc); });
    return acc;
  };
  const JOB_HREF = /\/(jobs?|offre|emploi|career|poste|vacanc|position|opening|stelle|job-board|apply)\//i;
  const links = _deep(document, [])
    .filter(a => {
      const r = a.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return false;
      const href = (a.getAttribute('href') || '').toLowerCase();
      if (!href || href === '#' || href.startsWith('javascript:')) return false;
      if (/(linkedin|indeed|glassdoor|twitter|facebook|instagram)/.test(href)) return false;
      return JOB_HREF.test(href);
    });
  document.querySelectorAll('[data-wn-firstjob]').forEach(e => e.removeAttribute('data-wn-firstjob'));
  if (links.length > 0) {
    links[0].setAttribute('data-wn-firstjob', '1');
    links[0].scrollIntoView({block: 'center'});
    return {
      found: true,
      href: links[0].href,
      label: (links[0].innerText || '').trim().slice(0, 80),
      total_offers: links.length,
    };
  }
  return { found: false, total_offers: 0 };
})()
"""


# ── JS pour Cat 3 : après avoir cliqué une offre, détecter si apply = register ──
ATS_APPLY_REGISTER_DETECT_JS = r"""
(() => {
  const txt = (document.body ? document.body.innerText : '').slice(0, 15000).toLowerCase();
  const q = s => document.querySelector(s);
  const qa = s => [...document.querySelectorAll(s)];

  // Détecter formulaire avec email + nouveau mot de passe (register via apply)
  const hasEmail = qa('input[type=email], input[name*=email i], input[name*=mail i], input[placeholder*=email i], input[placeholder*=mail i]')
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0; }).length > 0;

  const hasNewPwd = qa('input[type=password]')
    .filter(el => {
      const name = ((el.name || '') + (el.id || '')).toLowerCase();
      const r = el.getBoundingClientRect();
      return r.width > 0 && !/confirm|verify/.test(name);
    }).length > 0;

  const hasConfirmPwd = qa('input[type=password]').length >= 2;

  const hasUpload = qa('input[type=file]').length > 0;

  // Mots-clés register dans le contexte apply
  const registerInApply = /(cr[eé]er (un |mon )?compte|s'?inscrire|register|sign ?up|create account|nouveau compte|first time|new (user|candidate|applicant))/i.test(txt);

  // Mots-clés apply-only (sans register)
  const applyOnly = /(postuler|candidater|apply now|submit application|envoyer|upload.*(cv|resume))/i.test(txt);

  // Mots-clés login
  const hasLogin = /(already have|d[eé]j[aà] (un )?compte|returning|sign ?in|log ?in|se connecter|connexion)/i.test(txt);

  let kind = 'unknown';
  if (hasEmail && hasNewPwd && registerInApply) kind = 'apply_register';
  else if (hasEmail && hasNewPwd) kind = 'apply_register_silent';  // register sans texte explicite
  else if (hasEmail && applyOnly && !hasNewPwd) kind = 'apply_only';  // pas de register
  else if (hasLogin && hasEmail) kind = 'login_or_register';
  else if (hasUpload) kind = 'upload_form';

  return {
    kind,
    hasEmail,
    hasNewPwd,
    hasConfirmPwd,
    hasUpload,
    registerInApply,
    hasLogin,
    applyOnly,
    passwordCount: qa('input[type=password]').length,
    emailCount: qa('input[type=email]').length,
  };
})()
"""


# ── JS pour Cat 4 : vérifier si le domaine racine est accessible ──
ROOT_DOMAIN_CHECK_JS = r"""
(() => {
  // Retourne les infos de la page courante pour diagnostic
  const title = document.title || '';
  const bodyText = (document.body ? document.body.innerText : '').slice(0, 500);
  const links = [...document.querySelectorAll('a[href]')]
    .filter(a => {
      const t = (a.innerText || '').trim();
      return t && /(carri[eè]re|recrut|emplo|job|career|talent|offre)/i.test(t) && t.length < 60;
    })
    .slice(0, 10)
    .map(a => ({ text: (a.innerText || '').trim().slice(0, 40), href: a.href }));
  const hasCareerLinks = links.length > 0;
  return {
    title: title.slice(0, 120),
    bodyPreview: bodyText.slice(0, 300),
    hasCareerLinks,
    careerLinks: links,
    url: location.href,
    status: document.readyState,
  };
})()
"""


# ── JS pour scanner les endpoints /login, /register, /signin dans la page ──
SITEMAP_PROBE_JS = r"""
(() => {
  const AUTH_PATTERNS = /\/(login|signin|signup|register|account|my-account|mon-compte|connexion|inscription|espace-candidat|espace-recrutement|candidate|applicant|auth)/i;
  const links = [...document.querySelectorAll('a[href]')]
    .filter(a => {
      const href = (a.getAttribute('href') || '').toLowerCase();
      return AUTH_PATTERNS.test(href) && !/(newsletter|subscribe|investor|press|media|blog|contact)/.test(href);
    })
    .map(a => ({
      text: (a.innerText || '').trim().slice(0, 50),
      href: a.getAttribute('href'),
      visible: (() => { const r = a.getBoundingClientRect(); return r.width > 0 && r.height > 0; })(),
    }));
  // Aussi chercher les liens dans le footer (souvent cachés)
  const footerLinks = [...(document.querySelector('footer') || document.body).querySelectorAll('a[href]')]
    .filter(a => AUTH_PATTERNS.test((a.getAttribute('href') || '').toLowerCase()))
    .map(a => ({ text: (a.innerText || '').trim().slice(0, 50), href: a.getAttribute('href') }));
  return { found: links.length, authLinks: links, footerAuthLinks: footerLinks };
})()
"""


# Exports pour import
__all__ = [
    "ALL_SITE_STRATEGIES",
    "get_strategy",
    "get_category",
    "get_sites_by_category",
    "CAT1_BLOCKED",
    "CAT2_ATS",
    "CAT3_NO_SPACE",
    "CAT4_DEAD",
    "ATS_JOB_URLS",
    "BPIFRANCE_DIDOMI_JS",
    "BPCE_INPUT_JS",
    "ENGAGEMENT_JEUNES_JS",
    "MEESCHAERT_REGISTER_FALLBACK_JS",
    "FIRST_JOB_OFFER_JS",
    "ATS_APPLY_REGISTER_DETECT_JS",
    "ROOT_DOMAIN_CHECK_JS",
    "SITEMAP_PROBE_JS",
]
