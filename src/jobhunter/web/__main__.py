"""python -m jobhunter.web — opens the web interface prototype in a native window.

Needs the optional dependency: pip install "jobhunter[web]" (pywebview).
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

STATIC = Path(__file__).parent / "static"
# The application's icon file (jobhunter/assets, also used by the shortcut and the welcome).
ICONE = Path(__file__).parents[1] / "assets" / "jobhunter.ico"

# DwmSetWindowAttribute codes (Windows 11).
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMWCP_DONOTROUND = 1
_DWMWCP_ROUND = 2
_SPI_GETWORKAREA = 0x0030
_SWP_NOZORDER = 0x0004
_SWP_FRAMECHANGED = 0x0020
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010
_HWND_TOPMOST = -1


def _rect(texte: str) -> tuple[int, int, int, int] | None:
    """JH_RECT, "x,y,w,h" set by a profile switch, as a tuple; None when malformed."""
    try:
        x, y, lg, ht = (int(v) for v in texte.split(","))
    except ValueError:
        return None
    return x, y, lg, ht


class _Cadre:
    """The two sizes of the frameless window, drawn by hand on Windows 11.

    The system "maximize" misplaces a frameless WinForms window (it keeps its
    position and overflows the screen), so: full = the work area (taskbar left
    visible), square corners; windowed = 90 % of it, centred, rounded corners.
    Anything failing here only leaves a plain window: never fatal.
    """

    def __init__(self, fenetre: Any) -> None:
        self.fenetre = fenetre
        self.hwnd = 0
        self.plein = False

    def _attribut(self, code: int, valeur: int) -> None:
        import ctypes

        v = ctypes.c_int(valeur)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined,unused-ignore]
            self.hwnd, code, ctypes.byref(v), ctypes.sizeof(v)
        )

    def rect(self) -> tuple[int, int, int, int] | None:
        """The window's place and size (x, y, width, height), for the next window."""
        import ctypes
        from ctypes import wintypes

        if not self.hwnd:
            return None
        r = wintypes.RECT()
        if not ctypes.windll.user32.GetWindowRect(self.hwnd, ctypes.byref(r)):  # type: ignore[attr-defined,unused-ignore]
            return None
        return r.left, r.top, r.right - r.left, r.bottom - r.top

    def devant(self) -> None:
        """Above every window until it closes: a profile switch opens the next one under it."""
        import ctypes

        if self.hwnd:
            # As pointers: a bare -1 goes as a 32-bit int, not as HWND_TOPMOST on 64 bits,
            # and the call failed silently (the new window opened over this one).
            ctypes.windll.user32.SetWindowPos(  # type: ignore[attr-defined,unused-ignore]
                ctypes.c_void_p(self.hwnd),
                ctypes.c_void_p(_HWND_TOPMOST),
                0,
                0,
                0,
                0,
                _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE,
            )

    def _placer(self, plein: bool, rect: tuple[int, int, int, int] | None = None) -> None:
        import ctypes
        from ctypes import wintypes

        zone = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(_SPI_GETWORKAREA, 0, ctypes.byref(zone), 0)  # type: ignore[attr-defined,unused-ignore]
        lz, hz = zone.right - zone.left, zone.bottom - zone.top
        if plein:
            x, y, lg, ht = zone.left, zone.top, lz, hz
            # A window exactly the size of the monitor (taskbar hidden: the work area
            # is the whole screen) counts as full screen for DWM, which then drops
            # acrylic and mica for a flat grey: every backdrop looked the same. One
            # pixel short keeps them (the user, 2026-10-27).
            if (lz, hz) == (
                ctypes.windll.user32.GetSystemMetrics(0),  # type: ignore[attr-defined,unused-ignore]
                ctypes.windll.user32.GetSystemMetrics(1),  # type: ignore[attr-defined,unused-ignore]
            ):
                ht -= 1
        elif rect and rect[2] >= 900 and rect[3] >= 560:
            x, y, lg, ht = rect  # where the previous window was (a profile switch)
        else:
            lg, ht = int(lz * 0.9), int(hz * 0.9)
            x, y = zone.left + (lz - lg) // 2, zone.top + (hz - ht) // 2
        self._attribut(
            _DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_DONOTROUND if plein else _DWMWCP_ROUND
        )
        ctypes.windll.user32.SetWindowPos(  # type: ignore[attr-defined,unused-ignore]
            self.hwnd, 0, x, y, lg, ht, _SWP_NOZORDER | _SWP_FRAMECHANGED
        )
        self.plein = plein

    def icone(self) -> None:
        """JobHunter's icon on the window and its taskbar entry, not Python's."""
        try:
            from System import Action
            from System.Drawing import Icon

            forme = self.fenetre.native
            forme.Invoke(Action(lambda: setattr(forme, "Icon", Icon(str(ICONE)))))
        except Exception as e:  # noqa: BLE001 — cosmetic only
            print(f"icône : {e}")  # noqa: T201

    def installer(self) -> None:
        """The saved backdrop behind the transparent page, then the full size.

        The page is drawn on a transparent WebView2; the form is painted black, which
        DWM treats as "show the backdrop" once the frame covers the client area.
        """
        if sys.platform != "win32":
            return
        self.icone()
        try:
            import ctypes

            forme = self.fenetre.native
            self.hwnd = forme.Handle.ToInt32()

            class Marges(ctypes.Structure):
                _fields_ = [(n, ctypes.c_int) for n in ("g", "d", "h", "b")]

            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
                self.hwnd, ctypes.byref(Marges(-1, -1, -1, -1))
            )
            self._attribut(_DWMWA_USE_IMMERSIVE_DARK_MODE, 0)
            from jobhunter.web.api import lire_reglages

            self.fond(lire_reglages()["fond"])

            from System import Action
            from System.Drawing import Color

            forme.Invoke(Action(lambda: setattr(forme, "BackColor", Color.Black)))
            # Opened by a profile switch: the size and place the previous window had.
            plein = os.environ.pop("JH_PLEIN", "1") != "0"
            self._placer(plein, _rect(os.environ.pop("JH_RECT", "")))
        except Exception as e:  # noqa: BLE001 — cosmetic only
            print(f"cadre : {e}")  # noqa: T201

    def fond(self, nom: str) -> None:
        """Acrylic, mica or no backdrop (FONDS), at start and from the settings screen."""
        from jobhunter.web.api import FONDS

        if not self.hwnd:
            return
        try:
            self._attribut(_DWMWA_SYSTEMBACKDROP_TYPE, FONDS.get(nom, FONDS["acrylique"]))
        except Exception as e:  # noqa: BLE001 — cosmetic only
            print(f"cadre : {e}")  # noqa: T201

    def basculer(self) -> None:
        """Full screen <-> rounded window (title bar button, double click)."""
        if not self.hwnd:
            return
        try:
            self._placer(not self.plein)
        except Exception as e:  # noqa: BLE001 — cosmetic only
            print(f"cadre : {e}")  # noqa: T201


def _depot_cv(fenetre: Any) -> None:
    """The welcome's drop zone: a file dropped on the window goes to the page by its path.

    The page only sees a dropped file's name; pywebview gives its full path to Python
    (`pywebviewFullPath`), which hands it to the page's `cvDepose`.
    """
    try:
        from webview.dom import DOMEventHandler
    except ImportError:  # an older pywebview: the « Choisir mon CV… » button remains
        return

    def deposer(e: dict[str, Any]) -> None:
        fichiers = (e.get("dataTransfer") or {}).get("files") or []
        chemins = [str(f.get("pywebviewFullPath") or "") for f in fichiers if isinstance(f, dict)]
        chemin = next((c for c in chemins if c), "")
        if chemin:
            fenetre.evaluate_js(f"cvDepose({json.dumps(chemin)})")

    try:
        fenetre.dom.document.events.drop += DOMEventHandler(deposer, True, True)
    except Exception:  # noqa: BLE001 — no drop, the button remains
        pass


def main() -> int:
    """Opens the window; returns 1 when pywebview is missing."""
    # Without a console (pythonw.exe, the windowed JobHunter.exe) sys.stdout is None:
    # reconfiguring it failed, and the compiled app fell back to the classic window.
    # A null sink, as the desktop's main(), for every module that writes to it.
    for nom in ("stdout", "stderr"):
        if getattr(sys, nom) is None:
            setattr(sys, nom, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    from jobhunter import root

    root.exporter_paquet()  # the programs it starts run `python -m jobhunter...` (as the desktop)
    if sys.platform == "win32":
        # Its own taskbar entry, under JobHunter's icon, not python(w).exe's (as the desktop).
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Grisbix.JobHunter")
        except (AttributeError, OSError):
            pass
    try:
        import webview
    except ImportError:
        print('pywebview manque : python -m pip install "jobhunter[web]"')  # noqa: T201
        return 1
    from jobhunter.profiles import appliquer

    appliquer()  # the active profile, before any module builds its paths (as the desktop)
    from jobhunter.web.api import Api

    api = Api()
    from jobhunter import welcome

    if welcome.a_un_profil():  # without one, the welcome first (web.onboarding)
        api.demarrer_fond()  # the desktop's background work (web.background)
        # The first screen's data, read while WebView2 starts.
        threading.Thread(target=api._prechauffer, daemon=True).start()
    # The Start menu shortcut, once: pinned, the window keeps JobHunter's logo (shortcut.py).
    from jobhunter.programs import shortcut

    threading.Thread(target=shortcut.assurer, daemon=True).start()
    from jobhunter.programs import sandbox

    fenetre = webview.create_window(
        "JobHunter — bac à sable" if sandbox.actif() else "JobHunter",
        (STATIC / "index.html").as_uri(),
        js_api=api,
        width=1280,
        height=800,
        min_size=(900, 560),
        frameless=True,
        easy_drag=False,
        transparent=True,
    )
    if fenetre is None:  # pywebview gives no window: the desktop one opens instead
        return 1
    cadre = _Cadre(fenetre)
    api._fenetre = fenetre
    api._basculer = cadre.basculer
    from jobhunter import frozen

    if frozen.paquet_msix():
        # The Store's update closes the window; Windows opens it again after (3.74).
        from jobhunter import store_update

        store_update.redemarrer_apres_maj()
    api._plein = lambda: cadre.plein
    api._rect = cadre.rect
    api._devant = cadre.devant
    api._toile = cadre.fond
    fenetre.events.shown += cadre.installer
    if not welcome.a_un_profil():
        fenetre.events.loaded += lambda: _depot_cv(fenetre)
    api._relais = os.environ.pop("JH_RELAIS", "")
    if api._relais:
        # Opened by a profile switch, under the previous window: that one closes once
        # this page says its first screen is drawn (Api.affiche). A page that never says
        # so still takes over a few seconds after loading.
        def secours() -> None:
            import time

            time.sleep(6)
            api.affiche()

        fenetre.events.loaded += secours
    # The icon from the window's creation: set at "shown", the taskbar first showed
    # pythonw.exe's, Python's logo (the user, 2026-10-28).
    webview.start(icon=str(ICONE if sys.platform == "win32" else ICONE.with_suffix(".png")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
