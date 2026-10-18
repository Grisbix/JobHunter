"""`jobhunter <commande> [options]` : une seule entree pour tous les programmes.

Chaque commande lance le programme d'origine tel quel (memes options, meme `--help`) ;
ce module ne fait qu'aiguiller. Exemples :

    jobhunter collecte --linkedin --apec      (= python Scripts/job_sources.py ...)
    jobhunter documents --top 30              (= python Scripts/generate_docs.py ...)
    jobhunter postuler --canal linkedin       (DANS UN VRAI TERMINAL : il attend le clavier)

Sans installation : `python -m jobhunter ...` avec src/ dans le chemin. Installe
(`pip install -e .`, phase 6 du plan), la commande `jobhunter` existe directement.

Aucune commande n'envoie de candidature : le clic final reste celui de l'utilisateur.
"""

import runpy
import sys

from jobhunter import racine

# commande -> (module, ce qu'elle fait). Un nom sans point est un programme de Scripts/.
COMMANDES = {
    "app": ("jobhunter.app", "ouvre l'application (comme JobHunter.pyw)"),
    "collecte": ("jobhunter.sources", "collecte les offres et les fusionne dans la file"),
    "tri": ("jobhunter.scoring.tri", "retire de la file ce qui ne colle pas au profil"),
    "documents": ("generate_docs", "CV et lettre par offre"),
    "regenerer": ("regenere_docs", "refait les documents existants apres un changement de gabarit"),
    "message": ("jobhunter.documents.message", "message court des formulaires"),
    "cv-auto": ("jobhunter.documents.cv_auto", "banque de faits du CV automatique"),
    "dispo": ("audit_dispo", "controle les offres fermees"),
    "postuler": ("apply_runner", "candidature semi-automatique (l'envoi reste humain)"),
    "pipeline": ("pipeline_quotidien", "la routine quotidienne complete"),
    "ajouter": ("add_offer", "ajoute une offre par son URL"),
    "profil": ("premier_lancement", "cree le profil depuis un CV"),
    "verifier-profil": ("verifie_profil", "intitules gardes ou ecartes, domaine, note"),
    "maj": ("mise_a_jour", "met JobHunter a jour depuis GitHub"),
}


def aide():
    largeur = max(map(len, COMMANDES))
    lignes = ["usage : jobhunter <commande> [options]   (jobhunter <commande> --help)", ""]
    lignes += [f"  {c:<{largeur}}  {d}" for c, (_m, d) in COMMANDES.items()]
    return "\n".join(lignes)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "aide"):
        print(aide())
        return 0
    cmd, reste = argv[0], argv[1:]
    if cmd not in COMMANDES:
        print(f"jobhunter : commande inconnue « {cmd} »\n\n{aide()}", file=sys.stderr)
        return 2
    module = COMMANDES[cmd][0]
    if module == "jobhunter.app":
        from jobhunter.accueil import assurer_profil

        assurer_profil()
    # Les programmes de Scripts/ s'importent entre eux par leur nom.
    scripts = str(racine.scripts())
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
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
