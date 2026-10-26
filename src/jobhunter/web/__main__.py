"""python -m jobhunter.web — opens the web interface prototype in a native window.

Needs the optional dependency: pip install "jobhunter[web]" (pywebview).
"""

from __future__ import annotations

import sys
from pathlib import Path

STATIC = Path(__file__).parent / "static"


def main() -> int:
    """Opens the window; returns 1 when pywebview is missing."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    try:
        import webview
    except ImportError:
        print('pywebview manque : python -m pip install "jobhunter[web]"')
        return 1
    from jobhunter.web.api import Api

    webview.create_window(
        "JobHunter",
        str(STATIC / "index.html"),
        js_api=Api(),
        width=1440,
        height=920,
        min_size=(1100, 720),
        maximized=True,
        background_color="#E6E2E0",
    )
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
