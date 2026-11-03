"""`jobhunter <command> [options]`: a single entry for all the programs.

Each command runs the original program as is (same options, same `--help`);
this module only dispatches. Examples:

    jobhunter collect --linkedin --apec       (formerly python Scripts/job_sources.py ...)
    jobhunter documents --top 30              (formerly python Scripts/generate_docs.py ...)
    jobhunter apply --canal linkedin          (IN A REAL TERMINAL: it waits for the keyboard)

The French command names of 2.24 and before (collecte, postuler, maj...) stay aliases.
    jobhunter probe_ats ...                   any program of jobhunter.programs, by its name

Without installation: `python JobHunter.pyw <command> ...` from the JobHunter
folder. Installed (`pip install -e .`), the `jobhunter` command exists directly.

No command sends an application: the final click stays the user's.

Decision: docs/adr/0008-programs-in-the-package.md
"""

import importlib
import importlib.util
import inspect
import re
import runpy
import sys
from collections.abc import Sequence

from jobhunter import _old_names
from jobhunter import root as racine

# command -> (module, what it does). The programs live in jobhunter.programs.
COMMANDES = {
    "app": ("jobhunter.launch", "ouvre l'application (comme JobHunter.pyw)"),
    "collect": ("jobhunter.sources", "collecte les offres et les fusionne dans la file"),
    "companies-import": (
        "jobhunter.sources.directories",
        "ajoute les grands employeurs du pays du profil (Wikidata, SIRENE) au registre",
    ),
    "sort": ("jobhunter.scoring.sorting", "retire de la file ce qui ne colle pas au profil"),
    "documents": ("jobhunter.programs.generate_docs", "CV et lettre par offre"),
    "regenerate": (
        "jobhunter.programs.regenerate_docs",
        "refait les documents existants apres un changement de gabarit",
    ),
    "message": ("jobhunter.documents.message", "message court des formulaires"),
    "cv-auto": ("jobhunter.documents.cv_auto", "banque de faits du CV automatique"),
    "availability": ("jobhunter.programs.availability_audit", "controle les offres fermees"),
    "reposts": (
        "jobhunter.programs.reposts",
        "offres republiees, et meme texte sous une autre entreprise (colonne Signal)",
    ),
    "postings": (
        "jobhunter.programs.archive_postings",
        "garde une copie de l'annonce de chaque candidature (Letters/Postings)",
    ),
    "recipes": (
        "jobhunter.programs.recipes",
        "recettes de nettoyage (noms d'entreprises, lieux, contrats) : apercu, puis --appliquer",
    ),
    "restore": (
        "jobhunter.programs.restore",
        "remet la file d'une sauvegarde (le suivi n'est jamais touche)",
    ),
    "evaluation": (
        "jobhunter.programs.ranking_evaluation",
        "le classement face a mes jugements (postule, mauvaise...)",
    ),
    "yield": (
        "jobhunter.programs.source_yield",
        "ce que chaque source de collecte rapporte",
    ),
    "check": (
        "jobhunter.programs.check_folders",
        "verifie les dossiers (CV, lettre) avant envoi",
    ),
    "proofread": (
        "jobhunter.programs.proofread_letters",
        "relit les lettres et signale ce qui cloche (rien n'est modifie)",
    ),
    "mail-statuses": (
        "jobhunter.programs.mail_statuses",
        "statuts proposes depuis tes courriels, valides un a un (lecture seule)",
    ),
    "apply": (
        "jobhunter.programs.apply_runner",
        "candidature semi-automatique (l'envoi reste humain)",
    ),
    "pipeline": ("jobhunter.programs.daily_pipeline", "la routine quotidienne complete"),
    "add": ("jobhunter.programs.add_offer", "ajoute une offre par son URL"),
    "profile": ("jobhunter.programs.first_launch", "cree le profil depuis un CV"),
    "check-profile": (
        "jobhunter.programs.check_profile",
        "intitules gardes ou ecartes, domaine, note",
    ),
    "show-profile": ("jobhunter.profile", "affiche le profil tel que le moteur le lit"),
    "profiles": (
        "jobhunter.programs.profiles_cli",
        "plusieurs profils : liste, changer, nouveau depuis un CV, renommer, archiver",
    ),
    "update": ("jobhunter.programs.update", "met JobHunter a jour depuis GitHub"),
    "shortcut": (
        "jobhunter.programs.shortcut",
        "raccourci JobHunter dans le menu Demarrer (--bureau : aussi sur le bureau)",
    ),
    "migrate": (
        "jobhunter.programs.migrate",
        "passe les dossiers de donnees aux noms anglais de la 3.0 (avec sauvegarde)",
    ),
}


# The French names of 2.24 and before keep working: scheduled tasks, scripts and habits.
ALIAS = {
    "collecte": "collect",
    "tri": "sort",
    "regenerer": "regenerate",
    "dispo": "availability",
    "restaurer": "restore",
    "recettes": "recipes",
    "rendement": "yield",
    "controle": "check",
    "relecture": "proofread",
    "statuts-mail": "mail-statuses",
    "postuler": "apply",
    "ajouter": "add",
    "profil": "profile",
    "verifier-profil": "check-profile",
    "voir-profil": "show-profile",
    "maj": "update",
    "profils": "profiles",
}


def aide() -> str:
    """The help text: the named commands and their role."""
    largeur = max(map(len, COMMANDES))
    lignes = ["usage : jobhunter <commande> [options]   (jobhunter <commande> --help)", ""]
    lignes += [f"  {c:<{largeur}}  {d}" for c, (_m, d) in COMMANDES.items()]
    lignes += ["", "  et tout programme de jobhunter.programs par son nom (jobhunter probe_ats)"]
    return "\n".join(lignes)


def module_de(cmd: str) -> str | None:
    """The module of a command: a named command, or a program by its name."""
    cmd = ALIAS.get(cmd, cmd)
    if cmd in COMMANDES:
        return COMMANDES[cmd][0]
    if not cmd.isidentifier():
        return None
    # A program by its French name of 2.24 (jobhunter relances -> programs.follow_ups).
    nom = _old_names.ANCIENS.get(f"programmes.{cmd}", f"programs.{cmd}")
    if importlib.util.find_spec(f"jobhunter.{nom}"):
        return f"jobhunter.{nom}"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Runs a command: `jobhunter <command> [options]`.

    Args:
        argv: the arguments, without the program name; None = sys.argv.

    Returns:
        The exit code of the command (2 if it is unknown).
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "aide"):
        print(aide())
        return 0
    cmd, reste = argv[0], argv[1:]
    from jobhunter.profiles import appliquer

    appliquer()  # the active profile, before the command builds its paths
    module = module_de(cmd)
    if module is None:
        print(f"jobhunter : commande inconnue « {cmd} »\n\n{aide()}", file=sys.stderr)
        return 2
    if module == "jobhunter.launch":
        # The window has no options: `app --help` opened it, and its background
        # collection outlived a caller that closed it (22/10/2026).
        if any(a in ("-h", "--help") for a in reste):
            print(f"jobhunter {cmd} — {COMMANDES[cmd][1]}. Aucune option.")
            return 0
        from jobhunter.welcome import assurer_profil

        assurer_profil()
    # The steps launched as subprocesses (pipeline, application) do `python -m ...`.
    racine.exporter_paquet()
    sys.argv = [f"jobhunter {cmd}", *reste]  # argparse's prog, and the few that read it
    try:
        return executer(module, reste)
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):
            return e.code or 0
        print(e.code, file=sys.stderr)  # sys.exit("message"): display it, like Python
        return 1


# The `__main__` block a program must end with to be called as a function: `main()` or
# `sys.exit(main())`, nothing else. Anything more (a self-test, a console set up) runs
# as a script, as before.
_BLOC_MAIN = re.compile(r'\nif __name__ == "__main__":\n\s+(sys\.exit\()?main\(\)\)?\s*$')


def executer(module: str, argv: Sequence[str]) -> int:
    """Runs the program `module` with `argv`, in this process.

    A program whose `__main__` block only calls `main` is imported and its
    `main(argv)` called: a function with arguments and an exit code, which a test or
    another program calls the same way. The others (a package, a self-test in the
    block) run as `python -m` would.

    Returns:
        The exit code: what `sys.exit(main())` would give.
    """
    spec = importlib.util.find_spec(module)
    source = spec.loader.get_source(module) if spec and spec.loader else None  # type: ignore[attr-defined]
    canon = (
        _BLOC_MAIN.search(source or "") if spec and not spec.submodule_search_locations else None
    )
    if canon is None:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
        return 0
    principal = importlib.import_module(module).main
    code = principal(argv) if inspect.signature(principal).parameters else principal()
    if not canon.group(1):  # a bare `main()`: its return value was never the exit code
        return 0
    if code is None or isinstance(code, int):
        return int(code or 0)
    raise SystemExit(code)


if __name__ == "__main__":
    sys.exit(main())
