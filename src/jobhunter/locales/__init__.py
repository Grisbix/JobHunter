"""The interface texts in English, German and Spanish, indexed by the French text.

One module per language (`NOM`, `RELANCER`, `TEXTES`, `JOURNAL`, `SORTIE`, `FIT`).
They import nothing: the desktop window (jobhunter.app.language) and the web one
(jobhunter.web.i18n) both read them, and the web one may not import jobhunter.app.
"""


def systeme() -> str:
    """The system's language, when it is one the interface speaks; English otherwise.

    The interface language until the user chooses one: a first start in Ohio is in
    English, in Lyon in French. Windows says it by its UI language, others by `LANG`.
    """
    import os
    import sys

    code = ""
    if sys.platform == "win32":
        try:
            import ctypes

            # Primary language of the LANGID: 0x0c French, 0x07 German, 0x0a Spanish.
            principal = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            code = {0x0C: "fr", 0x09: "en", 0x07: "de", 0x0A: "es"}.get(principal, "")
        except (AttributeError, OSError):
            code = ""
    if not code:
        import locale

        brut = os.environ.get("LC_ALL") or os.environ.get("LANG") or (locale.getlocale()[0] or "")
        code = brut[:2].lower()
    return code if code in ("fr", "en", "de", "es") else "en"
