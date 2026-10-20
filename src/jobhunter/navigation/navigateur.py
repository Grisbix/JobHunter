"""Browser: standard Playwright only, typing helpers, robust loading, session.

Part of jobhunter.navigation (formerly Scripts/web_nav.py, phase 3.6).
"""

import random as _rnd
import re as _re_block
from typing import Any

# System browsers tried when Playwright's Chromium is not installed:
# the installed application (jobhunter.gele) does not ship it, and Edge is present on
# every Windows 10/11.
CANAUX_SYSTEME = ("chrome", "msedge")


def _manque_navigateur(e: Exception) -> bool:
    t = str(e).lower()
    return "executable doesn't exist" in t or "playwright install" in t


def lancer(chromium: Any, **options: Any) -> Any:
    """`chromium.launch(**options)`, then the system's Chrome or Edge if Chromium is missing.

    Args:
        chromium: `playwright.chromium`.
        **options: the `launch` options (headless, args…).

    Returns:
        The launched browser.

    Raises:
        Exception: the original error if no browser starts, or if the failure is not
            a missing browser.
    """
    try:
        return chromium.launch(**options)
    except Exception as e:
        if not _manque_navigateur(e) or options.get("channel"):
            raise
        for canal in CANAUX_SYSTEME:
            try:
                return chromium.launch(channel=canal, **options)
            except Exception:
                continue
        raise


def human_pause(page: Any, lo: int = 350, hi: int = 1100) -> None:
    """Fixed pause (average of lo and hi), so as not to hammer the site."""
    try:
        page.wait_for_timeout((lo + hi) // 2)
    except Exception:
        pass


def human_type(page: Any, selector: str, text: str, click_first: bool = True) -> bool:
    """Fills the field. Returns True if the field was found."""
    try:
        loc = page.locator(selector).first
        if click_first:
            loc.click(timeout=3000)
        loc.fill(str(text), timeout=3000)
        return True
    except Exception:
        return False


def human_click(page: Any, selector: str, steps: int | None = None, timeout: int = 4000) -> bool:
    """Clicks the element. Returns True if clicked."""
    try:
        page.locator(selector).first.click(timeout=timeout)
        return True
    except Exception:
        return False


def human_scroll(page: Any, steps: int | None = None) -> None:
    """Scrolls the page by a few screens."""
    for _ in range(steps or 3):
        try:
            page.mouse.wheel(0, 500)
            human_pause(page, 250, 800)
        except Exception:
            break


# ads/analytics/tags domains: useless for applying, they slow things down → blocked
_AD_RX = _re_block.compile(
    r"(doubleclick|googlesyndication|google-analytics|googletagmanager|/gtag/|/gtm\.js"
    r"|facebook\.net|connect\.facebook|hotjar|mouseflow|fullstory|segment\.(io|com)"
    r"|criteo|taboola|outbrain|adservice|adsystem|/pixel|/beacon|cdn\.cookielaw|onetrust)",
    _re_block.I,
)


# captcha/anti-bot: NEVER blocked (the human must SEE the image grid to solve it)
_CAPTCHA_OK_RX = _re_block.compile(
    r"(recaptcha|gstatic\.com/recaptcha|hcaptcha|turnstile|challenges\.cloudflare"
    r"|arkoselabs|funcaptcha|geo\.captcha|captcha-delivery)",
    _re_block.I,
)


def block_resources(ctx: Any, images: bool = False) -> None:
    """TURBO: drops heavy/useless requests (media, fonts, ads, analytics; images too if images=False).

    Speeds up loading 2-5×. CSS kept (layout/clicks). CAPTCHA resources always go
    through (otherwise invisible grid = unsolvable).
    """
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
    """Goto with retry + backoff on transient network/timeout errors.

    Returns {ok, status, note}. Does not bypass captcha (detected elsewhere).
    """
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
    """REMOVED. Hiding automation from the site (navigator.webdriver, WebGL fingerprint...) is an anti-bot bypass, against the project rules.

    Kept for the callers; does nothing.
    """
    return False


def available_engines() -> list[str]:
    """Installed engines: Playwright only."""
    try:
        import playwright.sync_api  # noqa: F401

        return ["playwright"]
    except Exception:
        return []


def get_sync_playwright(engine: str = "auto") -> tuple[Any, str]:
    """Returns (sync_playwright, "playwright"), whatever engine is."""
    from playwright.sync_api import sync_playwright

    return sync_playwright, "playwright"


class BrowserSession:
    """Manages the browser's life cycle with automatic recovery.

    Usage:
        bs = BrowserSession()
        page = bs.start()
        # ... if crash ...
        page = bs.recover()  # restarts browser + context + fresh page
    """

    def __init__(self, headless: bool = False, engine: str = "playwright") -> None:
        """Prepares the session without launching the browser (see `start`).

        Args:
            headless: browser without a window.
            engine: navigation engine (standard Playwright only).
        """
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
        """Launches the browser and returns the active page."""
        SyncPlaywright = self._get_playwright()
        self._playwright = SyncPlaywright().start()
        self._browser = lancer(
            self._playwright.chromium,
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
        """Checks whether the browser is still connected."""
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
        """Closes the page, the context, the browser and Playwright, without raising."""
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
