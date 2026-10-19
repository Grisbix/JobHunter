"""`jobhunter <commande> [options]` : une seule entree pour tous les programmes.

Chaque commande lance le programme d'origine tel quel (memes options, meme `--help`) ;
ce module ne fait qu'aiguiller. Exemples :

    jobhunter collecte --linkedin --apec      (ancien python Scripts/job_sources.py ...)
    jobhunter documents --top 30              (ancien python Scripts/generate_docs.py ...)
    jobhunter postuler --canal linkedin       (DANS UN VRAI TERMINAL : il attend le clavier)
    jobhunter probe_ats ...                   tout programme de jobhunter.programmes, par son nom

Sans installation : `python JobHunter.pyw <commande> ...` depuis le dossier de
JobHunter. Installe (`pip install -e .`), la commande `jobhunter` existe directement.

Aucune commande n'envoie de candidature : le clic final reste celui de l'utilisateur.

Decision : docs/adr/0008-programmes-dans-le-paquet.md
"""

import importlib.util
import runpy
import sys
from collections.abc import Sequence

from jobhunter import racine

# commande -> (module, ce qu'elle fait). Les programmes vivent dans jobhunter.programmes.
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
    largeur = max(map(len, COMMANDES))
    lignes = ["usage : jobhunter <commande> [options]   (jobhunter <commande> --help)", ""]
    lignes += [f"  {c:<{largeur}}  {d}" for c, (_m, d) in COMMANDES.items()]
    lignes += ["", "  et tout programme de jobhunter.programmes par son nom (jobhunter probe_ats)"]
    return "\n".join(lignes)


def module_de(cmd: str) -> str | None:
    """Le module d'une commande : une commande nommee, ou un programme par son nom."""
    if cmd in COMMANDES:
        return COMMANDES[cmd][0]
    if cmd.isidentifier() and importlib.util.find_spec(f"jobhunter.programmes.{cmd}"):
        return f"jobhunter.programmes.{cmd}"
    return None


def main(argv: Sequence[str] | None = None) -> int:
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
    # Les etapes lancees en sous-processus (pipeline, application) font `python -m ...`.
    racine.exporter_paquet()
    sys.argv = [f"jobhunter {cmd}", *reste]
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):
            return e.code or 0
        print(e.code, file=sys.stderr)  # sys.exit("message") : l'afficher, comme Python
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
