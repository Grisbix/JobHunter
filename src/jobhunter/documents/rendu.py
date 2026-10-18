"""Conversion .docx -> .pdf (LibreOffice).

Partie de jobhunter.documents (ancien Scripts/tailor_application.py, phase 3.5)."""

import subprocess
from pathlib import Path

# ---- PDF via LibreOffice ----
SOFFICE = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


def to_pdf(docx_path):
    exe = next((s for s in SOFFICE if Path(s).exists()), None)
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
        )
        return docx_path.with_suffix(".pdf")
    except Exception as e:
        print(f"  ! PDF échec: {e}")
        return None
