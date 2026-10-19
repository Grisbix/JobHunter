"""Strategies per site category (tables in navigation/strategies.py).

Part of jobhunter.navigation (formerly Scripts/web_nav.py, phase 3.6).
"""

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
    """Cat2/3: finds and clicks the first job offer on the page.

    Returns {found, href, label, total_offers}.
    """
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
    """Cat2/3: after clicking an offer, checks whether the apply flow includes an account creation (email + password asked).

    Returns {kind, hasEmail, hasNewPwd, ...}.
    """
    try:
        return page.evaluate(ATS_APPLY_REGISTER_DETECT_JS)
    except Exception:
        return {"kind": "error"}


def probe_auth_endpoints(page: Any) -> Any:
    """Cat3: scans the /login, /register, /signin links in the page.

    Returns {found, authLinks, footerAuthLinks}.
    """
    try:
        return page.evaluate(SITEMAP_PROBE_JS)
    except Exception:
        return {"found": 0, "authLinks": [], "footerAuthLinks": []}


def check_root_domain(page: Any) -> Any:
    """Cat4: checks whether the root domain is reachable and has career links.

    Returns {title, bodyPreview, hasCareerLinks, careerLinks, url, status}.
    """
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
    """Closes the Didomi banner (Bpifrance) and waits for React to load.

    Returns {done, ...}.
    """
    try:
        r = page.evaluate(BPIFRANCE_DIDOMI_JS)
    except Exception:
        r = {"done": "err"}
    page.wait_for_timeout(wait_ms)
    return r


def scan_nonstandard_inputs(page: Any) -> Any:
    """Scans the non-standard inputs (BPCE, Engagement Jeunes) for diagnostics.

    Returns {found, inputs}.
    """
    try:
        return page.evaluate(BPCE_INPUT_JS)
    except Exception:
        return {"found": 0, "inputs": []}
