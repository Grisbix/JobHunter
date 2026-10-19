"""`jobhunter <command> [options]`: a single entry for all the programs.

Each command runs the original program as is (same options, same `--help`);
this module only dispatches. Examples:

    jobhunter collecte --linkedin --apec      (formerly python Scripts/job_sources.py ...)
    jobhunter documents --top 30              (formerly python Scripts/generate_docs.py ...)
    jobhunter postuler --canal linkedin       (IN A REAL TERMINAL: it waits for the keyboard)
    jobhunter probe_ats ...                   any program of jobhunter.programmes, by its name

Without installation: `python JobHunter.pyw <command> ...` from the JobHunter
folder. Installed (`pip install -e .`), the `jobhunter` command exists directly.

No command sends an application: the final click stays the user's.

Decision: docs/adr/0008-programs-in-the-package.md
"""

import importlib.util
import runpy
import sys
from collections.abc import Sequence

from jobhunter import racine

# command -> (module, what it does). The programs live in jobhunter.programmes.
COMMANDES = {
    "app": ("jobhunter.app", "ouvre l'application (comme JobHunter.pyw)"),
    "collecte": ("jobhunter.sources", "collecte les offres et les fusionne dans la file"),
    "tri": ("jobhunter.scoring.tri", "retire de la file ce qui ne colle pas au profil"),
    "documents": ("jobhunter.programmes.generate_docs", "CV et lettre par offre"),
    "regenerer": (
        "jobhunter.programmes.regenere_docs",
        "refait les documents existants apres un changement de gabarit",
    ),
    "message": ("jobhunter.documents.message", "message court des formulaires"),
    "cv-auto": ("jobhunter.documents.cv_auto", "banque de faits du CV automatique"),
    "dispo": ("jobhunter.programmes.audit_dispo", "controle les offres fermees"),
    "evaluation": (
        "jobhunter.programmes.evaluation_classement",
        "le classement face a mes jugements (postule, mauvaise...)",
    ),
    "rendement": (
        "jobhunter.programmes.rendement_sources",
        "ce que chaque source de collecte rapporte",
    ),
    "controle": (
        "jobhunter.programmes.controle_dossiers",
        "verifie les dossiers (CV, lettre) avant envoi",
    ),
    "relecture": (
        "jobhunter.programmes.relecture",
        "relit les lettres et signale ce qui cloche (rien n'est modifie)",
    ),
    "statuts-mail": (
        "jobhunter.programmes.statuts_mail",
        "statuts proposes depuis tes courriels, valides un a un (lecture seule)",
    ),
    "postuler": (
        "jobhunter.programmes.apply_runner",
        "candidature semi-automatique (l'envoi reste humain)",
    ),
    "pipeline": ("jobhunter.programmes.pipeline_quotidien", "la routine quotidienne complete"),
    "ajouter": ("jobhunter.programmes.add_offer", "ajoute une offre par son URL"),
    "profil": ("jobhunter.programmes.premier_lancement", "cree le profil depuis un CV"),
    "verifier-profil": (
        "jobhunter.programmes.verifie_profil",
        "intitules gardes ou ecartes, domaine, note",
    ),
    "voir-profil": ("jobhunter.profil", "affiche le profil tel que le moteur le lit"),
    "maj": ("jobhunter.programmes.mise_a_jour", "met JobHunter a jour depuis GitHub"),
}


def aide() -> str:
    """Le texte d'aide : les commandes nommées et leur rôle."""
    largeur = max(map(len, COMMANDES))
    lignes = ["usage : jobhunter <commande> [options]   (jobhunter <commande> --help)", ""]
    lignes += [f"  {c:<{largeur}}  {d}" for c, (_m, d) in COMMANDES.items()]
    lignes += ["", "  et tout programme de jobhunter.programmes par son nom (jobhunter probe_ats)"]
    return "\n".join(lignes)


def module_de(cmd: str) -> str | None:
    """The module of a command: a named command, or a program by its name."""
    if cmd in COMMANDES:
        return COMMANDES[cmd][0]
    if cmd.isidentifier() and importlib.util.find_spec(f"jobhunter.programmes.{cmd}"):
        return f"jobhunter.programmes.{cmd}"
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
    module = module_de(cmd)
    if module is None:
        print(f"jobhunter : commande inconnue « {cmd} »\n\n{aide()}", file=sys.stderr)
        return 2
    if module == "jobhunter.app":
        from jobhunter.accueil import assurer_profil

        assurer_profil()
    # The steps launched as subprocesses (pipeline, application) do `python -m ...`.
    racine.exporter_paquet()
    sys.argv = [f"jobhunter {cmd}", *reste]
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):
            return e.code or 0
        print(e.code, file=sys.stderr)  # sys.exit("message"): display it, like Python
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
