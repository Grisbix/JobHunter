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
_DWMWCP_ROUND = 2
_DWMSBT_TRANSIENTWINDOW = 3  # acrylic: the wallpaper, blurred, behind the window


def _vitre(fenetre: Any) -> None:
    """Rounded corners and acrylic backdrop behind the transparent page (Windows 11).

    The page is drawn on a transparent WebView2; the form is painted black, which DWM
    treats as "show the backdrop" once the frame is extended over the whole client
    area. Anything failing here only leaves a plain window: never fatal.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        forme = fenetre.native
        hwnd = forme.Handle.ToInt32()
        dwm = ctypes.windll.dwmapi

        def attribut(code: int, valeur: int) -> None:
            v = ctypes.c_int(valeur)
            dwm.DwmSetWindowAttribute(hwnd, code, ctypes.byref(v), ctypes.sizeof(v))

        class Marges(ctypes.Structure):
            _fields_ = [(n, ctypes.c_int) for n in ("g", "d", "h", "b")]

        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(Marges(-1, -1, -1, -1)))
        attribut(_DWMWA_USE_IMMERSIVE_DARK_MODE, 0)
        attribut(_DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_ROUND)
        attribut(_DWMWA_SYSTEMBACKDROP_TYPE, _DWMSBT_TRANSIENTWINDOW)

        from System import Action
        from System.Drawing import Color

        forme.Invoke(Action(lambda: setattr(forme, "BackColor", Color.Black)))
    except Exception as e:  # noqa: BLE001 — cosmetic only
        print(f"vitre : {e}")


def main() -> int:
    """Opens the window; returns 1 when pywebview is missing."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    try:
        import webview
    except ImportError:
        print('pywebview manque : python -m pip install "jobhunter[web]"')
        return 1
    from jobhunter.web.api import Api

    api = Api()
    # Large but not maximized: Windows squares the corners of a maximized window.
    ecran = webview.screens[0] if webview.screens else None
    largeur = min(1600, ecran.width - 32) if ecran else 1440
    hauteur = min(1000, ecran.height - 72) if ecran else 920
    fenetre = webview.create_window(
        "JobHunter",
        str(STATIC / "index.html"),
        js_api=api,
        width=largeur,
        height=hauteur,
        x=(ecran.width - largeur) // 2 if ecran else None,
        y=max(0, (ecran.height - hauteur) // 2 - 20) if ecran else None,
        min_size=(1100, 720),
        frameless=True,
        easy_drag=False,
        transparent=True,
    )
    api._fenetre = fenetre
    fenetre.events.shown += lambda: _vitre(fenetre)
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
