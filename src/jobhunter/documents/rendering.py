"""Conversion .docx -> .pdf (LibreOffice).

Partie de jobhunter.documents (ancien Scripts/tailor_application.py, phase 3.5).
"""

import shutil
import subprocess
from pathlib import Path

from jobhunter import log as _journal

_log = _journal.journal(__name__)


# ---- PDF via LibreOffice ----
# Windows, then macOS, then whatever the PATH holds (Linux: /usr/bin/soffice). The
# Windows paths alone left every macOS and Linux installation without a PDF, the CV
# and letter going out as .docx (measured 2026-10-24, LibreOffice installed).
SOFFICE = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
] + [x for x in (shutil.which("soffice"), shutil.which("libreoffice")) if x]


def soffice() -> str | None:
    """The LibreOffice program found on this computer, None if none."""
    return next((s for s in SOFFICE if Path(s).exists()), None)


def pages_png(pdf: Path, largeur: int = 1100, maximum: int = 4) -> list[bytes]:
    """The PDF's first pages as PNG, `largeur` pixels wide.

    The window shows these pictures rather than the PDF itself: the web view's PDF
    reader is not always there (the user, 2026-11-02: « prévisualiser la version pdf
    depuis l'app sans ouvrir word »). [] if the file cannot be read.
    """
    try:
        import pymupdf

        with pymupdf.open(str(pdf)) as doc:
            images = []
            for page in list(doc)[:maximum]:
                zoom = largeur / max(page.rect.width, 1)
                images.append(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png"))
            return images
    except Exception as e:  # noqa: BLE001 — a picture missing is not an error
        _log.warning(f"  ! aperçu PDF impossible : {e}")
        return []


def to_pdf(docx_path: Path) -> Path | None:
    """Converts a .docx to PDF through LibreOffice, next to the file.

    Args:
        docx_path: the Word document.

    Returns:
        The path of the PDF, or None if LibreOffice is missing or failed.
    """
    exe = soffice()
    if not exe:
        return None
    try:
        subprocess.run(
            [
                exe,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(docx_path.parent),
                str(docx_path),
            ],
            check=True,
            capture_output=True,
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # no console flash
        )
        return docx_path.with_suffix(".pdf")
    except Exception as e:  # noqa: BLE001
        _log.warning(f"  ! PDF échec: {e}")
        return None
