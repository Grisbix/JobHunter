"""Opening the application: the web interface, the desktop one only as a fallback.

Since 3.29 the web window (jobhunter.web) is the application: every page of the desktop
one has moved there. The desktop window (jobhunter.app) opens only when the web view
cannot: pywebview missing from an older installation, or no WebView2 on the machine.
`jobhunter bureau` still opens it on purpose, for the guided application panel, which
the web window does not have (applying stays a desktop step, the final click yours).

JobHunter.pyw, `jobhunter app` and the compiled JobHunter.exe all come here.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Ensures the profile, then opens the web window, else the desktop one."""
    from jobhunter.profiles import appliquer

    appliquer()  # the active profile, before any module builds its paths
    from jobhunter.welcome import assurer_profil

    assurer_profil()
    try:
        from jobhunter.web.__main__ import main as web

        if web() == 0:
            return 0
    except Exception as e:  # noqa: BLE001 — no web view here: the desktop window instead
        print(f"interface web indisponible ({e}) : application de bureau", file=sys.stderr)
    from jobhunter.app.window import main as bureau

    bureau()
    return 0


if __name__ == "__main__":
    sys.exit(main())
