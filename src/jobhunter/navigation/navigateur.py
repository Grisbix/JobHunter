"""Navigateur : Playwright standard seul, aides de saisie, chargement robuste, session.

Partie de jobhunter.navigation (ancien Scripts/web_nav.py, phase 3.6)."""

import random as _rnd
import re as _re_block
from typing import Any


def human_pause(page: Any, lo: int = 350, hi: int = 1100) -> None:
    """Pause fixe (moyenne de lo et hi), pour ne pas marteler le site."""
    try:
        page.wait_for_timeout((lo + hi) // 2)
    except Exception:
        pass


def human_type(page: Any, selector: str, text: str, click_first: bool = True) -> bool:
    """Remplit le champ. Retour True si champ trouve."""
    try:
        loc = page.locator(selector).first
        if click_first:
            loc.click(timeout=3000)
        loc.fill(str(text), timeout=3000)
        return True
    except Exception:
        return False


def human_click(page: Any, selector: str, steps: int | None = None, timeout: int = 4000) -> bool:
    """Clique l'element. Retour True si clique."""
    try:
        page.locator(selector).first.click(timeout=timeout)
        return True
    except Exception:
        return False


def human_scroll(page: Any, steps: int | None = None) -> None:
    """Fait defiler la page de quelques ecrans."""
    for _ in range(steps or 3):
        try:
            page.mouse.wheel(0, 500)
            human_pause(page, 250, 800)
        except Exception:
            break


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


def block_resources(ctx: Any, images: bool = False) -> None:
    """TURBO : abandonne les requêtes lourdes/inutiles (media, fonts, pubs, analytics ;
    images aussi si images=False). Accélère 2-5× le chargement. CSS gardé (layout/clics).
    Les ressources CAPTCHA passent toujours (sinon grille invisible = insoluble)."""
    heavy = {"media", "font"} | (set() if images else {"image"})

    def _route(route: Any) -> Any:
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


def robust_goto(
    page: Any, url: str, tries: int = 3, wait_until: str = "domcontentloaded"
) -> dict[str, Any]:
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


def apply_stealth(context_or_page: Any) -> bool:
    """RETIRE. Masquer l'automatisation au site (navigator.webdriver, empreinte
    WebGL...) est un contournement anti-bot, contraire aux regles du projet.
    Garde pour les appelants ; ne fait rien."""
    return False


def available_engines() -> list[str]:
    """Moteurs installes : Playwright seul."""
    try:
        import playwright.sync_api  # noqa: F401

        return ["playwright"]
    except Exception:
        return []


def get_sync_playwright(engine: str = "auto") -> tuple[Any, str]:
    """Retourne (sync_playwright, "playwright"), quel que soit engine."""
    from playwright.sync_api import sync_playwright

    return sync_playwright, "playwright"


class BrowserSession:
    """Gère le cycle de vie du navigateur avec recovery automatique.

    Usage:
        bs = BrowserSession()
        page = bs.start()
        # ... si crash ...
        page = bs.recover()  # relance navigateur + contexte + page fluo
    """

    def __init__(self, headless: bool = False, engine: str = "playwright") -> None:
        self.headless = headless
        self.engine = engine
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._crashed = False

    def _get_playwright(self) -> Any:
        sp, self.engine = get_sync_playwright(self.engine)
        return sp

    def start(self) -> Any:
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

    def recover(self) -> Any:
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

    def close(self) -> None:
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
