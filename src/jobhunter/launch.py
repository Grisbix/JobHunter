"""Opening the application: the web interface.

Since 3.29 the web window (jobhunter.web) is the application; the desktop window
(customtkinter) it replaced was removed in 3.77, guided application included
(jobhunter.web.guided). When the web view cannot open (pywebview missing, no WebView2),
the launcher says so and how to fix it, instead of opening another window. Without a
profile the window shows the welcome (jobhunter.web.onboarding, 3.78).

JobHunter.pyw, `jobhunter app` and the compiled JobHunter.exe all come here.

Decision: docs/adr/0017-desktop-window-removed.md
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Opens the web window; without a profile it shows the welcome (3.78)."""
    from jobhunter.profiles import appliquer

    appliquer()  # the active profile, before any module builds its paths
    _migrer()
    try:
        from jobhunter.web.__main__ import main as web

        if web() == 0:
            return 0
        raison = "pywebview n'est pas installé"
    except Exception as e:  # noqa: BLE001 — said below, in a window: there is no console
        if os.environ.get("JOBHUNTER_EXIGER_WEB"):
            raise
        raison = str(e)
    if os.environ.get("JOBHUNTER_EXIGER_WEB"):
        return 2  # the installer's CI: the web window must open, nothing else
    _dire_pourquoi(raison)
    return 1


def _migrer() -> None:
    """A 2.x folder takes the 3.0 names before the window opens.

    Its sentence is shown by the page (JH_MIGRATION, jobhunter.web.onboarding).
    """
    from jobhunter.welcome import migrer_si_besoin

    try:
        message = migrer_si_besoin()
    except RuntimeError:  # no data folder at all: the welcome makes one
        return
    if message:
        os.environ["JH_MIGRATION"] = message


def _dire_pourquoi(raison: str) -> None:
    """The window could not open: says why, in a dialog (JobHunter.pyw has no console)."""
    texte = (
        f"La fenêtre de JobHunter n'a pas pu s'ouvrir : {raison}.\n\n"
        "Réinstalle les dépendances (install.bat, ou pip install --upgrade jobhunter), "
        "et sous Windows le runtime Microsoft Edge WebView2."
    )
    print(texte, file=sys.stderr)  # noqa: T201
    try:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        messagebox.showerror("JobHunter", texte, parent=racine)
        racine.destroy()
    except Exception:  # noqa: BLE001 — no display either: the message went to stderr
        pass


if __name__ == "__main__":
    sys.exit(main())
