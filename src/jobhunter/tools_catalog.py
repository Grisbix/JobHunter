"""The "Outils" menu, shared by the desktop application and the web interface.

One list, read by both: before 3.27 the desktop kept it in `app.common.MAINT` and the
web interface had to copy it, so a tool added to one was missing from the other.

Each tool is `(label, what)`: `what` is the module and its arguments (run with the
interpreter's `-m`), or the name of an action the interface opens itself
(`ACTIONS`). Labels are French, the key of the interface's translations.
"""

from __future__ import annotations

# Grouped by INTENT: one looks for "where are my offers going", not a script name.
OUTILS: list[tuple[str, list[tuple[str, list[str] | str]]]] = [
    (
        "Sources & offres",
        [
            ("Scrape les sites", ["jobhunter.programs.scrape_jobs", "--headless"]),
            ("Homepages", ["jobhunter.programs.enrich_homepages"]),
            # The daily scan only sees 7 days (LinkedIn f_TPR filter). An
            # offer published at the start of the month and missed at the time stays
            # invisible without this wider pass.
            ("Rattrapage 31 j", ["jobhunter.sources", "--all", "--days", "31"]),
            ("Sonder flux ATS", ["jobhunter.programs.probe_ats"]),
            ("Sonder flux Workday", ["jobhunter.programs.probe_workday"]),
            (
                "Sonder mots-clés",
                ["jobhunter.programs.probe_keywords", "--days", "30", "--min-new", "3"],
            ),
        ],
    ),
    (
        "Documents",
        [
            ("CV/lettres…", "documents"),  # which offers: chosen in a dialog
            ("Documents à comparer…", "comparer"),  # retouched vs regenerated (app.compare)
            ("Sync docs+format", ["jobhunter.programs.sync_docs", "--format"]),
            ("Export CSV", ["jobhunter.programs.export_queue_csv", "--keep", "8"]),
            ("Relire les lettres", ["jobhunter.programs.proofread_letters"]),
            ("Contrôler les dossiers", ["jobhunter.programs.check_folders"]),
        ],
    ),
    (
        "Hygiène de la file",
        [
            ("URLs mortes", ["jobhunter.programs.queue_tools", "mark"]),
            (
                "Recheck 404",
                ["jobhunter.programs.recheck_dead", "--status", "OK", "--limit", "120"],
            ),
            ("Re-score", ["jobhunter.programs.rescore_ats"]),
            ("Recettes de nettoyage…", "recettes"),  # normalisation rules (app.recipes)
        ],
    ),
    (
        "Suivi",
        [
            ("Relances", ["jobhunter.programs.follow_ups"]),
            ("Alerte matchs", ["jobhunter.programs.notify_matches", "--min-fit", "8"]),
        ],
    ),
    (
        "Accès & diagnostic",
        [
            # Masked entry of the API secret: it goes neither through the chat nor through
            # the shell history. A real console is needed (getpass reads stdin).
            ("Clés France Travail", ["jobhunter.programs.setup_francetravail"]),
            ("Fermer Chrome", ["jobhunter.programs.access", "--close"]),
            (
                "Tester accès aux sites",
                ["jobhunter.programs.test_site_access", "--all", "--limit", "0"],
            ),
            (
                "Tests live (lent, ouvre un navigateur)",
                ["jobhunter.programs.test_live_nav"],
            ),
            ("Statuts depuis mes courriels…", "courriels"),  # read-only (mail.reading)
            ("Profils…", "profils"),  # several searches, one workspace each (ADR 0013)
        ],
    ),
]

# What an interface opens itself rather than running a program.
ACTIONS = ("documents", "comparer", "recettes", "courriels", "profils")

# Programs that read the keyboard (input, getpass): run in a real console, not a pipe.
INTERACTIVE = (
    "jobhunter.programs.apply_runner",
    "jobhunter.programs.setup_francetravail",
    "jobhunter.programs.access",
)


def programme(what: list[str] | str) -> list[str] | None:
    """The module and arguments of a tool; None for an action of the interface."""
    return list(what) if isinstance(what, list) else None


def interactif(args: list[str]) -> bool:
    """True when the program needs a console of its own (keyboard, visible Chrome)."""
    return bool(args) and (args[0] in INTERACTIVE or "--chrome" in args)
