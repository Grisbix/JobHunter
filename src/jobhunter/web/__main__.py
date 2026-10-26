"""python -m jobhunter.web — opens the web interface prototype in a native window.

Needs the optional dependency: pip install "jobhunter[web]" (pywebview).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

STATIC = Path(__file__).parent / "static"

# DwmSetWindowAttribute codes (Windows 11).
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMWCP_DONOTROUND = 1
_DWMWCP_ROUND = 2
_SPI_GETWORKAREA = 0x0030
_SWP_NOZORDER = 0x0004
_SWP_FRAMECHANGED = 0x0020


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

    def _placer(self, plein: bool) -> None:
        import ctypes
        from ctypes import wintypes

        zone = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(_SPI_GETWORKAREA, 0, ctypes.byref(zone), 0)  # type: ignore[attr-defined,unused-ignore]
        lz, hz = zone.right - zone.left, zone.bottom - zone.top
        if plein:
            x, y, lg, ht = zone.left, zone.top, lz, hz
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

    def installer(self) -> None:
        """The saved backdrop behind the transparent page, then the full size.

        The page is drawn on a transparent WebView2; the form is painted black, which
        DWM treats as "show the backdrop" once the frame covers the client area.
        """
        if sys.platform != "win32":
            return
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
            self._placer(True)
        except Exception as e:  # noqa: BLE001 — cosmetic only
            print(f"cadre : {e}")

    def fond(self, nom: str) -> None:
        """Acrylic, mica or no backdrop (FONDS), at start and from the settings screen."""
        from jobhunter.web.api import FONDS

        if not self.hwnd:
            return
        try:
            self._attribut(_DWMWA_SYSTEMBACKDROP_TYPE, FONDS.get(nom, FONDS["acrylique"]))
        except Exception as e:  # noqa: BLE001 — cosmetic only
            print(f"cadre : {e}")

    def basculer(self) -> None:
        """Full screen <-> rounded window (title bar button, double click)."""
        if not self.hwnd:
            return
        try:
            self._placer(not self.plein)
        except Exception as e:  # noqa: BLE001 — cosmetic only
            print(f"cadre : {e}")


def main() -> int:
    """Opens the window; returns 1 when pywebview is missing."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    try:
        import webview
    except ImportError:
        print('pywebview manque : python -m pip install "jobhunter[web]"')
        return 1
    from jobhunter.profiles import appliquer

    appliquer()  # the active profile, before any module builds its paths (as the desktop)
    from jobhunter.web.api import Api

    api = Api()
    fenetre = webview.create_window(
        "JobHunter",
        str(STATIC / "index.html"),
        js_api=api,
        width=1280,
        height=800,
        min_size=(900, 560),
        frameless=True,
        easy_drag=False,
        transparent=True,
    )
    cadre = _Cadre(fenetre)
    api._fenetre = fenetre
    api._basculer = cadre.basculer
    api._fond = cadre.fond
    fenetre.events.shown += cadre.installer
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
