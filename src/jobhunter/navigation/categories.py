"""Strategies par categorie de site (tableaux de navigation/strategies.py).

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6)."""

from typing import Any

from jobhunter.navigation.strategies import (
    ATS_APPLY_REGISTER_DETECT_JS,
    BPCE_INPUT_JS,
    BPIFRANCE_DIDOMI_JS,
    FIRST_JOB_OFFER_JS,
    ROOT_DOMAIN_CHECK_JS,
    SITEMAP_PROBE_JS,
)


def click_first_job_offer(page: Any) -> Any:
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


def check_apply_for_register(page: Any) -> Any:
    """Cat2/3 : apres avoir clique une offre, verifie si le flux apply
    inclut une creation de compte (email + password demandes).
    Retour {kind, hasEmail, hasNewPwd, ...}."""
    try:
        return page.evaluate(ATS_APPLY_REGISTER_DETECT_JS)
    except Exception:
        return {"kind": "error"}


def probe_auth_endpoints(page: Any) -> Any:
    """Cat3 : scanne les liens /login, /register, /signin dans la page.
    Retour {found, authLinks, footerAuthLinks}."""
    try:
        return page.evaluate(SITEMAP_PROBE_JS)
    except Exception:
        return {"found": 0, "authLinks": [], "footerAuthLinks": []}


def check_root_domain(page: Any) -> Any:
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


def didomi_reject_and_wait(page: Any, wait_ms: int = 12000) -> Any:
    """Ferme la banniere Didomi (Bpifrance) et attend le chargement React.
    Retour {done, ...}."""
    try:
        r = page.evaluate(BPIFRANCE_DIDOMI_JS)
    except Exception:
        r = {"done": "err"}
    page.wait_for_timeout(wait_ms)
    return r


def scan_nonstandard_inputs(page: Any) -> Any:
    """Scan les inputs non-standards (BPCE, Engagement Jeunes) pour diagnostic.
    Retour {found, inputs}."""
    try:
        return page.evaluate(BPCE_INPUT_JS)
    except Exception:
        return {"found": 0, "inputs": []}
