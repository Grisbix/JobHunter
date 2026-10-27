"""Opening the application: the web interface, the desktop one only as a fallback.

Since 3.29 the web window (jobhunter.web) is the application: every page of the desktop
one has moved there. The desktop window (jobhunter.app) opens only when the web view
cannot: pywebview missing from an older installation, or no WebView2 on the machine.
`jobhunter bureau` still opens it on purpose, for the guided application panel, which
the web window does not have (applying stays a desktop step, the final click yours).

JobHunter.pyw, `jobhunter app` and the compiled JobHunter.exe all come here.
JOBHUNTER_EXIGER_WEB=1 forbids the fallback: the installer's CI checks that the
compiled app really opens the web window, not the classic one in its place.
"""

from __future__ import annotations

import os
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
        if os.environ.get("JOBHUNTER_EXIGER_WEB"):
            raise
        print(f"interface web indisponible ({e}) : application de bureau", file=sys.stderr)
    else:
        if os.environ.get("JOBHUNTER_EXIGER_WEB"):
            return 2  # pywebview missing, and the fallback is forbidden
    from jobhunter.app.window import main as bureau

    bureau()
    return 0


if __name__ == "__main__":
    sys.exit(main())
